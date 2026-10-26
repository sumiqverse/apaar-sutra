# APAAR-Sutra Integration Kit & Adapter Guide

Welcome to the **APAAR-Sutra Integration Kit**. This toolkit provides institutional software vendors, campus ERP administrators, and AICTE technical teams with the client libraries, sample connectors, Postman artifacts, and adapter specifications needed to integrate external systems with the APAAR-Sutra statutory compliance engine.

---

## Contents of this Directory

| File | Purpose |
| :--- | :--- |
| `apaar_sutra_postman_collection.json` | Ready-to-import Postman v2.1 collection with automated HMAC signing pre-request script. |
| `apaar_sutra_postman_environment.json` | Postman environment pre-configured with local & staging variables. |
| `python_client_example.py` | Standalone Python 3 client illustrating HMAC signing, batch upload, and status polling. |
| `node_client_example.js` | Standalone Node.js client using standard `crypto` and `http` modules. |
| `sample_erp_connector.py` | Complete ERP connector that extracts student records from an SQLite DB and pushes with delta-sync. |
| `webhook_local_receiver.py` | Lightweight Python HTTP server to test and verify incoming webhook event delivery and HMAC signatures. |
| `README.md` | This technical guide, adapter architecture, and SSO federation documentation. |

---

## 1. Authentication: System-to-System HMAC-SHA256

Campus ERPs authenticate with APAAR-Sutra using HMAC-SHA256 signatures over request metadata and body. This prevents credential compromise and guarantees payload integrity.

### Required HTTP Headers

```http
POST /api/v1/integration/students HTTP/1.1
Host: api.apaar-sutra.gov.in
Content-Type: application/json
X-Client-ID: erp_demo_client_001
X-Timestamp: 1730000000
X-Nonce: n_4f9a2b1c8e3d07aa
X-Signature: c8b9e691866db4ad328e...
Idempotency-Key: idemp_1730000000_abc123
```

### Signature Computation Algorithm

1. **Calculate Body Hash:**
   $$\text{body\_hash} = \text{SHA256}(\text{raw\_utf8\_body})$$
   *(If request has no body, use the SHA-256 hash of empty bytes `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`)*

2. **Construct Canonical String:**
   Join uppercase HTTP method, request path, timestamp, nonce, and body hash separated by newline (`\n`):
   ```
   POST
   /api/v1/integration/students
   1730000000
   n_4f9a2b1c8e3d07aa
   5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8
   ```

3. **Compute HMAC-SHA256:**
   $$\text{X-Signature} = \text{HMAC-SHA256}(\text{client\_secret}, \text{canonical\_string})$$

4. **Replay Defense & Clock Drift:**
   - Server allows timestamp drift within $\pm 300$ seconds (5 minutes).
   - Each `X-Nonce` is single-use and tracked in Redis / in-memory cache for 5 minutes.

---

## 2. Sample ERP Connector & Delta-Sync

The sample connector demonstrates syncing from campus databases (Banner, PeopleSoft, SAP Student Lifecycle, or homegrown SQL systems).

### Running the Connector

```bash
# 1. Start local webhook receiver (optional, for event notifications)
python webhook_local_receiver.py --port 9000

# 2. Run delta synchronization (only syncs records changed since last sync)
python sample_erp_connector.py --mode delta --url http://localhost:8000

# 3. Run full synchronization
python sample_erp_connector.py --mode full --url http://localhost:8000
```

### Delta-Sync Mechanism
The connector queries records where:
$$\text{sync\_status} \neq \text{'SYNCED'} \quad \text{OR} \quad \text{updated\_at} > \text{last\_synced\_at}$$
Upon receiving an HTTP 200 response, it commits `sync_status = 'SYNCED'` and timestamps `last_synced_at = NOW()`.

---

## 3. Webhook Event System

Institutions and AICTE officers can register Webhook Subscriptions to receive real-time push events.

### Supported Events
- `batch.completed`: Fired when an asynchronous or API student batch finishes processing.
- `alert.created`: Triggered when an intake overshoot or duplicate enrolment anomaly is detected.
- `record.revoked`: Triggered when a credential or enrolment is marked revoked or invalid.
- `consent.updated`: Triggered when a student modifies DPDP consent preferences.

