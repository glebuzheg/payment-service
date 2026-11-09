import httpx

from app.payments.domain import PaymentView


async def send_result(payment: PaymentView) -> None:
    body = {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.post(
            payment.webhook_url, json=body, headers={"X-Payment-Id": payment.payment_id}
        )
        response.raise_for_status()
