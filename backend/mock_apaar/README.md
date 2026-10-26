# Mock National APAAR Gateway Service

> **IMPORTANT NOTICE**:  
> **This simulates the ABC/DigiLocker APAAR verification API for the hackathon; production will use an official provider.**

---

## Overview
This standalone microservice mimics the national DigiLocker / Academic Bank of Credits (ABC) APAAR ID verification infrastructure. It provides institutional clients with high-fidelity responses, fuzzy name matching, date-of-birth validation, batch verification capabilities, and configurable network simulation toggles (artificial latency and simulated outage failure rates).

## Features
- **Authoritative Pre-loaded Registry**: Ingests `data/apaar_registry.json` containing 10,000 synthetic student identities.
- **Single Verification**: `POST /apaar/verify` validating APAAR ID, name match score (0–100), and DOB conformity.
- **Bulk Batch Verification**: `POST /apaar/verify-batch` supporting up to 500 records in a single payload.
- **Chaos Engineering & Resilience Simulation**:
  - `APAAR_MOCK_LATENCY_MS`: Injects artificial network latency.
  - `APAAR_MOCK_FAILURE_RATE`: Injects random HTTP 503 / 500 error rates to test client-side retry policies and circuit breakers.
- **API Key Security**: Rejects unauthenticated traffic missing valid `X-API-Key` or `Authorization: Bearer <key>`.

## Running Locally
```bash
uvicorn mock_apaar.server:mock_apaar_app --host 0.0.0.0 --port 8001 --reload
```

## Running via Docker
```bash
docker build -t mock-apaar -f mock_apaar/Dockerfile .
docker run -p 8001:8001 -e APAAR_MOCK_API_KEY=mock-apaar-secret-key-2026 mock-apaar
```
