from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from time import struct_time


class DisplayState(Enum):
    """Enum to store the display state of the checklist"""

    Hidden = 1
    Public = 2


@dataclass
class Checklist:
    """Class to store the checklist data"""

    id: str
    user: str
    start_time: struct_time
    duration: int
    """In minutes"""
    region: str
    subregion: str
    subregion2: Optional[str]
    subregion3: Optional[str]
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    observation: List["Observation"]

    complete: bool
    quantity_exact: bool


@dataclass
class CNReportChecklist(Checklist):
    version: str
    serial_id: str
    display_state: DisplayState


class EBirdChecklist(Checklist):
    """Class to store the eBird checklist data"""

    protocol: str
    distance: Optional[float]
    area: Optional[float]


@dataclass
class Observation:
    """Class to store the observation data"""

    common_name: str
    scientific_name: str
    count: int
    species_code: str
    observed_on: struct_time
    observed_at: str
    location: str
    lat: float
    lng: float
    user: str
    checklist_id: int
