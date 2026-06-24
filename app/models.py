"""
Request and response models for the checkout service.

These Pydantic models define the shape of the data the API accepts and
returns, and enforce the input validation rules. Invalid requests are
rejected automatically with a clear error before reaching the business
logic.
"""

from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field, field_validator


class LineItem(BaseModel):
    """A single line item in a checkout request."""

    # name must be present and not only whitespace.
    name: str = Field(min_length=1)

    # unit_price may be zero to allow free items such as gifts, but it
    # can never be negative.
    unit_price: Decimal = Field(ge=0)

    # quantity must be at least one. An item being checked out means the
    # customer is taking at least one unit of it.
    quantity: int = Field(ge=1)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        # Field(min_length=1) rejects an empty string, but a string made
        # only of spaces would still pass. Stripping catches that.
        if not value.strip():
            raise ValueError("name must not be blank")
        return value


class OrderPayload(BaseModel):
    """The full checkout request: a list of line items."""

    # min_length=1 rejects an empty list, since a checkout with no items
    # has no meaning.
    items: List[LineItem] = Field(min_length=1)


class OrderSummary(BaseModel):
    """The calculated order result returned to the caller."""

    subtotal: Decimal
    taxes: Decimal
    discount: Decimal
    total: Decimal
