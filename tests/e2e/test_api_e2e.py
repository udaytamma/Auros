import pytest
import httpx


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_end_to_end_root_and_health(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        root = await client.get("/")
        health = await client.get("/health")

    assert root.status_code == 200
    assert health.status_code == 200