### HMAC Signature Verification
Every webhook delivery includes an `X-Signature` header:
```http
X-Signature: sha256=1234567890abcdef...
X-APAAR-Event: batch.completed
X-Delivery-ID: f81d4fae-7dec-11d0-a765-00a0c91e6bf6
```
Recipient verification snippet (Python):
```python
import hmac, hashlib
expected = "sha256=" + hmac.new(sub_secret.encode(), raw_request_body, hashlib.sha256).hexdigest()
if not hmac.compare_digest(request.headers.get("X-Signature"), expected):
    return 401, "Invalid Signature"
```

### Retry Schedule & Dead-Letter Queue (DLQ)
- Delays: **30s**, **2 min**, **10 min**, **30 min**, **2 hours**.
- If all 5 attempts fail, status transitions to `DEAD_LETTER`.
- Super Admins can inspect and re-deliver DLQ items in the Admin Console (`/admin`).

---

## 4. Upstream APAAR / ABC Registry Adapter

To connect the platform to the live Government of India APAAR/ABC National Registry, implement the `ApaarProvider` abstract interface located in `backend/app/integrations/apaar.py`:

```python
from app.integrations.apaar import ApaarProvider, ApaarVerifyResult

class NationalApaarRegistryAdapter(ApaarProvider):
    """Production adapter communicating with Government APAAR/ABC National Portal."""

    def __init__(self, api_endpoint: str, cert_path: str, private_key_path: str):
        self.endpoint = api_endpoint
        self.cert = (cert_path, private_key_path) # mTLS client certificate

    async def verify_id(self, apaar_id: str, student_name: str, dob: date) -> ApaarVerifyResult:
        # 1. Establish mTLS session
        # 2. Encrypt PII payload using NIC Public RSA Key (PKCS#1 v2.1)
        # 3. Post to Government gateway /api/v2/student/verify
        # 4. Decrypt response and return standardized ApaarVerifyResult
        ...
```

### Configuration Switches (`.env`)
```ini
APAAR_PROVIDER_TYPE=live          # 'mock' (default) or 'live'
APAAR_API_GATEWAY_URL=https://api.abc.gov.in/v2
APAAR_MTLS_CERT_PATH=/etc/ssl/certs/apaar_client.crt
APAAR_MTLS_KEY_PATH=/etc/ssl/private/apaar_client.key
```

---

## 5. AICTE Portal SSO Integration (OIDC & SAML 2.0)

APAAR-Sutra supports single sign-on (SSO) federation with the central AICTE Portal.

### OIDC Adapter Interface
The platform's authentication provider implements standard OpenID Connect Authorization Code Flow with PKCE:

```
[ AICTE Officer Browser ]
        │
        │ 1. GET /api/v1/auth/sso/aicte/login
        ▼
[ APAAR-Sutra Auth Router ] ─── 2. Redirect to AICTE IDP with client_id, nonce, code_challenge ───► [ Central AICTE IdP ]
                                                                                                        │
[ APAAR-Sutra Auth Router ] ◄── 3. Redirect back with auth code & state ──────────────────────────────┘
        │
        ├── 4. Token exchange (POST /token) with client_secret
        ├── 5. Validate ID Token JWT signature against AICTE JWKS
        ├── 6. Extract claims: sub, email, aicte_role, institution_code
        └── 7. Issue APAAR-Sutra session token & redirect to Dashboard
```

### Claims Mapping
| AICTE IdP Claim | APAAR-Sutra Attribute | Role Mapping |
| :--- | :--- | :--- |
| `aicte_officer_id` | `User.id` | `REGULATOR` |
| `role: "SUPER_ADMIN"` | `User.role` | `SUPER_ADMIN` |
| `inst_code: "1-12345678"` | `User.institution_id` | Scopes user to specific institution |

### SAML 2.0 Note for Legacy Institutions
For state universities and legacy autonomous institutions utilizing Shibboleth or Active Directory Federation Services (ADFS), configure the SAML 2.0 Service Provider (SP) module in `backend/app/integrations/saml_sp.py`. Metadata XML is published at `/auth/saml/metadata.xml`.
