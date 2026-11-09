import pytest
import httpx
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_three_attempts_then_raises(monkeypatch):
    from app.service import retry

    attempts = []
    delays = []

    async def fail():
        attempts.append(1)
        raise RuntimeError("offline")

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("app.service.asyncio.sleep", sleep)
    with pytest.raises(RuntimeError, match="offline"):
        await retry(fail)
    assert len(attempts) == 3
    assert delays == [1, 2]


@pytest.mark.asyncio
async def test_redelivery_keeps_result_and_commits_before_notification(monkeypatch):
    from app import repository, service
    from app.db import Base
    from app.models import Payment

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(repository, "Session", sessions)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions.begin() as session:
        payment = Payment(
            amount=Decimal("2.00"), currency="RUB", description="Test", metadata_json={},
            idempotency_key="redelivery", request_hash="x", webhook_url="https://example.com/hook",
        )
        session.add(payment)
        await session.flush()
        payment_id = payment.id

    gateway_calls = 0
    notified = []

    async def gateway():
        nonlocal gateway_calls
        gateway_calls += 1
        return "succeeded"

    async def notify(result):
        async with sessions() as session:
            stored = await session.get(Payment, payment_id)
            assert stored.status == "succeeded"
            assert stored.processed_at is not None
        notified.append(result.status)

    monkeypatch.setattr(service, "gateway_result", gateway)
    processor = service.PaymentService(repository, notify)
    await processor.process_once(payment_id)
    await processor.process_once(payment_id)

    assert gateway_calls == 1
    assert notified == ["succeeded", "succeeded"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_webhook_payload_and_idempotency_header(monkeypatch):
    from app import webhook
    from app.domain import PaymentView

    sent = []

    def receive(request):
        sent.append((request.headers["X-Payment-Id"], request.content))
        return httpx.Response(204)

    client_type = httpx.AsyncClient
    monkeypatch.setattr(
        webhook.httpx, "AsyncClient",
        lambda timeout: client_type(transport=httpx.MockTransport(receive), timeout=timeout),
    )
    processed_at = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    payment = PaymentView(
        payment_id="payment-1", amount=Decimal("2.00"), currency="RUB",
        description="Test", metadata={}, status="succeeded", idempotency_key="key",
        webhook_url="https://example.com/hook", created_at=processed_at,
        processed_at=processed_at,
    )
    await webhook.send_result(payment)

    assert sent == [(
        "payment-1",
        b'{"payment_id":"payment-1","status":"succeeded","processed_at":"2026-11-09T12:00:00+00:00"}',
    )]
