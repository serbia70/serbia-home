from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


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

    def to_dict(self) -> dict:
        return asdict(self)
