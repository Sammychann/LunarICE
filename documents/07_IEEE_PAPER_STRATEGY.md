# IEEE Research Paper Strategy — LunarIce-360

> Strategy document for publishing our hackathon work as a peer-reviewed IEEE conference paper.

---

## 🎯 Target Venues

### Primary Target: IEEE Radar Conference 2027 (RadarConf)
| Detail | Information |
|:---|:---|
| **Location** | **Bangalore, India** 🇮🇳 |
| **Dates** | May 1–6, 2027 |
| **Submission Opens** | July 1, 2026 |
| **Paper Deadline** | **September 30, 2026** |
| **Scope** | Radar phenomenology, SAR, planetary mapping, remote sensing |
| **Why This** | Perfect alignment — SAR + lunar + held in India |

> [!IMPORTANT]
> **Timeline:** Hackathon is August 6–7 → we have ~7 weeks post-hackathon to write and submit the paper. This is tight but feasible if we start drafting now.

### Secondary Target: IEEE InGARSS 2026 (India GRSS Symposium)
| Detail | Information |
|:---|:---|
| **Location** | **Hyderabad, India** 🇮🇳 |
| **Dates** | December 1–4, 2026 |
| **Paper Deadline** | June 30, 2026 (may have late submission window) |
| **Scope** | Planetary and Space Sciences, geoscience, remote sensing |

### Other Venues
| Venue | Deadline | Notes |
|:---|:---|:---|
| **IEEE IGARSS 2027** | ~Jan 2027 | Flagship GRSS conference |
| **LPSC 2027** (USRA) | ~Oct 2026 | Premier planetary science (not IEEE but highly prestigious) |
| **IEEE TGRS** (Journal) | Rolling | Archival journal — higher impact, slower review |

---

## 📄 Proposed Paper Structure

### Title
> **"LunarIce-360: A Multi-Method Fusion Framework for Subsurface Ice Detection, Mission Planning, and Volumetric Estimation Using Chandrayaan-2 DFSAR"**

### Authors
Team members + faculty advisor(s)

---

### Abstract (~200 words)
Detection of subsurface water-ice in the lunar South Polar Region is critical for future In-Situ Resource Utilization (ISRU). We present LunarIce-360, an end-to-end framework that processes Chandrayaan-2 Dual Frequency SAR (DFSAR) data to: (1) detect subsurface ice using a novel multi-method fusion of physics-based thresholding, Gaussian Mixture Model clustering, Isolation Forest anomaly detection, and Cloude-Pottier scattering classification; (2) select safe landing sites via multi-criteria utility scoring; (3) plan optimal rover traverses using NSGA-II tri-objective optimization balancing distance, hazard, and solar illumination; and (4) estimate ice volume through Bayesian MCMC inversion of radar backscatter. Applied to doubly shadowed craters in the Faustini region, our fusion approach achieves [X]% improvement in detection F1-score over single-threshold methods, while the MCMC inversion provides the first uncertainty-quantified volumetric estimates of lunar subsurface ice. The complete pipeline processes raw SAR data to mission-ready outputs in under 5 minutes.

---

### I. Introduction (~1 page)
- Motivation: water-ice for ISRU, sustained lunar presence
- Chandrayaan-2 DFSAR as enabling instrument
- Doubly shadowed craters as targets (Sinha et al. 2026)
- Gap: existing detection is threshold-only, no ML, no volume estimation, no mission planning
- **Contribution statement** (5 numbered points)

### II. Related Work (~1 page)
- CPR/DOP-based ice detection (Spudis 2010, Thomson 2012, Sinha 2026)
- Cloude-Pottier decomposition for lunar SAR
- m-chi decomposition (Raney 2012)
- Rover path planning algorithms
- Dielectric models for lunar regolith

### III. Methodology (~3 pages)
- **III-A: Data & Preprocessing** — DFSAR Stokes parameters, Adaptive Lee filter
- **III-B: Polarimetric Feature Extraction** — 17-feature stack formulation
- **III-C: Multi-Method Ice Detection Fusion** — 4 methods + weighted fusion (CORE CONTRIBUTION)
- **III-D: Landing Site Selection** — Multi-attribute utility function
- **III-E: NSGA-II Rover Traverse** — 3-objective formulation
- **III-F: Bayesian MCMC Volume Inversion** — Forward model + MCMC sampling

### IV. Experimental Setup (~0.5 pages)
- Study area: doubly shadowed crater in Faustini PSR
- DFSAR data specifications (L-band, S-band, resolution)
- Synthetic validation setup
- Computational environment

