import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select


@pytest.mark.asyncio
async def test_create_idempotency_and_lookup(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from app.main import app
    from app.db import engine, Base, Session
    from app.payments.models import Outbox, Payment

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    payload = {
        "amount": "12.50", "currency": "USD", "description": "Order 1",
        "metadata": {"order": 1}, "webhook_url": "https://example.com/hook",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"X-API-Key": "test-secret", "Idempotency-Key": "order-1"}
        first = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert first.status_code == 202, first.text
        assert first.json()["status"] == "pending"
        assert first.json()["created_at"].endswith("+00:00")
        again = await client.post("/api/v1/payments", json=payload, headers=headers)
        assert again.status_code == 202
        assert again.json()["payment_id"] == first.json()["payment_id"]
        conflict = await client.post(
            "/api/v1/payments", json={**payload, "amount": "13.00"}, headers=headers
        )
        assert conflict.status_code == 409
        found = await client.get(
            f"/api/v1/payments/{first.json()['payment_id']}", headers={"X-API-Key": "test-secret"}
        )
        assert found.status_code == 200
        assert found.json()["amount"] == "12.50"
        assert found.json()["metadata"] == {"order": 1}
        forbidden = await client.get(
            f"/api/v1/payments/{first.json()['payment_id']}", headers={"X-API-Key": "wrong"}
        )
        assert forbidden.status_code == 401
    async with Session() as session:
        assert await session.scalar(select(func.count()).select_from(Payment)) == 1
        assert await session.scalar(select(func.count()).select_from(Outbox)) == 1


@pytest.mark.asyncio
async def test_invalid_input_and_missing_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-secret")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = {"amount": "0", "currency": "RUB", "webhook_url": "https://example.com"}
        response = await client.post(
            "/api/v1/payments", json=body,
            headers={"X-API-Key": "test-secret", "Idempotency-Key": "x"},
        )
        assert response.status_code == 422
        response = await client.post(
            "/api/v1/payments", json={**body, "amount": "1"},
            headers={"X-API-Key": "test-secret"},
        )
        assert response.status_code == 422
