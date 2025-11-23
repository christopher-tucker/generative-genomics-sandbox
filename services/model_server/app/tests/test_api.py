import httpx
import pytest

from ..main import app


@pytest.fixture
def anyio_backend():
    # Force AnyIO to use asyncio only (avoid trio dependency)
    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=5.0) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"
    assert "model_version" in body


@pytest.mark.anyio
async def test_generate_endpoint_mocked(monkeypatch):
    # Mock the heavy inference call so we don't load model artifacts during API tests.
    def fake_generate_expression(descriptor, seed=None):
        assert descriptor == {"celltype": "X"}
        assert seed == 123
        return ["G1", "G2"], [1.0, 2.0], "fake_version"

    # Patch the symbol imported into main.py
    monkeypatch.setattr("app.main.generate_expression", fake_generate_expression)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=5.0) as client:
        resp = await client.post(
            "/generate",
            json={"descriptor": {"celltype": "X"}, "seed": 123},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "model_version": "fake_version",
        "genes": ["G1", "G2"],
        "expression": [1.0, 2.0],
    }
