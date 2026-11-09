import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class NewPayment:
    amount: Decimal
    currency: str
    description: str
    metadata: dict
    webhook_url: str


@dataclass(frozen=True)
class PaymentView:
    payment_id: str
    amount: Decimal
    currency: str
    description: str
    metadata: dict
    status: str
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


class IdempotencyConflict(Exception):
    pass


class PaymentNotFound(Exception):
    pass


def request_hash(payment: NewPayment) -> str:
    content = {
        "amount": str(payment.amount.normalize()),
        "currency": payment.currency,
        "description": payment.description,
        "metadata": payment.metadata,
        "webhook_url": payment.webhook_url,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
