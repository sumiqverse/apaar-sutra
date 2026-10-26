import React, { useState } from "react";
import {
  Code,
  FileCode,
  Download,
  Terminal,
  Shield,
  Key,
  Clock,
  Layers,
  Copy,
  Check,
  ExternalLink,
  BookOpen,
  AlertCircle,
  Hash,
} from "lucide-react";

export const DeveloperDocs: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"specs" | "errors" | "hmac" | "kits">("specs");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [errorSearch, setErrorSearch] = useState<string>("");

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const errorCatalog = [
    { code: "UNAUTHORIZED", status: 401, desc: "Missing, expired, or invalid bearer token or HMAC signature.", fix: "Re-authenticate or check HMAC secret and key_id." },
    { code: "TOKEN_EXPIRED", status: 401, desc: "JWT access token has passed expiration TTL.", fix: "Invoke /api/v1/auth/refresh with refresh token." },
    { code: "FORBIDDEN", status: 403, desc: "User or API client lacks sufficient role or scope privileges.", fix: "Request required scope (e.g., 'students:write' or SUPER_ADMIN)." },
    { code: "NOT_FOUND", status: 404, desc: "The requested student, batch, report, or institution does not exist.", fix: "Verify resource UUID and tenant ownership." },
    { code: "VALIDATION_ERROR", status: 422, desc: "Request payload failed Pydantic schema validation.", fix: "Review response details array and correct field types." },
    { code: "INVALID_APAAR_FORMAT", status: 400, desc: "12-digit APAAR ID failed Verhoeff checksum algorithm.", fix: "Verify APAAR ID syntax and national ID checksum digit." },
    { code: "APAAR_REGISTRY_UNAVAILABLE", status: 503, desc: "National ABC/APAAR Identity Registry did not respond.", fix: "Retry with exponential backoff or use async queue." },
    { code: "DUPLICATE_ENROLMENT", status: 409, desc: "Student already has an active full-time enrolment for this year.", fix: "Review AICTE dual-enrolment policy; issue transfer NOC." },
    { code: "INTAKE_CAPACITY_EXCEEDED", status: 422, desc: "Admission breaches sanctioned AICTE intake capacity.", fix: "Verify quota categorization (supernumerary / EWS / TFW)." },
    { code: "HMAC_SIGNATURE_MISMATCH", status: 401, desc: "Computed request signature does not match X-Signature header.", fix: "Check canonical string format: METHOD\\nPATH\\nTIMESTAMP\\nNONCE\\nBODY_HASH." },
    { code: "HMAC_TIMESTAMP_EXPIRED", status: 401, desc: "X-Timestamp drift exceeds maximum allowable window (300s).", fix: "Synchronize local server clock via NTP." },
    { code: "IDEMPOTENCY_CONFLICT", status: 409, desc: "Concurrent request with identical Idempotency-Key is processing.", fix: "Wait for initial batch to finish or generate unique key." },
    { code: "REPORT_HASH_MISMATCH", status: 400, desc: "Report SHA-256 hash not recognized in official verification ledger.", fix: "Verify genuine unaltered report export from platform." },
    { code: "RATE_LIMIT_EXCEEDED", status: 429, desc: "Request volume exceeds configured limit per minute.", fix: "Throttle calls; inspect X-RateLimit-Reset header." },
  ];

  const filteredErrors = errorCatalog.filter(
    (e) =>
      e.code.toLowerCase().includes(errorSearch.toLowerCase()) ||
      e.desc.toLowerCase().includes(errorSearch.toLowerCase())
  );

  const pythonSnippet = `import hmac, hashlib, time, json, urllib.request, uuid

def make_signed_request(url, path, client_id, secret, payload):
    timestamp = str(int(time.time()))
    nonce = f"n_{uuid.uuid4().hex[:16]}"
    body_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    
    # Canonical String: METHOD\\nPATH\\nTIMESTAMP\\nNONCE\\nBODY_HASH
    canonical = f"POST\\n{path}\\n{timestamp}\\n{nonce}\\n{body_hash}"
    sig = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Client-ID": client_id,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": sig,
        "Idempotency-Key": f"idemp_{uuid.uuid4().hex}"
    }
    req = urllib.request.Request(f"{url}{path}", data=body_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())`;

  const nodeSnippet = `const crypto = require('crypto');

function signRequest(method, path, bodyString, secret, clientId) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = 'n_' + crypto.randomBytes(8).toString('hex');
  const bodyHash = crypto.createHash('sha256').update(bodyString, 'utf8').digest('hex');
  
  const canonicalString = \`\${method.toUpperCase()}\\n\${path}\\n\${timestamp}\\n\${nonce}\\n\${bodyHash}\`;
  const signature = crypto.createHmac('sha256', secret).update(canonicalString, 'utf8').digest('hex');
  
  return {
    'X-Client-ID': clientId,
    'X-Timestamp': timestamp,
    'X-Nonce': nonce,
    'X-Signature': signature,
    'Idempotency-Key': 'idemp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6)
  };
}`;

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-600/10 text-blue-600 dark:text-blue-400 rounded-xl">
              <Code className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Developer Documentation & OpenAPI
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                System-to-system ERP APIs, HMAC-SHA256 signatures, error catalogue, and integration kits.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/api/v1/openapi.json"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition"
          >
            <Download className="w-4 h-4 text-slate-400" />
            Raw openapi.json
          </a>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition shadow-sm"
          >
            <ExternalLink className="w-4 h-4" />
            Interactive Swagger UI
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("specs")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 ${
            activeTab === "specs"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Interactive API Explorer
        </button>
        <button
          onClick={() => setActiveTab("hmac")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 ${
            activeTab === "hmac"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Key className="w-4 h-4" />
          HMAC Auth & Security Protocol
        </button>
        <button
          onClick={() => setActiveTab("errors")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 ${
            activeTab === "errors"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <AlertCircle className="w-4 h-4" />
          Error Catalogue ({errorCatalog.length})
        </button>
        <button
          onClick={() => setActiveTab("kits")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 ${
            activeTab === "kits"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Terminal className="w-4 h-4" />
          Integration Kit & Connectors
        </button>
      </div>

      {/* TAB 1: API SPECS / REDOC EMBED */}
      {activeTab === "specs" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <div className="text-xs text-slate-400 uppercase font-semibold">Versioning Policy</div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white mt-1">
                Canonical Base: /api/v1/
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Backward compatible. Deprecations signaled via Sunset HTTP headers 6 months in advance.
              </p>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <div className="text-xs text-slate-400 uppercase font-semibold">Rate Limiting</div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white mt-1">
                1000 req / min (Sliding Window)
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Tracked via X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers.
              </p>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <div className="text-xs text-slate-400 uppercase font-semibold">Idempotency Guarantee</div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white mt-1">
                Idempotency-Key Header
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Guarantees exactly-once batch ingestion semantics on network retries without duplicates.
              </p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 dark:text-white text-sm">
                Embedded API Documentation & Schema Explorer
              </h3>
              <span className="text-xs text-indigo-500 font-mono">OpenAPI 3.1.0</span>
            </div>
            <div className="h-[600px] w-full">
              <iframe
                src="/docs"
                title="API Spec Documentation"
                className="w-full h-full border-0 bg-slate-50 dark:bg-slate-950"
              />
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: HMAC AUTH */}
      {activeTab === "hmac" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
              System-to-System HMAC-SHA256 Protocol
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
              Requests to <code className="font-mono text-indigo-500">/api/v1/integration/students</code> must be signed using the institutional API secret.
            </p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Required Headers
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl">
                    <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">X-Client-ID</span>
                    <p className="text-slate-500 dark:text-slate-400 mt-0.5">Your institutional API client ID issued in the Admin Console.</p>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl">
                    <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">X-Timestamp</span>
                    <p className="text-slate-500 dark:text-slate-400 mt-0.5">Current UTC epoch in seconds. Server rejects drift {'>'} 300 seconds.</p>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl">
                    <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">X-Nonce</span>
                    <p className="text-slate-500 dark:text-slate-400 mt-0.5">Unique random string per request to prevent replay attacks.</p>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl">
                    <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">X-Signature</span>
                    <p className="text-slate-500 dark:text-slate-400 mt-0.5">Hex-encoded HMAC-SHA256 signature of the canonical string.</p>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl">
                    <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">Idempotency-Key</span>
                    <p className="text-slate-500 dark:text-slate-400 mt-0.5">UUID or unique identifier enabling safe retries without double insertions.</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Python 3 Implementation
                  </h4>
                  <button
                    onClick={() => copyCode(pythonSnippet, "py")}
                    className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-600 font-semibold"
                  >
                    {copiedCode === "py" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedCode === "py" ? "Copied" : "Copy"}
                  </button>
                </div>
                <pre className="p-4 rounded-xl bg-slate-950 text-slate-200 text-xs font-mono overflow-x-auto leading-relaxed max-h-80">
                  {pythonSnippet}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ERROR CATALOGUE */}
      {activeTab === "errors" && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Platform Error Catalogue & Remediation Guide
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Detailed catalogue of platform errors adhering to RFC 7807 problem details specification.
              </p>
            </div>

            <div className="relative w-full sm:w-72">
              <input
                type="text"
                placeholder="Search error codes or symptoms..."
                value={errorSearch}
                onChange={(e) => setErrorSearch(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/60 uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">Error Code</th>
                  <th className="py-3 px-4">HTTP Status</th>
                  <th className="py-3 px-4">Cause Description</th>
                  <th className="py-3 px-4">Recommended Client Remediation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredErrors.map((err) => (
                  <tr key={err.code} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                      {err.code}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        err.status === 401 || err.status === 403
                          ? "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300"
                          : err.status === 409 || err.status === 422
                          ? "bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                      }`}>
                        {err.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                      {err.desc}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400">
                      {err.fix}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: INTEGRATION KIT */}
      {activeTab === "kits" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="p-2.5 rounded-xl bg-orange-500/10 text-orange-500 w-fit">
                <Terminal className="w-5 h-5" />
              </div>
              <h4 className="font-semibold text-slate-900 dark:text-white text-sm">
                Postman Collection
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Collection v2.1 with pre-request HMAC signing script and staging environment.
              </p>
              <div className="pt-2">
                <span className="text-[11px] font-mono text-slate-400">/integration-kit/apaar_sutra_postman_collection.json</span>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500 w-fit">
                <Code className="w-5 h-5" />
              </div>
              <h4 className="font-semibold text-slate-900 dark:text-white text-sm">
                Python Client Snippet
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Production-ready Python client with RFC 8785 canonical JSON and status polling.
              </p>
              <div className="pt-2">
                <span className="text-[11px] font-mono text-slate-400">/integration-kit/python_client_example.py</span>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-500 w-fit">
                <FileCode className="w-5 h-5" />
              </div>
              <h4 className="font-semibold text-slate-900 dark:text-white text-sm">
                Sample ERP Connector
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Delta-sync SQLite connector extracting records and pushing with retry backoff.
              </p>
              <div className="pt-2">
                <span className="text-[11px] font-mono text-slate-400">/integration-kit/sample_erp_connector.py</span>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-500 w-fit">
                <Layers className="w-5 h-5" />
              </div>
              <h4 className="font-semibold text-slate-900 dark:text-white text-sm">
                Local Webhook Receiver
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Lightweight HTTP server verifying incoming X-Signature webhook deliveries.
              </p>
              <div className="pt-2">
                <span className="text-[11px] font-mono text-slate-400">/integration-kit/webhook_local_receiver.py</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default DeveloperDocs;
