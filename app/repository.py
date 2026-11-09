from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import Session, now
from app.domain import IdempotencyConflict, NewPayment, PaymentNotFound, PaymentView
from app.models import Outbox, Payment


def to_view(payment: Payment) -> PaymentView:
    return PaymentView(
        payment_id=payment.id, amount=payment.amount, currency=payment.currency,
        description=payment.description, metadata=payment.metadata_json, status=payment.status,
        idempotency_key=payment.idempotency_key, webhook_url=payment.webhook_url,
        created_at=payment.created_at, processed_at=payment.processed_at,
    )


def check_key(payment: Payment, digest: str) -> PaymentView:
    if payment.request_hash != digest:
        raise IdempotencyConflict
    return to_view(payment)


async def create_payment(data: NewPayment, key: str, digest: str) -> PaymentView:
    async with Session() as session:
        existing = await session.scalar(select(Payment).where(Payment.idempotency_key == key))
        if existing:
            return check_key(existing, digest)
        payment = Payment(
            amount=data.amount, currency=data.currency, description=data.description,
            metadata_json=data.metadata, webhook_url=data.webhook_url,
            idempotency_key=key, request_hash=digest,
        )
        session.add(payment)
        try:
            await session.flush()
            session.add(Outbox(payment_id=payment.id, payload={"payment_id": payment.id}))
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await session.scalar(select(Payment).where(Payment.idempotency_key == key))
            if existing is None:
                raise
            return check_key(existing, digest)
        return to_view(payment)


async def get_payment(payment_id: str) -> PaymentView:
    async with Session() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            raise PaymentNotFound
        return to_view(payment)


async def complete_if_pending(payment_id: str, resolve: Callable[[], Awaitable[str]]) -> PaymentView:
    async with Session.begin() as session:
        payment = await session.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if payment is None:
            raise PaymentNotFound
        if payment.status == "pending":
            payment.status = await resolve()
            payment.processed_at = now()
        return to_view(payment)
