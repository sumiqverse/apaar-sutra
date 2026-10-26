# APAAR-Sutra: Disaster Recovery & Backup Assets Plan

**Document Purpose**: Guarantees a flawless evaluation under zero-connectivity, projector failure, or hardware contingency conditions during the SIH Grand Finale.

---

## 1. 3-Minute Backup Video Shot List & Narration Script

This script is recorded as an MP4 fallback video (`apaar_sutra_demo_backup_1080p.mp4`) loaded on a local flash drive. If network or live system fails, this video can be presented immediately.

| Shot # | Timecode | Duration | On-Screen Action / Visual Focus | Voiceover Narration Script |
| :---: | :---: | :---: | :--- | :--- |
| **01** | `0:00 - 0:15` | 15s | AICTE National Directorate Dashboard panning across pan-India metrics and GIS map. | *"APAAR-Sutra is AICTE's automated academic registry, eliminating ghost students, dual enrolments, and unapproved seat expansions across 15,000 Indian colleges."* |
| **02** | `0:15 - 0:35` | 20s | Zoom in on IITM Mumbai portal. Registrar uploads `violation.csv` (150 records for 120 sanctioned intake). | *"Here, IITM Mumbai uploads 150 student records against an approved intake of 120. In under two seconds, our deterministic engine executes 31 AICTE compliance rules."* |
| **03** | `0:35 - 0:55` | 20s | Validation Results modal highlights Rule R020 (Intake Exceeded) and Rule R011 (Cross-College Duplicate). | *"Rule R020 blocks the 30-student intake breach. Concurrently, Rule R011 catches two students who are already actively enrolled full-time at Delhi Technological University."* |
| **04** | `0:55 - 1:15` | 20s | Switch to AICTE Directorate Dashboard. Real-time alert toast pops up; Maharashtra polygon turns red. | *"Instantly, without page refresh, the AICTE Central Directorate receives a real-time WebSocket alert. The national map highlights Maharashtra in red as KPI alerts increment."* |
| **05** | `1:15 - 1:35` | 20s | Click into IITM Mumbai anomaly dossier. Display Isolation Forest score (88.4) and peer radar chart. | *"The AICTE officer opens the institution's ML dossier. An Isolation Forest model explains the anomaly: intake utilisation is 3.8 sigma above peer median with dual-enrolment evidence."* |
| **06** | `1:35 - 1:55` | 20s | Verifier Portal (`/verifier`). TCS submits verification query for Student Rohan Mehta. | *"For background checks, TCS requests academic verification under the DPDP Act 2023, specifying employment purpose and requesting only degree status and CGPA."* |
| **07** | `1:55 - 2:15` | 20s | Student Privacy Portal (`/student/consent`). Rohan approves request; shows blinded Aadhaar hash. | *"On his mobile privacy portal, student Rohan Mehta reviews the request, selectively discloses his academic transcript, and approves with cryptographically blinded Aadhaar."* |
| **08** | `2:15 - 2:35` | 20s | Tamper Demo (`/tamper-demo`). Changing CGPA from 8.92 to 9.92 triggers instant red signature failure. | *"In our tamper demo, modifying even a single byte in the digital transcript causes the Ed25519 signature to fail verification immediately. Cryptographic integrity is unforgeable."* |
| **09** | `2:35 - 2:45` | 10s | Student revokes consent; public verification endpoint displays red banner: "CONSENT REVOKED". | *"When the student revokes consent, the public QR verification gateway immediately marks the record as revoked across all national verification points."* |
| **10** | `2:45 - 2:55` | 10s | Statutory Reports (`/reports`). Generate National Overshoot PDF with SHA-256 footer verification seal. | *"AICTE officers generate certified statutory PDF reports with embedded analytics and an immutable SHA-256 audit ledger hash."* |
| **11** | `2:55 - 3:00` | 05s | System Health screen showing Locust load numbers: 1,842 req/s at 142ms p95 latency. | *"Engineered for national scale, APAAR-Sutra delivers 1,842 requests per second. Built for AICTE, ready for India. Thank you."* |

---

## 2. Screenshot Pack Catalogue

