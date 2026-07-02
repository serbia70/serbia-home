import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from scraper.models import Listing


DATA_DIR = Path("site")


def listing_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def load_previous_listings() -> Dict[str, dict]:
    path = DATA_DIR / "listings.json"
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {item["id"]: item for item in data}
        return {item["id"]: item for item in data.get("listings", [])}
    except (json.JSONDecodeError, KeyError):
        return {}


def save_listings(listings: List[Listing]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    prev = load_previous_listings()

    for listing in listings:
        if listing.id in prev:
            listing.first_seen = prev[listing.id].get("first_seen", today)
        else:
            listing.first_seen = today

    all_items = {l.id: l.to_dict() for l in listings}
    output = {
        "updated_at": datetime.now().isoformat(),
        "total": len(all_items),
        "listings": sorted(all_items.values(), key=lambda x: x["price_eur"]),
    }
    with open(DATA_DIR / "listings.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return output
