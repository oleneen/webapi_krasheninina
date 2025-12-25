import asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import CurrencyRate
from ..services.cbr_parser import fetch_rates_from_cbr
from ..nats_client.handlers import publish_rate_event
from ..config import settings
from ..db.base import AsyncSessionLocal
from sqlalchemy import select

async def save_and_publish_rates(rates_data, db: AsyncSession):
    new_rates = []
    for rate_dto in rates_data:
        existing = await db.execute(
            select(CurrencyRate)
            .where(CurrencyRate.char_code == rate_dto.char_code)
            .where(CurrencyRate.date == rate_dto.date)
        )
        if existing.scalar_one_or_none():
            continue

        db_obj = CurrencyRate(**rate_dto.dict())
        db.add(db_obj)
        new_rates.append(db_obj)

    if new_rates:
        await db.commit()
        for r in new_rates:
            await db.refresh(r)
            await publish_rate_event({
                "id": r.id,
                "char_code": r.char_code,
                "value": float(r.value),
                "date": r.date.isoformat()
            })

async def periodic_fetch_task():
    while True:
        try:
            rates = await fetch_rates_from_cbr()
            async with AsyncSessionLocal() as session:
                await save_and_publish_rates(rates, session)

        except httpx.ConnectTimeout:
            print("[Periodic Task] CBR timeout, retry later")

        except Exception as e:
            print("[Periodic Task] Error:", repr(e))

        await asyncio.sleep(settings.FETCH_INTERVAL_SEC)

async def manual_fetch_task():
    try:
        rates = await fetch_rates_from_cbr()
        async with AsyncSessionLocal() as session:
            await save_and_publish_rates(rates, session)
    except Exception as e:
        print(f"[Manual Task] Error: {e}")