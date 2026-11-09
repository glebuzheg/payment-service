from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException

from app.auth import require_key
from app.dependencies import payment_service
from app.domain import IdempotencyConflict, PaymentNotFound
from app.schemas import PaymentAccepted, PaymentDetail, PaymentIn


router = APIRouter(prefix="/api/v1/payments", dependencies=[Depends(require_key)])


@router.post("", status_code=202, response_model=PaymentAccepted)
async def create_payment(body: PaymentIn, idempotency_key: Annotated[str, Header(min_length=1, max_length=255)]):
    try:
        return await payment_service.create_payment(body.to_domain(), idempotency_key)
    except IdempotencyConflict:
        raise HTTPException(409, "Idempotency key already used for another request") from None


@router.get("/{payment_id}", response_model=PaymentDetail)
async def get_payment(payment_id: UUID):
    try:
        return await payment_service.get_payment(str(payment_id))
    except PaymentNotFound:
        raise HTTPException(404, "Payment not found") from None
