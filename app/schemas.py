"""Request and response bodies. Limits live on the input models only."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, StringConstraints, model_validator

MAX_ID = 2**63 - 1
NO_NUL = r"^[^\x00]*$"

Id = Annotated[int, Field(gt=0, le=MAX_ID)]
Cents = Annotated[int, Field(ge=0, le=10_000_000)]  # 249 = 2.49, at most 100,000 in any currency
Currency = Literal["EUR", "USD", "GBP"]
Sku = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{8,64}$"), AfterValidator(str.lower)]


class CategoryWrite(BaseModel, extra="forbid"):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=100, pattern=NO_NUL)
    ]
    parent_id: Annotated[Id, Field(strict=True)] | None = None  # None = top-level category


class CategoryRead(BaseModel):
    id: int
    name: str
    parent_id: int | None
    created_at: datetime
    updated_at: datetime


class ProductWrite(BaseModel, extra="forbid"):
    sku: Sku
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=NO_NUL)]
    description: Annotated[str, StringConstraints(max_length=2_000, pattern=NO_NUL)] = ""
    image_url: HttpUrl | None = None
    price: Annotated[Cents, Field(strict=True)]
    currency: Currency = "EUR"
    category_id: Annotated[Id, Field(strict=True)]


class ProductRead(BaseModel):
    id: int
    sku: str
    title: str
    description: str
    image_url: str | None
    price: int
    currency: Currency
    category_id: int
    created_at: datetime
    updated_at: datetime


class PageParams(BaseModel, extra="forbid"):
    page: Annotated[int, Field(ge=1, le=100)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20


class SearchParams(PageParams):
    q: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100, pattern=NO_NUL)] | None = (
        Field(default=None, description="At least 3 characters. Title contains it (case-insensitive)")
    )
    sku: Sku | None = Field(default=None, description="Exact SKU (case-insensitive)")
    category_id: Id | None = Field(default=None, description="That category or any subcategory")
    currency: Currency | None = Field(default=None, description="Required with min_price or max_price")
    min_price: Cents | None = Field(default=None, description="Inclusive, in cents")
    max_price: Cents | None = Field(default=None, description="Inclusive, in cents")

    @model_validator(mode="after")
    def check_price_range(self) -> Self:
        if self.currency is None and (self.min_price is not None or self.max_price is not None):
            raise ValueError("currency is required with min_price or max_price")
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price can't be greater than max_price")
        return self


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorRead(BaseModel):
    detail: str
