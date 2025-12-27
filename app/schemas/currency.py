from datetime import date
from pydantic import BaseModel, Field
from typing import Optional

class CurrencyRateCreate(BaseModel):
    char_code: str = Field(example="BTC")
    num_code: str = Field(example="960")
    nominal: int = Field(example=1)
    name: str = Field(example="Биткоин")
    value: float = Field(example=6842370.50)
    date: date

class CurrencyRateOut(CurrencyRateCreate):
    id: int

    class Config:
        from_attributes = True

class CurrencyRateUpdate(BaseModel):
    nominal: Optional[int] = None
    value: Optional[float] = None
    name: Optional[str] = None