import json
from typing import Dict, Any
from .client import get_nats_client
from ..ws.manager import manager


async def publish_rate_event(rate_data: Dict[str, Any]):
    nc = await get_nats_client()
    msg = json.dumps(rate_data, default=str)
    await nc.publish("currency.new_rate", msg.encode())

async def subscribe_to_nats():
    nc = await get_nats_client()
    async def message_handler(msg):
        data = json.loads(msg.data.decode())
        await manager.broadcast({
            "event": "new_rate",
            "payload": data
        })

    await nc.subscribe("currency.new_rate", cb=message_handler)