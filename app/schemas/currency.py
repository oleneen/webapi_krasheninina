from datetime import date
from pydantic import BaseModel, Field
from typing import Optional

class CurrencyRateCreate(BaseModel):
    char_code: str = Field(example="RUB")
    num_code: str = Field(example="643")
    nominal: int = Field(example=1000)
    name: str = Field(example="Русский Рубль")
    value: float = Field(example=12.84)
    date: date

class CurrencyRateOut(CurrencyRateCreate):
    id: int

    class Config:
        from_attributes = True

class CurrencyRateUpdate(BaseModel):
    nominal: Optional[int] = None
    value: Optional[float] = None
    name: Optional[str] = None