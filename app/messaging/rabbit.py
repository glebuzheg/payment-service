from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.settings import rabbit_url


EXCHANGE = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
DLX = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)
QUEUE = RabbitQueue(
    "payments.new", routing_key="payments.new", durable=True,
    arguments={"x-dead-letter-exchange": "payments.dlx", "x-dead-letter-routing-key": "payments.dead"},
)
DEAD_QUEUE = RabbitQueue("payments.dlq", routing_key="payments.dead", durable=True)


def new_broker():
    return RabbitBroker(rabbit_url())


async def declare_topology(broker: RabbitBroker):
    dlx = await broker.declare_exchange(DLX)
    dead = await broker.declare_queue(DEAD_QUEUE)
    await dead.bind(dlx, routing_key="payments.dead")
    exchange = await broker.declare_exchange(EXCHANGE)
    queue = await broker.declare_queue(QUEUE)
    await queue.bind(exchange, routing_key="payments.new")
