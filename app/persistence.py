"""
Persistence layer for the checkout service.

This module defines a small repository abstraction for storing checkout
records, plus two implementations: one backed by DynamoDB for real use,
and an in-memory one used in tests. The endpoint depends on the
abstraction, so the storage backend can change without touching the
business logic.
"""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

import boto3


def build_checkout_record(
    line_items: List[dict], totals: dict, username: str
) -> dict:
    """Assemble the record that will be persisted for a checkout.

    A unique id and a UTC timestamp are generated here so every stored
    checkout is uniquely identifiable and ordered in time.
    """
    return {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "username": username,
        "items": line_items,
        "subtotal": totals["subtotal"],
        "taxes": totals["taxes"],
        "discount": totals["discount"],
        "total": totals["total"],
    }


class CheckoutRepository(ABC):
    """Contract for storing checkout records.

    Any concrete repository must be able to save a record. Keeping this
    as an abstract base lets the rest of the app depend on the contract
    rather than a specific database.
    """

    @abstractmethod
    def save(self, record: dict) -> None:
        """Persist a single checkout record."""
        raise NotImplementedError


class InMemoryCheckoutRepository(CheckoutRepository):
    """A repository that keeps records in a list.

    Used in tests so they run without any external service. The stored
    records can be inspected to assert that a checkout was persisted.
    """

    def __init__(self) -> None:
        self.records: List[dict] = []

    def save(self, record: dict) -> None:
        self.records.append(record)


class DynamoDBCheckoutRepository(CheckoutRepository):
    """A repository that stores records in a DynamoDB table.

    The table name comes from the environment so the same code works
    across different deployments. DynamoDB does not accept float values,
    so monetary Decimals are stored as strings and can be parsed back
    when read.
    """

    def __init__(self, table_name: str = None) -> None:
        resolved_name = table_name or os.environ["CHECKOUT_TABLE_NAME"]
        self.table = boto3.resource("dynamodb").Table(resolved_name)

    def save(self, record: dict) -> None:
        # Convert Decimal amounts to strings so DynamoDB accepts them and
        # no precision is lost in the round trip.
        storable = dict(record)
        for field in ("subtotal", "taxes", "discount", "total"):
            storable[field] = str(record[field])
        storable["items"] = [
            {**item, "unit_price": str(item["unit_price"])}
            for item in record["items"]
        ]
        self.table.put_item(Item=storable)
