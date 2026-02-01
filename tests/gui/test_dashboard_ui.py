import asyncio
import os
import signal
import socket
import subprocess
import time

import pytest
from playwright.async_api import async_playwright


def _wait_for_port(host: str, port: int, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


@pytest.mark.gui
@pytest.mark.asyncio
async def test_dashboard_renders():
    ui_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ui"))
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
        cwd=ui_dir,
        env={**os.environ, "VITE_API_BASE_URL": "http://127.0.0.1:8008"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        assert _wait_for_port("127.0.0.1", 5173, timeout=40)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("http://127.0.0.1:5173", wait_until="domcontentloaded")
            title = await page.text_content("h1")
            assert "Auros" in (title or "")
            await browser.close()
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
