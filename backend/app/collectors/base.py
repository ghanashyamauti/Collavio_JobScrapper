from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from abc import ABC, abstractmethod


@dataclass
class RawJob:
    source_name: str
    external_id: Optional[str]
    title: str
    company: str
    apply_url: str
    location: Optional[str] = None
    city: Optional[str] = None
    is_remote: bool = False
    category: Optional[str] = None
    min_exp: Optional[float] = None
    max_exp: Optional[float] = None
    job_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None


class BaseCollector(ABC):
    name: str = "base"

    @abstractmethod
    def collect(self) -> List[RawJob]:
        """Collects and returns raw jobs from the target source."""
        pass