A high-resolution screenshot gallery (`/docs/screenshots/`) stored locally in PNG format (1920x1080) for instant slide embedding or offline judge inspection:

1. **`01_aicte_national_telemetry.png`**:
   - *View*: AICTE National Directorate Dashboard (`/`).
   - *Key Elements*: India SVG GIS state heatmap (Maharashtra highlighted in red), real-time KPI tiles (Total Enrolments, Total Intake, Active Breaches: 2, Pan-India Duplicates: 2), and Real-Time Telemetry Event Stream.
2. **`02_institutional_ingestion_violation.png`**:
   - *View*: College Portal (`/institution-dashboard`).
   - *Key Elements*: Batch upload modal with 100% processed status, red callout for Rule R020 (Intake Exceeded: 150/120), amber callout for Rule R011 (Cross-Institution Duplicate: DTU Delhi conflict), and "Export Error Report" button.
3. **`03_anomaly_drilldown_forensics.png`**:
   - *View*: Institution Anomaly Dossier.
   - *Key Elements*: Unsupervised Isolation Forest score (88.4 / 100), plain-English anomaly explanation card, multi-axis peer comparison radar chart, and student-level cross-institution conflict evidence table.
4. **`04_dpdp_student_privacy_consent.png`**:
   - *View*: Student Mobile Consent Portal (`/student/consent`).
   - *Key Elements*: Data Fiduciary identification (Tata Consultancy Services), purpose category (EMPLOYMENT), 30-day retention notice, selective disclosure checkboxes, and "Approve Consent" / "Revoke" controls.
5. **`05_cryptographic_tamper_demo.png`**:
   - *View*: Tamper Proof Testing Interface (`/tamper-demo`).
   - *Key Elements*: Split view comparing authentic Ed25519 canonical JSON with modified payload, glowing red failure badge ("CRYPTOGRAPHIC VERIFICATION FAILED: Signature mismatch"), and active key ID (`aicte-key-2026-v1`).
6. **`06_statutory_reports_ledger_hash.png`**:
   - *View*: Statutory Reports Engine (`/reports`).
   - *Key Elements*: Branded AICTE PDF preview with Matplotlib distribution graphs, row count, generated timestamp, and certified SHA-256 footer verification hash.

---

## 3. 100% Offline Laptop Execution Instructions

To run the entire APAAR-Sutra platform with zero Wi-Fi or mobile data connectivity:

### Step 1: Pre-Bake Docker Container Images (Done Before Travel)
Run the following script to export all images to a portable `.tar` archive:
```bash
# Save all 7 platform images into an offline bundle (approx. 1.8 GB)
docker save -o apaar_sutra_offline_images.tar \
  apaar-sutra-backend:latest \
  apaar-sutra-frontend:latest \
  postgres:16-alpine \
  redis:7-alpine \
  nginx:alpine
```
Copy `apaar_sutra_offline_images.tar` to the evaluation laptop or a USB flash drive.

### Step 2: Load Images on the Evaluation Laptop
```bash
docker load -i apaar_sutra_offline_images.tar
```

### Step 3: Run Completely Offline Stack
In the project directory on the laptop:
```bash
# 1. Start containers using local images (no registry network pull)
docker compose up -d

# 2. Trigger instant local baseline reset (< 3 seconds)
curl -X POST http://localhost:8000/api/v1/demo/reset

# 3. Open local application in Chrome / Firefox
# Web Dashboard:    http://localhost:5173
# Demo Guide:        http://localhost:5173/demo-guide
# API Documentation: http://localhost:8000/docs
```

### Step 4: Verify Offline Mock Integrations
The application automatically runs in standalone offline mode:
- **Mock APAAR Gateway**: `app/integrations/mock_apaar.py` provides simulated responses for upstream Verhoeff APAAR and ABC queries without reaching out to external government networks.
- **Local Keystore**: Ed25519 keypair loaded from local environment variables via `EnvKeyProvider`.
- **Pre-Seeded Data**: Demo assets in `/demo-assets` (`clean.csv`, `violation.csv`, `tamper_sample.json`) are stored on the local disk.
