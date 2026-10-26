# ML Intelligence Layer: Institutional Anomaly Benchmark Report

**Dataset**: 60 AICTE-Accredited Institutions (~25,000 Enrolment Population)  
**Evaluation Date**: 2026-10-26 15:43:03 UTC  
**Target Criteria**: Injected suspicious spike institutions (`1-100234907` and `1-100234908`) must rank in the **Top 5** risk list.

---

## 1. Executive Summary

The **APAAR-Sutra Intelligence Layer** was benchmarked on a simulated national institutional cohort to evaluate its capacity to uncover institutional enrollment fraud, ghost student clusters, and robotic bulk upload patterns without manual threshold tuning.

| Metric | Target | Achieved | Status |
| :--- | :---: | :---: | :---: |
| **Spike Inst 1 Rank (`1-100234907`)** | &le; 5 | **#1** | **PASSED** |
| **Spike Inst 2 Rank (`1-100234908`)** | &le; 5 | **#2** | **PASSED** |
| **ROC-AUC (Anomaly Separation)** | &ge; 0.95 | **1.0000** | **PASSED** |
| **Precision@Top5** | 0.40 | **0.40** | **OPTIMAL** |
| **Top Contributing Explainability** | Plain English | **Automated** | **PASSED** |

---

## 2. Top 10 Ranked High-Risk Institutions

| Rank | AICTE ID | Institution Name | Risk Score (0-100) | Severity Level | Top Anomaly Contributing Factor |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **#1** | `1-100234907` | Tiruchirappalli Institute of Technology & Science (WB-07) **[INJECTED SPIKE]** | **100.0** | `CRITICAL` | *Enrolment grew 239.8% YoY vs peer median 0.0%* |
| **#2** | `1-100234908` | Muzaffarpur Institute of Technology & Science (TG-08) **[INJECTED SPIKE]** | **100.0** | `CRITICAL` | *Share of APAAR verification failures is 17.0% vs peer median 0.0%* |
| **#3** | `1-100234920` | Mahbubnagar Institute of Technology & Science (UP-20) | **53.3** | `MEDIUM` | *Admission date clustering is 10.3% vs peer median 7.4% (burst admission anomaly)* |
| **#4** | `1-100234960` | Dehri Institute of Technology & Science (BR-60) | **52.4** | `MEDIUM` | *Admission date clustering is 10.2% vs peer median 7.4% (burst admission anomaly)* |
| **#5** | `1-100234947` | Asansol Institute of Technology & Science (DL-47) | **49.3** | `MEDIUM` | *Enrolment contracted 3.9% YoY vs peer median 0.0%* |
| **#6** | `1-100234929` | Vijayawada Institute of Technology & Science (OD-29) | **49.2** | `MEDIUM` | *Supernumerary and NRI quota share is 18.3% vs peer median 10.8%* |
| **#7** | `1-100234921` | Varanasi Institute of Technology & Science (GJ-21) | **45.0** | `MEDIUM` | *DOB repeat ratio is 25.2% vs peer median 17.4% (synthetic cluster signal)* |
| **#8** | `1-100234928` | Ambattur Institute of Technology & Science (PB-28) | **42.2** | `MEDIUM` | *Admission date clustering is 9.0% vs peer median 7.4% (burst admission anomaly)* |
| **#9** | `1-100234954` | Mysore Institute of Technology & Science (RJ-54) | **41.5** | `MEDIUM` | *Admission date clustering is 9.8% vs peer median 7.0% (burst admission anomaly)* |
| **#10** | `1-100234901` | Nagpur Institute of Technology & Science (MH-01) | **40.5** | `MEDIUM` | *Enrolment contracted 9.2% YoY vs peer median 5.3%* |

---

## 3. Granular Explainability Breakdown for Injected Spike Institutions

### Institution `1-100234907` (Rank #1)
- **Risk Score**: 100.0 / 100 (`CRITICAL`)
- **Contributing Factors**:
  - **yoy_enrolment_growth**: Enrolment grew 239.8% YoY vs peer median 0.0% (Robust Z-Score: `+21.52`, Deviation: `+239820.0%`)
  - **apaar_failure_share**: Share of APAAR verification failures is 17.4% vs peer median 0.0% (Robust Z-Score: `+3.81`, Deviation: `+17450.0%`)
  - **warning_record_share**: Share of records with validation warnings is 14.1% vs peer median 0.0% (Robust Z-Score: `+3.82`, Deviation: `+14060.0%`)

### Institution `1-100234908` (Rank #2)
- **Risk Score**: 100.0 / 100 (`CRITICAL`)
- **Contributing Factors**:
  - **apaar_failure_share**: Share of APAAR verification failures is 17.0% vs peer median 0.0% (Robust Z-Score: `+3.70`, Deviation: `+16970.0%`)
  - **warning_record_share**: Share of records with validation warnings is 13.6% vs peer median 0.0% (Robust Z-Score: `+3.69`, Deviation: `+13570.0%`)
  - **admission_burst_index**: Admission date clustering is 69.0% vs peer median 7.4% (burst admission anomaly) (Robust Z-Score: `+80.30`, Deviation: `+835.0%`)

---

## 4. Methodology & Theoretical Guarantees

1. **Isolation Forest**:
   - Isolates abnormal vectors using multi-dimensional recursive tree partitioning ($100$ estimators).
   - Highly resilient to multi-collinear features (YoY growth + burst clustering).
2. **Robust Z-Score Baseline**:
   - Uses Median and Median Absolute Deviation (MAD):
     $$Z_{\text{robust}} = \frac{x - \text{median}}{1.4826 \cdot \text{MAD}}$$
   - Immunizes the anomaly detector from distortion by heavy outlier tails.
3. **Contextual Peer Benchmarking**:
   - Slices institutions by type (`AUTONOMOUS`, `AFFILIATED`), state, and size tier to prevent penalizing legitimately fast-growing regional programs.
