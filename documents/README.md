# 📁 LunarIce-360 — Documentation Index

> **Project:** LunarIce-360 — BAH 2026 (Bharatiya Antariksh Hackathon)  
> **Problem Statement #8:** Detection & Characterization of Subsurface Ice in Lunar South Polar Regions  
> **Team:** BAHood

---

## 📋 Document Map

| # | Document | Description | Audience |
|:---:|:---|:---|:---|
| 01 | [Hackathon Rules](./01_HACKATHON_RULES.md) | BAH 2026 rules, timeline, evaluation criteria, strategic notes | Team |
| 02 | [Problem Statement](./02_PROBLEM_STATEMENT.md) | Official PS #8 — structured with objectives, workflow, datasets | Team + Judges |
| 03 | [Literature Review](./03_LITERATURE_REVIEW.md) | Survey of prior work, key papers, gaps our pipeline fills | Team + Paper |
| 04 | [Architecture](./04_ARCHITECTURE.md) | System architecture, module breakdown, data flow, constants | Team + Paper |
| 05 | [Novelty Analysis](./05_NOVELTY_ANALYSIS.md) | 6 core novelties, competitive positioning, killer features | Team + Judges |
| 06 | [Approach Flow](./06_APPROACH_FLOW.md) | Step-by-step methodology with mathematical formulations | Team + Paper |
| 07 | [IEEE Paper Strategy](./07_IEEE_PAPER_STRATEGY.md) | Target venues, paper structure, timeline, contribution framing | Team |
| 08 | [Issues & TODO](./08_ISSUES_AND_TODO.md) | Known bugs, inconsistencies, pre-hackathon action items | Team |

---

## 🔑 Quick Reference

### Key Dates
- **Registration Deadline:** July 1, 2026
- **Grand Finale:** August 6–7, 2026 (30 hours)
- **IEEE RadarConf 2027 Submission:** September 30, 2026

### Our 6 Core Novelties
1. Multi-Method Fusion Ice Detection (Threshold + GMM + Isolation Forest + H-Alpha)
2. Dual-Frequency Depth Discrimination (L-band vs S-band penetration)
3. Analytical Vectorized Cloude-Pottier Decomposition
4. NSGA-II Tri-Objective Rover Traverse Optimization
5. Bayesian MCMC Volumetric Ice Inversion
6. End-to-End Integrated Pipeline

### Pipeline Metrics
- **Total Code:** ~6,400 lines of Python
- **Modules:** 14 files
- **Features Extracted:** 17 per pixel
- **Detection Methods:** 4 (fused)
- **NSGA-II Objectives:** 3
- **MCMC Parameters:** 4
- **Auto-generated Figures:** 12
- **Estimated Runtime:** ~4 minutes

---

## 📂 Repository Structure
```
BAHood/
├── documents/              ← 📁 YOU ARE HERE
│   ├── README.md           ← This index
│   ├── 01_HACKATHON_RULES.md
│   ├── 02_PROBLEM_STATEMENT.md
│   ├── 03_LITERATURE_REVIEW.md
│   ├── 04_ARCHITECTURE.md
│   ├── 05_NOVELTY_ANALYSIS.md
│   ├── 06_APPROACH_FLOW.md
│   ├── 07_IEEE_PAPER_STRATEGY.md
│   └── 08_ISSUES_AND_TODO.md
├── main.py                 ← Pipeline orchestrator
├── config.py               ← Configuration & constants
├── preprocessing.py        ← Adaptive Lee filter
├── polarimetry.py          ← 17-feature polarimetric extraction
├── ice_detection.py        ← 4-method fusion detection
├── terrain.py              ← Slope, roughness, illumination
├── landing_site.py         ← Multi-criteria site scoring
├── traverse.py             ← NSGA-II rover path optimization
├── volume_estimation.py    ← Bayesian MCMC ice volume
├── visualization.py        ← 12 publication-quality figures
├── data_loader.py          ← GeoTIFF / PDS data loading
├── demo_synthetic.py       ← Synthetic data generator
├── ui_app.py               ← Interactive browser UI
├── __init__.py             ← Package init
├── tests/                  ← Test suite
├── README.md               ← Project README
└── PROBLEM_STATEMENT.md    ← Original PS file
```
