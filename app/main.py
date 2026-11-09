import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.payments.router import router
from app.messaging.outbox import publish_forever


@asynccontextmanager
async def lifespan(app: FastAPI):
    publisher = asyncio.create_task(publish_forever())
    yield
    publisher.cancel()
    with suppress(asyncio.CancelledError):
        await publisher


app = FastAPI(title="Payment Service", lifespan=lifespan)
app.include_router(router)
