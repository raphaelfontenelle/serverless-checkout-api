# Deployment guide

These commands run on your own machine, where the AWS credentials are
configured. They build the application and deploy it to AWS as a
serverless stack.

## Prerequisites

You need the AWS SAM CLI and Docker installed. SAM uses Docker to build
the Python dependencies in an environment that matches Lambda.

Check they are present:

    sam --version
    docker --version

If SAM is not installed on macOS:

    brew install aws-sam-cli

## Step 1: Build

From the project root, build the application. SAM reads template.yaml,
installs the dependencies from requirements.txt, and packages everything.

    sam build

## Step 2: Deploy

Run the guided deploy the first time. It asks a few questions and saves
your answers for next time.

    sam deploy --guided

When prompted:

- Stack Name: checkout-service
- AWS Region: us-east-2 (the same region used for the Bedrock work)
- Parameter JwtSecret: enter a long random string
- Confirm changes before deploy: Y
- Allow SAM CLI IAM role creation: Y
- Disable rollback: N
- Save arguments to configuration file: Y

After it finishes, SAM prints the Outputs. Copy the ApiBaseUrl value.
That is the public URL of the service.

## Step 3: Test the deployed service

Get a token, replacing BASE_URL with the ApiBaseUrl from the outputs:

    curl -X POST BASE_URL/login \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "admin"}'

Call the checkout endpoint with the token:

    curl -X POST BASE_URL/checkout \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer THE_TOKEN" \
      -d '{"items": [{"name": "Book", "unit_price": 39.99, "quantity": 2}]}'

## Step 4: Point the UI at the deployed service (optional)

    export API_BASE_URL=BASE_URL
    streamlit run ui.py

## Tearing it down

When the service is no longer needed, remove every resource it created so
nothing keeps running:

    sam delete --stack-name checkout-service
