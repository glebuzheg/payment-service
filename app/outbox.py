import asyncio
import logging

from sqlalchemy import select

from app.db import Session, now
from app.models import Outbox
from app.rabbit import EXCHANGE, declare_topology, new_broker


logger = logging.getLogger(__name__)


async def publish_batch(broker):
    async with Session.begin() as session:
        rows = (await session.scalars(
            select(Outbox).where(Outbox.published_at.is_(None))
            .order_by(Outbox.created_at).limit(100).with_for_update(skip_locked=True)
        )).all()
        for row in rows:
            confirmation = await broker.publish(
                row.payload, exchange=EXCHANGE, routing_key="payments.new",
                persist=True, mandatory=True, message_id=row.id,
            )
            if confirmation is None:
                raise RuntimeError("RabbitMQ did not confirm publication")
            row.published_at = now()
        return len(rows)


async def publish_forever():
    while True:
        broker = new_broker()
        try:
            await broker.connect()
            await declare_topology(broker)
            while True:
                count = await publish_batch(broker)
                if not count:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Outbox publication failed; retrying")
            await asyncio.sleep(2)
        finally:
            await broker.close()
