from app import repository, webhook
from app.service import PaymentService


payment_service = PaymentService(repository, webhook.send_result)
