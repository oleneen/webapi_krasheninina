from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.base import get_db
from ..db.models import CurrencyRate
from ..schemas.currency import CurrencyRateCreate, CurrencyRateOut
from ..tasks.background import manual_fetch_task
from ..ws.manager import manager
from ..nats_client.handlers import publish_rate_event
from ..schemas.currency import CurrencyRateUpdate

router = APIRouter(prefix="/rates", tags=["rates"])

@router.get("/", response_model=list[CurrencyRateOut])
async def get_rates(char_code: str = None, db: AsyncSession = Depends(get_db)):
    query = select(CurrencyRate)
    if char_code:
        query = query.where(CurrencyRate.char_code == char_code)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{char_code}", response_model=list[CurrencyRateOut])
async def get_rates_by_char_code(
    char_code: str,
    db: AsyncSession = Depends(get_db)
):
    query = select(CurrencyRate).where(CurrencyRate.char_code == char_code)
    result = await db.execute(query)
    rates = result.scalars().all()
    if not rates:
        raise HTTPException(status_code=404, detail="No rates found for this currency")
    return rates

@router.get("/{rate_id}", response_model=CurrencyRateOut)
async def get_rate(rate_id: int, db: AsyncSession = Depends(get_db)):
    rate = await db.get(CurrencyRate, rate_id)
    if not rate:
        raise HTTPException(404, "Rate not found")
    return rate

@router.post("/", response_model=CurrencyRateOut, status_code=201)
async def create_rate(rate: CurrencyRateCreate, db: AsyncSession = Depends(get_db)):
    db_rate = CurrencyRate(**rate.dict())
    db.add(db_rate)
    await db.commit()
    await db.refresh(db_rate)

    await publish_rate_event({
        "id": db_rate.id,
        "char_code": db_rate.char_code,
        "value": float(db_rate.value),
        "date": db_rate.date.isoformat()
    })
    return db_rate

@router.patch("/{rate_id}", response_model=CurrencyRateOut)
async def update_rate(
    rate_id: int,
    rate: CurrencyRateUpdate,
    db: AsyncSession = Depends(get_db)
):
    db_rate = await db.get(CurrencyRate, rate_id)
    if not db_rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    update_data = rate.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_rate, field, value)

    await db.commit()
    await db.refresh(db_rate)

    await publish_rate_event({
        "event": "rate_updated",
        "id": db_rate.id,
        "char_code": db_rate.char_code,
        "value": float(db_rate.value),
        "date": db_rate.date.isoformat()
    })

    return db_rate

@router.delete("/{rate_id}", status_code=204)
async def delete_rate(rate_id: int, db: AsyncSession = Depends(get_db)):
    db_rate = await db.get(CurrencyRate, rate_id)
    if not db_rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    await db.delete(db_rate)
    await db.commit()

    await publish_rate_event({
        "event": "rate_deleted",
        "id": db_rate.id,
        "char_code": db_rate.char_code,
        "date": db_rate.date.isoformat()
    })

@router.post("/tasks/run")
async def run_fetch_task(background_tasks: BackgroundTasks):
    background_tasks.add_task(manual_fetch_task)
    return {"status": "fetch task started"}