import nats
from ..config import settings

_nats_client = None

async def get_nats_client():
    global _nats_client
    if _nats_client is None:
        _nats_client = await nats.connect(settings.NATS_URL)
    return _nats_client

async def close_nats_client():
    global _nats_client
    if _nats_client:
        await _nats_client.close()
        _nats_client = None