# APAAR-Sutra Platform Error Catalogue

This document enumerates all standard error codes, their corresponding HTTP status codes, cause descriptions, and recommended client remediation actions.

---

## Standard Error Response Schema

All error responses from the APAAR-Sutra API adhere to RFC 7807 (Problem Details for HTTP APIs) compatible JSON payloads:

```json
{
  "status_code": 400,
  "error_code": "INVALID_APAAR_FORMAT",
  "message": "The provided APAAR/ABC ID does not conform to the 12-digit format or failed the Verhoeff checksum algorithm.",
  "timestamp": "2026-10-27T00:00:00Z",
  "details": {
    "field": "apaar_id",
    "value_masked": "1234-****-5678",
    "rule": "VERHOEFF_CHECKSUM"
  }
}
```

---

## Error Codes Reference

| Error Code | HTTP Status | Description | Trigger Scenarios | Client Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `UNAUTHORIZED` | 401 Unauthorized | Missing, expired, or invalid bearer token / HMAC signature. | Missing `Authorization` header, invalid JWT claims, expired session, or incorrect HMAC secret. | Re-authenticate at `/api/v1/auth/login` or re-compute HMAC SHA-256 signature using assigned API key & secret. |
| `TOKEN_EXPIRED` | 401 Unauthorized | The access token has passed its expiration time (`exp`). | Access token TTL (typically 15-60 minutes) expired. | Use the refresh token endpoint `/api/v1/auth/refresh` to obtain a fresh access token without user credentials. |
| `FORBIDDEN` | 403 Forbidden | Authenticated user or API client lacks sufficient role/scope privileges. | Institution user attempting to access AICTE regulator reports; client missing `students:write` scope. | Ensure correct role is assigned (`SUPER_ADMIN`, `REGULATOR`, `INSTITUTION_ADMIN`) or request additional API client scopes. |
| `NOT_FOUND` | 404 Not Found | The requested resource (student, enrolment, batch, report, rule) does not exist. | Querying invalid UUID or an entity belonging to another institution. | Verify resource UUID and ensure the calling tenant owns or has permission to view the resource. |
| `VALIDATION_ERROR` | 422 Unprocessable Entity | Request payload schema validation failed (Pydantic / JSON schema). | Missing required fields, invalid date formats (`YYYY-MM-DD`), numbers out of range. | Check response `details` array and format inputs according to OpenAPI specification. |
| `INVALID_APAAR_FORMAT` | 400 Bad Request | APAAR/ABC ID is not 12 digits or fails Verhoeff / Luhn checksum check. | Typing error or non-numeric characters in APAAR input. | Validate APAAR ID format and checksum algorithm before submission. |
| `APAAR_REGISTRY_UNAVAILABLE` | 503 Service Unavailable | The upstream APAAR/ABC National Registry did not respond. | Government identity portal downtime or network timeout. | Retry with exponential backoff; use the asynchronous upload mode for automatic retries. |
| `DUPLICATE_ENROLMENT` | 409 Conflict | A student is already registered with an active full-time enrolment in the same academic year. | Student admitted to two institutions simultaneously. | Review AICTE dual-enrolment policy; initiate multi-institution NOC transfer or cancellation workflow. |
| `INTAKE_CAPACITY_EXCEEDED` | 422 Unprocessable Entity | Adding the student would breach AICTE sanctioned intake limits for the program. | Total regular admissions > approved intake. | Verify quota categorization; supernumerary (EWS, TFW, PMSSS, NRI) seats must be tagged with valid documentation. |
| `HMAC_SIGNATURE_MISMATCH` | 401 Unauthorized | The `X-Signature` header does not match the computed hash of the request body. | Incorrect secret key, altered payload after signing, or non-canonical JSON whitespace. | Use RFC 8785 canonical JSON formatting (sorted keys, no spaces) before HMAC-SHA256 calculation. |
| `HMAC_TIMESTAMP_EXPIRED` | 401 Unauthorized | The `X-Timestamp` header is more than 300 seconds (5 minutes) away from server time. | System clock skew or replay attempt. | Synchronize system clock via NTP. Generate fresh timestamps for each request. |
| `IDEMPOTENCY_CONFLICT` | 409 Conflict | An operation with the same `Idempotency-Key` is currently executing. | Concurrent requests sent with the identical idempotency key before the first completed. | Await completion of the initial request or use a unique idempotency key for distinct payloads. |
| `REPORT_GENERATION_FAILED` | 500 Internal Server Error | Asynchronous report compilation encountered a data or rendering error. | Database timeout or corrupted intermediate file. | Check `/api/v1/reports/history` for error details; retry report generation. |
| `REPORT_HASH_MISMATCH` | 400 Bad Request | The provided SHA-256 hash does not match any official report in the tamper-proof ledger. | Altered or forged PDF/XLSX export. | Re-download genuine report from `/api/v1/reports/download/{id}`. |
| `RATE_LIMIT_EXCEEDED` | 429 Too Many Requests | Client has exceeded the permitted requests per minute threshold. | Rapid automated polling without backoff. | Inspect `X-RateLimit-Reset` header and throttle outgoing requests accordingly. |
| `WEBHOOK_ENDPOINT_UNREACHABLE` | 502 Bad Gateway | The subscriber webhook URL did not respond with 2xx HTTP status within 10 seconds. | Target server down, DNS error, or firewall blocking inbound requests. | The platform will retry up to 5 times (exponential backoff: 30s, 2m, 10m, 30m, 2h) before moving payload to DLQ. |

---

## Rate Limiting & Quota Headers

All API responses include standardized rate-limiting headers:

| Header Name | Type | Description |
| :--- | :--- | :--- |
| `X-RateLimit-Limit` | Integer | Maximum permitted requests within the rolling window (e.g., `1000`). |
| `X-RateLimit-Remaining` | Integer | Remaining request quota in the current window. |
| `X-RateLimit-Reset` | Integer | Epoch timestamp (seconds) when quota refreshes. |
| `Retry-After` | Integer | Returned on HTTP 429 indicating seconds to wait before retrying. |

---

## API Versioning Policy

1. **Path-Based Versioning:** Current canonical endpoints are located under `/api/v1/`.
2. **Backward Compatibility:** Breaking schema changes (such as field removals or renaming) will trigger a major version increment (`/api/v2/`). Minor non-breaking additions (e.g., optional response fields) occur within `/api/v1/`.
3. **Deprecation Notice:** Deprecated endpoints will include an HTTP `Deprecation: true` header and `Sunset: <date>` header at least 6 months prior to decommissioning.
