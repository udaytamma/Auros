from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanySeed:
    id: str
    name: str
    careers_url: str
    tier: int = 2
    enabled: bool = True


DEFAULT_COMPANIES: list[CompanySeed] = [
    CompanySeed(id="stripe", name="Stripe", careers_url="https://stripe.com/jobs"),
    CompanySeed(id="airbnb", name="Airbnb", careers_url="https://careers.airbnb.com/"),
    CompanySeed(id="datadog", name="Datadog", careers_url="https://careers.datadoghq.com/"),
    CompanySeed(id="atlassian", name="Atlassian", careers_url="https://www.atlassian.com/company/careers"),
    CompanySeed(id="cloudflare", name="Cloudflare", careers_url="https://www.cloudflare.com/careers/jobs/"),
    CompanySeed(id="gitlab", name="GitLab", careers_url="https://about.gitlab.com/jobs/all-jobs/"),
    CompanySeed(id="hashicorp", name="HashiCorp", careers_url="https://www.hashicorp.com/careers"),
    CompanySeed(id="workday", name="Workday", careers_url="https://workday.wd5.myworkdayjobs.com/Workday"),
    CompanySeed(id="servicenow", name="ServiceNow", careers_url="https://careers.servicenow.com/"),
    CompanySeed(id="snowflake", name="Snowflake", careers_url="https://careers.snowflake.com/"),
]
