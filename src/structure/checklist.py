from dataclasses import dataclass
from typing import List

from .observation import Observation


@dataclass
class Checklist:
    id: int
    name: str
    description: str
    created_at: str
    updated_at: str
    observations: List[Observation]
