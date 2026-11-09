from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer

from app.domain import NewPayment


class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Literal["RUB", "USD", "EUR"]
    description: str = Field(max_length=500)
    metadata: dict = Field(default_factory=dict)
    webhook_url: HttpUrl

    def to_domain(self) -> NewPayment:
        return NewPayment(
            amount=self.amount, currency=self.currency, description=self.description,
            metadata=self.metadata, webhook_url=str(self.webhook_url),
        )


class PaymentAccepted(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: str
    status: str
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()


class PaymentDetail(PaymentAccepted):
    amount: Decimal
    currency: str
    description: str
    metadata: dict
    idempotency_key: str
    webhook_url: str
    processed_at: datetime | None

    @field_serializer("processed_at", when_used="json")
    def serialize_processed_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
