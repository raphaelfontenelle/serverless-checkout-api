"""
FastAPI application for the checkout service.

This is the delivery layer. It exposes a login endpoint that issues a
JWT, and a protected POST /checkout endpoint that calculates order
totals and persists each checkout. Validation lives in the Pydantic
models, calculation in the calculator, and storage behind the
repository abstraction.
"""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from mangum import Mangum
from pydantic import BaseModel

from app.auth import authenticate_user, issue_token, require_valid_token
from app.calculator import compute_order_totals
from app.models import OrderPayload, OrderSummary
from app.persistence import (
    CheckoutRepository,
    DynamoDBCheckoutRepository,
    InMemoryCheckoutRepository,
    build_checkout_record,
)

api = FastAPI(
    title="Checkout Service",
    description="Calculates and stores checkout totals for a list of items.",
    version="1.0.0",
)


@lru_cache
def get_repository() -> CheckoutRepository:
    """Provide the repository used to store checkouts.

    The choice is driven by an environment variable so tests can swap in
    the in-memory implementation while a real deployment uses DynamoDB.
    lru_cache keeps a single instance alive across requests.
    """
    backend = os.environ.get("STORAGE_BACKEND", "memory")
    if backend == "dynamodb":
        return DynamoDBCheckoutRepository()
    return InMemoryCheckoutRepository()


class LoginRequest(BaseModel):
    """Credentials submitted to obtain an access token."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """The access token returned after a successful login."""

    access_token: str
    token_type: str = "bearer"


@api.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest) -> TokenResponse:
    """Exchange valid credentials for a signed access token."""
    if not authenticate_user(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = issue_token(credentials.username)
    return TokenResponse(access_token=token)


@api.post("/checkout", response_model=OrderSummary)
def create_checkout(
    payload: OrderPayload,
    username: str = Depends(require_valid_token),
    repository: CheckoutRepository = Depends(get_repository),
) -> OrderSummary:
    """Calculate the totals for a checkout and persist the result.

    The token dependency rejects unauthenticated requests with 401.
    After the totals are computed, a record is stored through the
    repository so there is an auditable history of every checkout.
    """
    line_items = [item.model_dump() for item in payload.items]
    totals = compute_order_totals(line_items)

    record = build_checkout_record(line_items, totals, username)
    repository.save(record)

    return OrderSummary(**totals)


# Mangum adapts the FastAPI application to the AWS Lambda and API Gateway
# event format. When the code runs locally with uvicorn this handler is
# simply unused, so the same file works in both places.
handler = Mangum(api)
