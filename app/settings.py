import os


def api_key() -> str | None:
    return os.getenv("API_KEY")


def database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+asyncpg://payment:payment@localhost/payment")


def rabbit_url() -> str:
    return os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")
