from sqlalchemy import Column, Integer, String, Numeric, Date
from .base import Base

class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id = Column(Integer, primary_key=True, index=True)
    char_code = Column(String(3), index=True)
    num_code = Column(String(3))
    nominal = Column(Integer)
    name = Column(String)
    value = Column(Numeric(10, 4))
    date = Column(Date, index=True)