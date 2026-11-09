import secrets
from typing import Annotated

from fastapi import Header, HTTPException

from app.settings import api_key


async def require_key(x_api_key: Annotated[str | None, Header()] = None):
    key = api_key()
    if not key or not x_api_key or not secrets.compare_digest(x_api_key, key):
        raise HTTPException(401, "Invalid API key")
