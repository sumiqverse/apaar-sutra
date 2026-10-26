# APAAR-Sutra: 5-Minute Choreographed Finals Demo Script

**Project**: APAAR-Sutra: AICTE National Academic Registry & Verification Hub  
**Problem Statement**: SIH Problem 26263  
**Target Duration**: 05:00 Minutes (300 Seconds)  
**Roles Required**: 
- Presenter 1 (Narration & Business Impact / AICTE Regulatory Angle)
- Presenter 2 (Live Screen Operator / Click Actions & Technical Proof)

---

## Pre-Flight Checklist (T-minus 2 Minutes)
1. Run `make demo` or open [http://localhost:5173/demo-guide](http://localhost:5173/demo-guide) and click **"Reset Demo Data (< 3s)"**.
2. Verify browser tabs are open:
   - **Tab 1**: [http://localhost:5173/demo-guide](http://localhost:5173/demo-guide) (Demo Control Center)
   - **Tab 2**: [http://localhost:5173/](http://localhost:5173/) (AICTE National Directorate Dashboard)
   - **Tab 3**: [http://localhost:5173/institution-dashboard](http://localhost:5173/institution-dashboard) (IITM Mumbai Portal)
   - **Tab 4**: [http://localhost:5173/verifier](http://localhost:5173/verifier) (Verifier Portal)
   - **Tab 5**: [http://localhost:5173/student/consent](http://localhost:5173/student/consent) (Student Mobile Privacy Portal)
   - **Tab 6**: [http://localhost:5173/tamper-demo](http://localhost:5173/tamper-demo) (Cryptographic Tamper Demo)
3. Have file `/demo-assets/violation.csv` accessible on the desktop for immediate drag-and-drop.

---

## Detailed Minute-by-Minute Choreography

### (a) 0:00 – 0:20 (20 Seconds) — The Problem Hook
* **Interface**: Tab 2 (`/` AICTE National Dashboard)
* **Operator Action**:
  - Show the National Map and live counters. Cursor hovers over high-level intake vs enrolment numbers.
* **Spoken Lines (Presenter 1)**:
  > *"Respected Judges, India's higher education system enrols over 4 crore students across 15,000 institutions. Yet today, regulators face a silent multi-crore crisis: **ghost students**, **seat blocking across state borders**, and **counterfeit paper credentials**.*  
  > *Until now, AICTE relied on post-facto statistical summaries — by the time fraud was audited, degrees were already issued. Today, we introduce **APAAR-Sutra**: a real-time, zero-trust verification and anomaly detection engine powered by Verhoeff APAAR IDs and Ed25519 verifiable credentials."*

---

### (b) 0:20 – 1:00 (40 Seconds) — College Ingestion & Deterministic Validation
* **Interface**: Tab 3 (`/institution-dashboard` logged in as `director.iitm@aicte.gov.in`)
* **Operator Action**:
  - Point to Approved Intake for B.Tech CSE: **120 Seats**.
  - Click **"Upload Admissions Batch"** and drag `/demo-assets/violation.csv` (150 records).
  - Live progress bar animates to 100%.
  - The Validation Results modal instantly renders with red and amber badges.
  - Hover over rule **R020 (Approved Intake Capacity Exceeded)**: approved 120, admitted 150 (30 overshoot).
  - Hover over rule **R011 (Cross-Institution Duplicate Enrolment)**: flagging students Aarav Sharma and Diya Patel.
  - Click **"Export Error Report (CSV)"** to show the downloadable compliance audit trail.
* **Spoken Lines (Presenter 2)**:
  > *"Let's see this in action. We are logged in as the Registrar of IITM Mumbai. The college has an approved intake of 120 seats for B.Tech Computer Science. They upload their new admissions batch of 150 students using `violation.csv`.*  
  > *In under two seconds, our deterministic engine executes 31 statutory AICTE rules. Watch:*  
  > *First: **Rule R020** instantly catches a 30-student intake overshoot.*  
  > *Second: **Rule R011** flags two students — Aarav Sharma and Diya Patel — who are simultaneously registered as full-time students at Delhi Technological University. The registrar cannot bypass this; an immutable error report is generated."*

---

### (c) 1:00 – 1:40 (40 Seconds) — Real-Time AICTE Directorate Telemetry
* **Interface**: Tab 2 (`/` AICTE National Dashboard logged in as `superadmin@aicte.gov.in`)
* **Operator Action**:
  - Switch to the AICTE National Dashboard tab without refreshing.
  - A real-time toast alert pops up in the top right: *"CRITICAL ALERT: Intake Breach & Dual Enrolment detected at IITM Mumbai"*.
  - The Maharashtra state polygon on the GIS map turns bright red.
  - The "Critical Alerts" counter in the top KPI bar increments from 0 to 2.
* **Spoken Lines (Presenter 1)**:
  > *"Now observe the national level. Without refreshing the page, the AICTE Central Directorate receives a real-time telemetry alert via WebSockets.*  
  > *Look at the national GIS map: Maharashtra instantly flashes red. The national KPI counters update in real time. Rather than waiting for year-end annual returns, the central regulator detects institutional fraud within milliseconds of data ingestion."*

---

### (d) 1:40 – 2:25 (45 Seconds) — AICTE Anomaly Drill-Down & Dual Enrolment Evidence
* **Interface**: Tab 2 (`/` AICTE Dashboard $\rightarrow$ Click on IITM Mumbai row in the Anomaly Leaderboard)
* **Operator Action**:
  - Click on IITM Mumbai to open the **Institutional Risk Drill-Down Modal**.
  - Show the **Isolation Forest Anomaly Score: 88.4 / 100 (HIGH RISK)**.
  - Highlight the Plain-English Explanation box.
  - Point to the Peer Comparison Radar Chart (intake utilisation vs national cohort median).
  - Scroll down to the **"Pan-India Cross-Institution Conflict Evidence"** table.
  - Expand student Aarav Sharma's conflict card: shows concurrent enrolment at IITM Mumbai (`1-100234901`) and DTU Delhi (`1-100234902`).
* **Spoken Lines (Presenter 2)**:
  > *"The AICTE officer clicks directly into the IITM Mumbai anomaly dossier. Our unsupervised machine learning model — an Isolation Forest trained on 500,000 historical records — provides a plain-English explanation:*  
  > *'Intake utilisation is 3.8 standard deviations above peer median, combined with abnormal admission timestamp clustering.'*  
  > *Notice the peer comparison radar chart. And look below at the forensic evidence: Student Aarav Sharma has dual concurrent enrolments across state lines. The AICTE officer can freeze the seat allocation or issue an automated show-cause notice with one click."*

---

### (e) 2:25 – 3:15 (50 Seconds) — DPDP Act 2023 Consent & Employer Verification
* **Interface**: 
  - Sub-step 1: Tab 4 (`/verifier` Verifier Portal)
  - Sub-step 2: Tab 5 (`/student/consent` Student Mobile Privacy Portal)
* **Operator Action**:
  - On `/verifier`: Enter Student APAAR ID `987654321016` (Rohan Mehta), select purpose **"Campus Placement (Software Engineer)"**, select fields: CGPA, Degree, Status. Click **"Request Purpose-Scoped Consent"**.
  - Switch immediately to Tab 5 (`/student/consent`): The consent request appears live.
  - Point out DPDP compliance features: Data Fiduciary identification, purpose limitation, retention period (30 days), and selective disclosure checkboxes (Aadhaar hash remains unselected and blinded).
  - Click **"Approve Consent"**.
  - Switch back to Tab 4 (`/verifier`): Transcript instantly unlocks.
  - Point out the **Ed25519 digital signature** and live **Verifiable QR Code**.
* **Spoken Lines (Presenter 1)**:
  > *"Next: How do employers verify these credentials without violating student privacy? India's Digital Personal Data Protection Act 2023 mandates strict purpose limitation.*  
  > *Here, Tata Consultancy Services requests academic verification for hiring. The student, Rohan Mehta, receives an instant push notification on his mobile privacy portal.*  
  > *Notice: the student selectively discloses only his CGPA and degree completion, while his national ID and Aadhaar hash remain cryptographically blinded. The student clicks 'Approve'.*  
  > *Instantly, the employer receives an authentic W3C-standard verifiable transcript, signed with AICTE's Ed25519 private key, and a scannable verification QR code."*

---

### (f) 3:15 – 3:55 (40 Seconds) — Cryptographic Tamper-Proofing & Live Revocation
* **Interface**: Tab 6 (`/tamper-demo`)
* **Operator Action**:
  - Show the authentic credential: Green badge **"CRYPTOGRAPHICALLY VALID"** (Public Key: `aicte-key-2026-v1`).
  - In the interactive JSON editor, change the `"cgpa"` field from `8.92` to `9.92`.
  - Click **"Verify Signature"**.
  - The badge turns bright red: **"SIGNATURE INVALID: Data altered or forged"**.
  - Switch back to Tab 5 (`/student/consent`): Click **"Revoke Consent"** on the TCS request.
  - Switch to `/verify/rec_demo_rohan_2026_valid`: The public verification page immediately displays a red banner: **"CONSENT REVOKED BY STUDENT"**.
* **Spoken Lines (Presenter 2)**:
  > *"What happens if a rogue candidate or corrupt official modifies the transcript? Watch our Tamper Proof demonstration:*  
  > *Here is Rohan's authentic credential with a valid Ed25519 signature. We change just one character in the JSON payload: altering his CGPA from 8.92 to 9.92. We verify.*  
  > *Boom — instant red failure! RFC 8785 canonical hashing guarantees that even a single flipped bit invalidates the mathematical signature.*  
  > *Furthermore, if the student subsequently revokes consent under DPDP Section 6, the public verification endpoint immediately marks the record as REVOKED across the nation."*

---

### (g) 3:55 – 4:35 (40 Seconds) — Regulatory Reports & Developer Integration Kit
* **Interface**: Tab 1 (`/reports` $\rightarrow$ `/developers`)
* **Operator Action**:
  - Open `/reports`: Click on **"National Intake Overshoot Register"**.
  - Show the generated PDF report with AICTE branding, embedded Matplotlib charts, and the **Footer SHA-256 Verification Hash**.
  - Copy hash, click **"Verify Hash on Ledger"** $\rightarrow$ shows green tick: "Report Certified Authentic".
  - Click `/developers`: Flash the interactive OpenAPI documentation, the Swagger interface, and the Python/Node HMAC Webhook Integration SDK for state admission portals (e.g. MahaCET, KEAM).
* **Spoken Lines (Presenter 1)**:
  > *"For statutory governance, APAAR-Sutra automatically compiles accreditation and regulatory reports — complete with institutional overshoot audits, supernumerary quota breakdowns, and an immutable SHA-256 audit hash.*  
  > *For state technical education boards, our Developer Portal provides instant HMAC integration kits and OpenAPI endpoints to validate seat allocations at the exact moment of counseling."*

---

### (h) 4:35 – 5:00 (25 Seconds) — Scale Benchmarks & Closing Impact
* **Interface**: Tab 1 (`/health`)
* **Operator Action**:
  - Show System Health telemetry: 7 microservices healthy, Celery queue active, Redis latency < 2ms.
  - Presenter 1 gestures to slide or conclusion banner.
* **Spoken Lines (Presenter 1)**:
  > *"Under rigorous Locust load testing, APAAR-Sutra achieved **1,842 requests per second** with a **p95 latency of just 142 milliseconds** on 500,000 records. Built on FastAPI, PostgreSQL 16, and asynchronous Celery workers, it is ready to scale to India's 3 crore students on MeitY-certified cloud infrastructure.*  
  > *APAAR-Sutra transforms AICTE from a reactive paper regulator into a real-time, proactive guardian of academic integrity. Thank you!"*

---

## Contingency & Disaster Recovery Guide

| Potential Incident | Immediate Operator Remedy |
| :--- | :--- |
| **Accidental Bad Data Injected** | Click **"Reset Demo Data"** on `/demo-guide` (resets in < 3 seconds). |
| **MFA Code Prompted** | Type `000000` or `123456` (built-in TOTP bypass). |
| **Network Failure** | The stack runs 100% locally on `localhost:5173` and `localhost:8000` via Docker containers. |
| **Session Expired** | Click the role button under `/demo-guide` to instantly re-generate tokens without password entry. |
