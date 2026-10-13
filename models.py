from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


@dataclass
class ScrapedGrant:
    source_name: str
    source_url: str
    source_external_id: str
    title: str
    program: str = ""
    source_closed: Optional[bool] = None
    funder: str = ""
    category: str = ""
    description: str = ""
    objectives: str = ""
    activities: str = ""
    beneficiaries: str = ""
    eligible_entities: str = ""
    territory: str = ""
    partners_required: str = ""
    amount_available: str = ""
    cofinancing: str = ""
    open_date: Optional[date] = None
    deadline: Optional[date] = None
    official_url: str = ""
    requirements: str = ""
    raw_text: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["open_date"] = self.open_date.isoformat() if self.open_date else None
        d["deadline"] = self.deadline.isoformat() if self.deadline else None
        return d
