import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.domain import NewPayment, PaymentView, request_hash


class PaymentStore(Protocol):
    async def create_payment(self, data: NewPayment, key: str, digest: str) -> PaymentView: ...
    async def get_payment(self, payment_id: str) -> PaymentView: ...
    async def complete_if_pending(
        self, payment_id: str, resolve: Callable[[], Awaitable[str]]
    ) -> PaymentView: ...


class PaymentService:
    def __init__(self, store: PaymentStore, notify: Callable[[PaymentView], Awaitable[None]]):
        self.store = store
        self.notify = notify

    async def create_payment(self, data: NewPayment, key: str) -> PaymentView:
        return await self.store.create_payment(data, key, request_hash(data))

    async def get_payment(self, payment_id: str) -> PaymentView:
        return await self.store.get_payment(payment_id)

    async def process_once(self, payment_id: str) -> None:
        payment = await self.store.complete_if_pending(payment_id, gateway_result)
        await self.notify(payment)

    async def process_payment(self, payment_id: str) -> None:
        await retry(lambda: self.process_once(payment_id))


async def gateway_result() -> str:
    await asyncio.sleep(random.uniform(2, 5))
    return "succeeded" if random.random() < 0.9 else "failed"


async def retry(operation):
    for attempt in range(3):
        try:
            return await operation()
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)