### V. Results & Discussion (~2 pages)
- **V-A: Ice Detection Results** — probability maps, comparison of individual vs fused methods
- **V-B: Scattering Analysis** — H/Alpha plane, m-chi decomposition maps
- **V-C: Landing Site Analysis** — top-3 sites with scoring breakdown
- **V-D: Rover Traverse** — Pareto front, selected paths, energy profiles
- **V-E: Volume Estimation** — posterior distributions, corner plots, volume CI
- **V-F: Ablation Study** — contribution of each detection method

### VI. Conclusion (~0.5 pages)
- Summary of contributions
- Limitations
- Future work: real DFSAR validation, multi-crater analysis, RL for traverse

### References (~30 references)

---

## 🔑 Key Contributions to Highlight

### Contribution 1 (PRIMARY): Multi-Method Fusion Framework
- **Claim:** First framework to combine physics-based radar thresholds with unsupervised ML for lunar ice detection
- **Evidence:** F1-score improvement over single-threshold baseline
- **Novelty type:** Methodological

### Contribution 2: Bayesian MCMC Volume Inversion
- **Claim:** First uncertainty-quantified volumetric estimate of lunar subsurface ice
- **Evidence:** Posterior distributions, credible intervals, corner plots
- **Novelty type:** Application + Methodological

### Contribution 3: NSGA-II Tri-Objective Traverse
- **Claim:** First multi-objective rover path optimization for ice-access in lunar PSRs
- **Evidence:** Pareto front, energy simulation, comparison with single-objective
- **Novelty type:** Application

### Contribution 4: End-to-End Integration
- **Claim:** First complete pipeline from raw SAR to mission-ready outputs
- **Evidence:** Processing time, output quality, all 5 PS objectives addressed
- **Novelty type:** Systems

### Contribution 5: Dual-Frequency Depth Discrimination
- **Claim:** Novel use of L-band vs S-band penetration depth differences for ice depth classification
- **Evidence:** Depth maps, cross-frequency feature analysis
- **Novelty type:** Analytical

---

## 📊 Required Figures for Paper

| # | Figure | Type | Status |
|:---:|:---|:---|:---:|
| 1 | Pipeline architecture diagram | System overview | 🟢 Ready |
| 2 | Study area / crater location map | Context | 🟡 Needs real data |
| 3 | Ice probability map (fusion vs threshold) | Core result | 🟢 Auto-generated |
| 4 | H/Alpha classification plane | Analysis | 🟢 Auto-generated |
| 5 | Fusion method comparison (bar chart) | Ablation | 🟡 Need to add |
| 6 | Landing site score map | Planning | 🟢 Auto-generated |
| 7 | Pareto front (3D scatter) | Traverse | 🟢 Auto-generated |
| 8 | Rover path on terrain | Planning | 🟢 Auto-generated |
| 9 | MCMC corner plot | Volume | 🟢 Auto-generated |
| 10 | Volume posterior histogram | Volume | 🟢 Auto-generated |

---

## 📝 Writing Timeline

| Milestone | Target Date | Notes |
|:---|:---|:---|
| Draft outline & abstract | July 15, 2026 | Before hackathon |
| Hackathon execution | August 6–7, 2026 | Generate results on real data |
| First draft (full paper) | August 20, 2026 | 2 weeks post-hackathon |
| Internal review | September 1, 2026 | Get faculty/mentor feedback |
| Revisions | September 15, 2026 | Address feedback |
| **Submission** | **September 25, 2026** | 5 days before deadline |

---

## 📚 Alternative Paper Options

If a single comprehensive paper is too large, we can split into **2–3 focused papers:**

### Paper A: Detection Focus
> "Multi-Method Fusion for Subsurface Ice Detection in Lunar Doubly Shadowed Craters Using Chandrayaan-2 DFSAR"
- Contributions 1 + 5
- Target: IEEE RadarConf 2027 or IEEE TGRS

### Paper B: Mission Planning Focus
> "NSGA-II Optimized Rover Traverse Planning for Lunar South Polar Ice Exploration"
- Contribution 3 + landing site selection
- Target: IEEE Aerospace Conference or LPSC 2027

### Paper C: Volume Estimation Focus
> "Bayesian Inversion of Subsurface Ice Volume from Dual-Frequency Polarimetric SAR Backscatter"
- Contribution 2
- Target: IEEE TGRS (journal) or IGARSS 2027

---

## 🎓 IEEE Formatting Notes

- **Conference papers:** 4–6 pages, IEEE two-column format
- **Template:** Use IEEE conference LaTeX/Word template from [IEEE Author Tools](https://www.ieee.org/conferences/publishing/templates.html)
- **Indexing:** All RadarConf papers indexed in IEEE Xplore
- **Copyright:** IEEE copyright form required upon acceptance
- Use `\usepackage{IEEEtran}` for LaTeX
