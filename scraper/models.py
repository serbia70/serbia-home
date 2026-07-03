from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class PricePoint:
    date: str  # YYYY-MM-DD
    price: float


@dataclass
class Listing:
    id: str  # sha256 of url, for dedup
    title: str
    price_eur: float
    area_sqm: Optional[float] = None
    rooms: str = ""
    location: str = ""
    url: str = ""
    source: str = ""  # "4zida", "halo_oglasi", "kupujemprodajem"
    image_url: Optional[str] = None
    published_at: Optional[str] = None
    first_seen: str = ""  # YYYY-MM-DD
    price_history: Optional[List[dict]] = None  # [{"date": "2026-07-01", "price": 95000}, ...]

    def to_dict(self) -> dict:
        return asdict(self)
