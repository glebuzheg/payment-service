from faststream import FastStream

from app.payments.dependencies import payment_service
from app.messaging.rabbit import EXCHANGE, QUEUE, declare_topology, new_broker


broker = new_broker()
app = FastStream(broker)


@app.after_startup
async def prepare_topology():
    await declare_topology(broker)


@broker.subscriber(QUEUE, EXCHANGE)
async def handle_payment(payload: dict):
    await payment_service.process_payment(payload["payment_id"])
