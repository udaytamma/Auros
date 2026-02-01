from __future__ import annotations

import asyncio
import random
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from playwright.async_api import async_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from ..config import settings
from ..logging import configure_logging
from ..utils.retry import retry_async


MAX_JOBS_PER_COMPANY = 20  # Limited for testing


@dataclass(frozen=True)
class JobLink:
    title: str
    url: str


@dataclass(frozen=True)
class WorkdayContext:
    base_url: str
    tenant: str
    site: str
    locale: str | None = None


class ScrapeError(RuntimeError):
    pass


def detect_ats(careers_url: str) -> str | None:
    parsed = urlparse(careers_url)
    host = parsed.netloc.lower()
    if "greenhouse.io" in host:
        return "greenhouse"
    if "lever.co" in host:
        return "lever"
    if "myworkdayjobs.com" in host or "workdayjobs.com" in host:
        return "workday"
    return None


def _extract_greenhouse_board(careers_url: str) -> str | None:
    parsed = urlparse(careers_url)
    host = parsed.netloc.lower()
    query = parse_qs(parsed.query)

    if "for" in query and query["for"]:
        return query["for"][0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if host.startswith("boards.") and path_parts:
        return path_parts[0]

    if host.endswith("greenhouse.io") and host not in {"boards.greenhouse.io", "boards.eu.greenhouse.io"}:
        return host.split(".")[0]

    return None


def _extract_lever_company(careers_url: str) -> str | None:
    parsed = urlparse(careers_url)
    if "lever.co" not in parsed.netloc.lower():
        return None
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        return path_parts[0]
    return None


def _parse_workday_context(careers_url: str) -> WorkdayContext | None:
    parsed = urlparse(careers_url)
    host = parsed.netloc
    if "workdayjobs" not in host:
        return None

    base_url = f"{parsed.scheme}://{host}"
    tenant = host.split(".")[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if "wday" in path_parts and "cxs" in path_parts:
        idx = path_parts.index("cxs")
        if idx + 2 < len(path_parts):
            tenant = path_parts[idx + 1]
            site = path_parts[idx + 2]
            locale = None
            if idx + 3 < len(path_parts) and path_parts[idx + 3] not in {"jobs"}:
                locale = path_parts[idx + 3]
            return WorkdayContext(base_url=base_url, tenant=tenant, site=site, locale=locale)
        return None

    locale = None
    site = None
    if path_parts:
        if len(path_parts[0]) == 5 and "-" in path_parts[0]:
            locale = path_parts[0]
            if len(path_parts) > 1:
                site = path_parts[1]
        else:
            site = path_parts[0]

    if site:
        return WorkdayContext(base_url=base_url, tenant=tenant, site=site, locale=locale)
    return None


@asynccontextmanager
async def _browser_context():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        try:
            yield context
        finally:
            await context.close()
            await browser.close()


async def scrape_company_jobs(careers_url: str) -> list[JobLink]:
    logger = configure_logging()
    ats = detect_ats(careers_url)

    async def _run():
        async def _generic_links() -> list[JobLink]:
            async with _browser_context() as context:
                page = await context.new_page()
                await page.goto(careers_url, wait_until="load", timeout=60000)
                # Wait for JS to render dynamic content
                await asyncio.sleep(3)
                links = await _extract_job_links(page, careers_url)
                await page.close()
                return links

        if ats == "greenhouse":
            try:
                return await _scrape_greenhouse_links(careers_url)
            except ScrapeError as exc:
                logger.warning_structured("greenhouse_api_failed", url=careers_url, error=str(exc))
                return await _generic_links()
        if ats == "lever":
            try:
                return await _scrape_lever_links(careers_url)
            except ScrapeError as exc:
                logger.warning_structured("lever_api_failed", url=careers_url, error=str(exc))
                return await _generic_links()
        if ats == "workday":
            try:
                return await _scrape_workday_links(careers_url)
            except ScrapeError as exc:
                logger.warning_structured("workday_api_failed", url=careers_url, error=str(exc))
                return await _generic_links()

        return await _generic_links()

    try:
        links = await retry_async(_run, (PlaywrightError, PlaywrightTimeoutError, TimeoutError, ScrapeError, httpx.HTTPError))
    except (PlaywrightError, PlaywrightTimeoutError, TimeoutError, ScrapeError, httpx.HTTPError) as exc:
        logger.error_structured("scrape_company_failed", url=careers_url, error=str(exc))
        raise ScrapeError(str(exc)) from exc

    # Limit volume to protect performance
    return links[:MAX_JOBS_PER_COMPANY]


async def fetch_job_description(url: str) -> str:
    logger = configure_logging()

    async def _run():
        async with _browser_context() as context:
            page = await context.new_page()
            await _rate_limit()
            await page.goto(url, wait_until="load", timeout=60000)
            text = await page.evaluate("document.body.innerText")
            await page.close()
            return _normalize_text(text)

    try:
        return await retry_async(_run, (PlaywrightError, PlaywrightTimeoutError, TimeoutError))
    except (PlaywrightError, PlaywrightTimeoutError, TimeoutError) as exc:
        logger.error_structured("fetch_job_description_failed", url=url, error=str(exc))
        raise ScrapeError(str(exc)) from exc


async def scrape_jobs_with_descriptions(careers_url: str, title_filter=None) -> list[dict]:
    logger = configure_logging()
    ats = detect_ats(careers_url)

    async def _run():
        async def _generic_scrape() -> list[dict]:
            async with _browser_context() as context:
                page = await context.new_page()
                await page.goto(careers_url, wait_until="load", timeout=60000)
                # Wait for JS to render dynamic content
                await asyncio.sleep(3)
                links = await _extract_job_links(page, careers_url)
                if title_filter:
                    links = [link for link in links if title_filter(link.title)]
                await page.close()
                return await _fetch_descriptions_for_links(links, context=context)

        if ats == "greenhouse":
            try:
                jobs = await _scrape_greenhouse_jobs(careers_url)
                if title_filter:
                    jobs = [job for job in jobs if title_filter(job["title"])]
                return jobs
            except ScrapeError as exc:
                logger.warning_structured("greenhouse_api_failed", url=careers_url, error=str(exc))
                return await _generic_scrape()
        if ats == "lever":
            try:
                jobs = await _scrape_lever_jobs(careers_url)
                if title_filter:
                    jobs = [job for job in jobs if title_filter(job["title"])]
                return jobs
            except ScrapeError as exc:
                logger.warning_structured("lever_api_failed", url=careers_url, error=str(exc))
                return await _generic_scrape()
        if ats == "workday":
            try:
                links = await _scrape_workday_links(careers_url)
                if title_filter:
                    links = [link for link in links if title_filter(link.title)]
                return await _fetch_descriptions_for_links(links)
            except ScrapeError as exc:
                logger.warning_structured("workday_api_failed", url=careers_url, error=str(exc))
                return await _generic_scrape()

        return await _generic_scrape()

    try:
        return await retry_async(_run, (PlaywrightError, PlaywrightTimeoutError, TimeoutError, ScrapeError, httpx.HTTPError))
    except (PlaywrightError, PlaywrightTimeoutError, TimeoutError, ScrapeError, httpx.HTTPError) as exc:
        logger.error_structured("scrape_jobs_with_descriptions_failed", url=careers_url, error=str(exc))
        raise ScrapeError(str(exc)) from exc


async def _fetch_descriptions_for_links(
    links: list[JobLink],
    context=None,
) -> list[dict]:
    logger = configure_logging()

    if not links:
        return []

    if context is None:
        async with _browser_context() as local_context:
            return await _fetch_descriptions_for_links(links, context=local_context)

    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PAGES)

    async def fetch(link: JobLink) -> dict | Exception:
        job_page = None
        try:
            async with semaphore:
                await _rate_limit()
                job_page = await context.new_page()
                await job_page.goto(link.url, wait_until="load", timeout=60000)
                text = await job_page.evaluate("document.body.innerText")
                return {"title": link.title, "url": link.url, "description": _normalize_text(text)}
        except (PlaywrightError, PlaywrightTimeoutError, TimeoutError) as exc:
            logger.error_structured("fetch_job_failed", url=link.url, error=str(exc))
            return exc
        finally:
            if job_page:
                await job_page.close()

    tasks = [fetch(link) for link in links[:MAX_JOBS_PER_COMPANY]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning_structured(
                "job_fetch_skipped",
                url=links[i].url if i < len(links) else "unknown",
                error=str(result),
            )
        elif isinstance(result, dict):
            successful_results.append(result)

    return successful_results


async def _extract_job_links(page, base_url: str) -> list[JobLink]:
    candidates = await page.evaluate(
        """
        () => Array.from(document.querySelectorAll('a'))
            .map(a => ({ text: a.textContent || '', href: a.href || '' }))
        """
    )

    base_domain = urlparse(base_url).netloc
    filtered: list[JobLink] = []
    seen = set()

    for item in candidates:
        href = item.get("href") or ""
        text = " ".join((item.get("text") or "").split())
        if not href or len(text) < 3:
            continue

        parsed = urlparse(href)
        if parsed.scheme in {"mailto", "tel"}:
            continue
        # Allow links from known ATS domains
        is_ats_domain = any(ats in parsed.netloc for ats in settings.ATS_ALLOWED_DOMAINS)
        if parsed.netloc and parsed.netloc != base_domain and not is_ats_domain:
            continue

        if not _looks_like_job_link(href, text):
            continue

        final_url = href if parsed.scheme else urljoin(base_url, href)
        if final_url in seen:
            continue
        seen.add(final_url)
        filtered.append(JobLink(title=text, url=final_url))

    return filtered


def _looks_like_job_link(href: str, text: str) -> bool:
    h = href.lower()
    t = text.lower()
    if any(bad in t for bad in ["privacy", "cookie", "terms", "policy", "benefits", "equal employment"]):
        return False
    if any(x in h for x in ["/jobs/", "/job/", "/careers/", "greenhouse.io", "lever.co", "workdayjobs", "job" ]):
        return True
    if any(x in t for x in ["manager", "program", "product", "technical", "tpm", "principal", "senior"]):
        return True
    return False


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(text.split())


def _normalize_text(text: str) -> str:
    return " ".join(text.split())[:50000]


async def _rate_limit() -> None:
    delay = random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)
    await asyncio.sleep(delay)


async def _fetch_json(url: str, method: str = "GET", payload: dict | None = None) -> Any:
    async def _run():
        async with httpx.AsyncClient(timeout=20) as client:
            if method.upper() == "POST":
                resp = await client.post(url, json=payload)
            else:
                resp = await client.get(url, params=payload)
            resp.raise_for_status()
            return resp.json()

    try:
        return await retry_async(_run, (httpx.HTTPError, TimeoutError))
    except (httpx.HTTPError, TimeoutError) as exc:
        raise ScrapeError(str(exc)) from exc


async def _scrape_greenhouse_jobs(careers_url: str) -> list[dict]:
    board = _extract_greenhouse_board(careers_url)
    if not board:
        raise ScrapeError("Unable to determine Greenhouse board")

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    data = await _fetch_json(api_url)
    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title")
        url = job.get("absolute_url") or job.get("url")
        if not title or not url:
            continue
        content = job.get("content") or job.get("content_text") or ""
        description = _normalize_text(_strip_html(content))
        jobs.append({"title": title, "url": url, "description": description})
    return jobs[:MAX_JOBS_PER_COMPANY]


async def _scrape_greenhouse_links(careers_url: str) -> list[JobLink]:
    jobs = await _scrape_greenhouse_jobs(careers_url)
    return [JobLink(title=job["title"], url=job["url"]) for job in jobs]


async def _scrape_lever_jobs(careers_url: str) -> list[dict]:
    company = _extract_lever_company(careers_url)
    if not company:
        raise ScrapeError("Unable to determine Lever company slug")

    api_url = f"https://api.lever.co/v0/postings/{company}"
    data = await _fetch_json(api_url, payload={"mode": "json"})
    jobs = []
    for job in data or []:
        title = job.get("text")
        url = job.get("hostedUrl") or job.get("applyUrl")
        if not title or not url:
            continue
        description = job.get("descriptionPlain") or _strip_html(job.get("description") or "")
        jobs.append({"title": title, "url": url, "description": _normalize_text(description)})
    return jobs[:MAX_JOBS_PER_COMPANY]


async def _scrape_lever_links(careers_url: str) -> list[JobLink]:
    jobs = await _scrape_lever_jobs(careers_url)
    return [JobLink(title=job["title"], url=job["url"]) for job in jobs]


def _extract_workday_postings(data: dict) -> list[dict]:
    if "jobPostings" in data:
        return data["jobPostings"] or []
    if "jobs" in data:
        return data["jobs"] or []
    if "data" in data and isinstance(data["data"], dict):
        inner = data["data"]
        if "jobPostings" in inner:
            return inner["jobPostings"] or []
        if "jobs" in inner:
            return inner["jobs"] or []
    return []


def _extract_workday_total(data: dict) -> int | None:
    for key in ("total", "totalCount"):
        if key in data and isinstance(data[key], int):
            return data[key]
    if "data" in data and isinstance(data["data"], dict):
        inner = data["data"]
        for key in ("total", "totalCount"):
            if key in inner and isinstance(inner[key], int):
                return inner[key]
    page = data.get("page") if isinstance(data.get("page"), dict) else None
    if page and isinstance(page.get("total"), int):
        return page["total"]
    return None


async def _workday_request(api_url: str, payload: dict) -> dict:
    try:
        return await _fetch_json(api_url, method="POST", payload=payload)
    except ScrapeError:
        return await _fetch_json(api_url, method="GET", payload=payload)


async def _scrape_workday_links(careers_url: str) -> list[JobLink]:
    ctx = _parse_workday_context(careers_url)
    if not ctx:
        raise ScrapeError("Unable to determine Workday context")

    base_api = f"{ctx.base_url}/wday/cxs/{ctx.tenant}/{ctx.site}/jobs"
    alt_api = None
    if ctx.locale:
        alt_api = f"{ctx.base_url}/wday/cxs/{ctx.tenant}/{ctx.site}/{ctx.locale}/jobs"

    payload = {"limit": 50, "offset": 0, "appliedFacets": {}}
    links: list[JobLink] = []

    while True:
        try:
            data = await _workday_request(base_api, payload)
        except ScrapeError:
            if not alt_api:
                raise
            data = await _workday_request(alt_api, payload)

        postings = _extract_workday_postings(data)
        for job in postings:
            title = job.get("title") or job.get("jobTitle")
            if not title:
                continue
            url = job.get("jobPostingUrl") or job.get("externalUrl") or job.get("externalURL")
            external_path = job.get("externalPath")
            if not url and external_path:
                url = urljoin(ctx.base_url, external_path)
            if not url:
                continue
            links.append(JobLink(title=title, url=url))

        total = _extract_workday_total(data)
        payload["offset"] += payload["limit"]
        if not total or payload["offset"] >= total:
            break

    return links[:MAX_JOBS_PER_COMPANY]
