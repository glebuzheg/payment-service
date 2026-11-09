from app.payments import repository, webhook
from app.payments.service import PaymentService


payment_service = PaymentService(repository, webhook.send_result)
