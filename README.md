# Checkout Service

A small checkout service that calculates order totals for a list of
items. It exposes a single REST endpoint, protects it with JWT
authentication, persists every checkout, and is designed to run in a
distributed, serverless environment on AWS.

## What it does

The service receives a list of items, each with a name, a unit price and
a quantity, and returns the calculated totals:

- subtotal: the sum of unit price times quantity across all items
- taxes: 13 percent of the subtotal
- discount: 10 percent of the subtotal, applied only when the subtotal is
  strictly greater than 100
- total: subtotal plus taxes minus discount

All monetary values are rounded to two decimal places.

## Design decisions

The code is organised in layers, each with a single responsibility. This
keeps the business rules easy to find and change as requirements evolve,
which was a stated goal of the challenge.

- calculator.py holds the pure calculation logic. It has no framework or
  database code, so it can be tested in isolation and reused if the
  delivery mechanism changes.
- models.py defines the request and response shapes with Pydantic and
  enforces the input validation rules.
- auth.py provides the JWT authentication. It is stateless, so any
  instance can verify a request without sharing session state, which
  suits a distributed deployment.
- persistence.py defines a repository abstraction with two
  implementations: one backed by DynamoDB for real use and an in-memory
  one for tests. The endpoint depends on the abstraction, so the storage
  backend can change without touching the business logic.
- main.py wires everything together and exposes the endpoints.

### Money is handled with Decimal

Monetary calculations use Python's Decimal type rather than float. Float
cannot represent many decimal values exactly, which causes small errors
that accumulate and break accounting. Decimal keeps the arithmetic exact.

### Validation rules

- name must be present and not blank
- unit price must be zero or greater, so free items such as gifts are
  allowed, but negative prices are rejected
- quantity must be at least one, since an item in a checkout means the
  customer is taking at least one unit
- an empty items list is rejected, because a checkout with no items has
  no meaning

Invalid requests are rejected automatically with a clear error before
they reach the business logic.

## API

### POST /login

Exchanges credentials for a signed access token.

Request body:

    {
      "username": "admin",
      "password": "admin"
    }

Response:

    {
      "access_token": "a signed JWT",
      "token_type": "bearer"
    }

### POST /checkout

Calculates the totals for a checkout and stores the result. Requires a
valid bearer token in the Authorization header.

Request body:

    {
      "items": [
        { "name": "Book", "unit_price": 39.99, "quantity": 2 },
        { "name": "Pen", "unit_price": 5.00, "quantity": 1 }
      ]
    }

Response:

    {
      "subtotal": "84.98",
      "taxes": "11.05",
      "discount": "0.00",
      "total": "96.03"
    }

If the token is missing or invalid the service responds with 401. If the
request body fails validation it responds with 422.

## Running locally

Create a virtual environment and install the dependencies:

    pip install -r requirements.txt

Start the API:

    uvicorn app.main:api --port 8000

The interactive API documentation is then available at
http://localhost:8000/docs

### Trying it from the command line

Get a token:

    curl -X POST http://localhost:8000/login \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "admin"}'

Call the checkout endpoint with the token:

    curl -X POST http://localhost:8000/checkout \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer THE_TOKEN_FROM_LOGIN" \
      -d '{"items": [{"name": "Book", "unit_price": 39.99, "quantity": 2}]}'

### Optional user interface

A Streamlit interface is included as a bonus. With the API running, start
it in a second terminal:

    streamlit run ui.py

It lets you sign in, build a list of items, and see the calculated
totals. It reads the API location from the API_BASE_URL environment
variable, defaulting to the local server.

## Tests

The test suite covers the calculation logic, including edge cases such as
a subtotal at exactly the threshold, and the full API path including
authentication, validation and persistence. The in-memory repository is
injected in place of DynamoDB so the tests run without any external
service.

Run the tests with:

    pytest

## Configuration

The service reads its settings from environment variables, so the same
code runs unchanged across environments:

- JWT_SECRET: the secret used to sign and verify tokens
- STORAGE_BACKEND: memory for local use, or dynamodb for AWS
- CHECKOUT_TABLE_NAME: the DynamoDB table name when using dynamodb
- API_BASE_URL: used by the Streamlit interface to locate the API

## Deployment

The service is deployed to AWS as a serverless stack defined in
template.yaml and deployed with the AWS SAM CLI. The architecture is
distributed and scales automatically with no servers to manage:

- API Gateway receives requests and routes them to the function
- AWS Lambda runs the FastAPI application, adapted with Mangum
- DynamoDB stores the checkout records

Each request can be handled by any instance, which is what makes the
architecture distributed. Step by step deployment instructions are in
DEPLOY.md.

### Live endpoint

A live instance is available for evaluation:

    https://de4uyj31r0.execute-api.us-east-2.amazonaws.com

This endpoint is deployed for the review and will be decommissioned
afterwards. The demo credentials are admin and admin.

Example, get a token:

    curl -X POST https://de4uyj31r0.execute-api.us-east-2.amazonaws.com/login \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "admin"}'

Then call checkout with the returned token:

    curl -X POST https://de4uyj31r0.execute-api.us-east-2.amazonaws.com/checkout \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer THE_TOKEN" \
      -d '{"items": [{"name": "Book", "unit_price": 39.99, "quantity": 2}]}
