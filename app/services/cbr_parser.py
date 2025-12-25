import httpx
from datetime import date
from xml.etree import ElementTree as ET
from typing import List
from ..schemas.currency import CurrencyRateCreate
import asyncio

async def fetch_rates_from_cbr(target_date: date = None) -> List[CurrencyRateCreate]:
    if target_date is None:
        target_date = date.today()
    date_str = target_date.strftime("%d/%m/%Y")
    url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={date_str}"

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
            return parse_xml(response.text, target_date)

        except httpx.ConnectTimeout:
            if attempt == 2:
                raise
            await asyncio.sleep(2)

    return parse_xml(response.text, target_date)

def parse_xml(xml_data: str, effective_date: date) -> List[CurrencyRateCreate]:
    root = ET.fromstring(xml_data)
    rates = []
    for valute in root.findall("Valute"):
        char_code = valute.find("CharCode").text
        num_code = valute.find("NumCode").text
        nominal = int(valute.find("Nominal").text)
        name = valute.find("Name").text
        value_str = valute.find("Value").text.replace(",", ".")
        value = float(value_str)

        rates.append(CurrencyRateCreate(
            char_code=char_code,
            num_code=num_code,
            nominal=nominal,
            name=name,
            value=value,
            date=effective_date
        ))
    return rates