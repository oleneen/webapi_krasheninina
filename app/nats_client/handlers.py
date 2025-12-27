import json
from typing import Dict, Any
from .client import get_nats_client
from ..ws.manager import manager
import logging

logger = logging.getLogger("nats_handler")

async def message_handler(msg):
    data = json.loads(msg.data.decode())
    logger.info(f"NATS message received: {data}")

    event_type = data.get("event", "new_rate")
    payload = {k: v for k, v in data.items() if k != "event"}

    await manager.broadcast({
        "event": event_type,
        "payload": payload
    })

async def publish_rate_event(rate_data: Dict[str, Any]):
    nc = await get_nats_client()
    msg = json.dumps(rate_data, default=str)
    await nc.publish("currency.new_rate", msg.encode())
    logger.debug("Published event to NATS")

async def subscribe_to_nats():
    nc = await get_nats_client()
    logger.info("Subscribing to NATS channel 'currency.new_rate'")
    await nc.subscribe("currency.new_rate", cb=message_handler)