import asyncio
import json
import nats
from ws.manager import manager

async def main():
    nc = await nats.connect("nats://localhost:4222")

    async def handler(msg):
        data = json.loads(msg.data.decode())
        print("NATS EVENT:", data)

        await manager.broadcast({
            "event": "new_rate",
            "payload": data
        })

    await nc.subscribe("currency.new_rate", cb=handler)

    print("Subscribed to currency.new_rate")
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
