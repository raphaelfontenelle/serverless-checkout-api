"""
Integration tests for the checkout API.

These tests exercise the full request path: authentication, validation,
calculation and persistence. The in-memory repository is injected in
place of DynamoDB so the tests run without any external service, and the
stored records can be inspected directly.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import api, get_repository
from app.persistence import InMemoryCheckoutRepository

# A single shared in-memory repository so a test can read back what the
# request stored.
test_repository = InMemoryCheckoutRepository()


def override_repository() -> InMemoryCheckoutRepository:
    return test_repository


# Replace the real repository dependency with the in-memory one.
api.dependency_overrides[get_repository] = override_repository

client = TestClient(api)


def get_auth_header() -> dict:
    """Log in with the demo account and return the auth header."""
    response = client.post(
        "/login", json={"username": "admin", "password": "admin"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_checkout_requires_authentication():
    # Without a token the request must be rejected.
    response = client.post(
        "/checkout",
        json={"items": [{"name": "Book", "unit_price": 50, "quantity": 1}]},
    )
    assert response.status_code == 401


def test_checkout_returns_correct_totals():
    response = client.post(
        "/checkout",
        json={"items": [{"name": "Monitor", "unit_price": 200, "quantity": 1}]},
        headers=get_auth_header(),
    )
    assert response.status_code == 200

    body = response.json()
    assert body["subtotal"] == "200.00"
    assert body["taxes"] == "26.00"
    assert body["discount"] == "20.00"
    assert body["total"] == "206.00"


def test_checkout_persists_a_record():
    # Clear any records from earlier tests so the count is predictable.
    test_repository.records.clear()

    client.post(
        "/checkout",
        json={"items": [{"name": "Book", "unit_price": 50, "quantity": 2}]},
        headers=get_auth_header(),
    )

    # Exactly one record should have been stored, carrying the totals and
    # the user who made the checkout.
    assert len(test_repository.records) == 1
    stored = test_repository.records[0]
    assert stored["username"] == "admin"
    # The in-memory repository keeps the Decimal as is. Only the DynamoDB
    # repository converts amounts to strings, so here we compare Decimals.
    assert stored["subtotal"] == Decimal("100.00")
    assert "id" in stored
    assert "created_at" in stored


def test_empty_items_list_is_rejected():
    response = client.post(
        "/checkout",
        json={"items": []},
        headers=get_auth_header(),
    )
    assert response.status_code == 422
