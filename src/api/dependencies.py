from fastapi import Header, HTTPException
from core.config import config


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Dependency kiểm tra API Key cho mọi request từ Edge Node và UI."""
    if x_api_key != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key
