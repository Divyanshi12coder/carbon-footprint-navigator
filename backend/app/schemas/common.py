import re
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

Category = Literal["transport", "flights", "energy", "food", "waste", "consumption", "digital", "business", "other"]
RangeKey = Literal["7d", "30d", "90d", "180d", "365d", "custom"]
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageOut(BaseModel):
    detail: str
