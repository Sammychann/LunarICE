# Literature Review — Lunar Subsurface Ice Detection & Mission Planning

> This document surveys the state-of-the-art in each domain relevant to our problem statement, identifies gaps in existing work, and positions our approach relative to prior research.

---

## 1. Chandrayaan-2 DFSAR & Subsurface Ice Detection

### 1.1 Foundational Work — Sinha et al. (2026)

**Paper:** *"Subsurface ice in doubly shadowed craters as revealed by Chandrayaan-2 dual frequency synthetic aperture radar"*  
**Authors:** Rishitosh K. Sinha, Rajiv R. Bharti, Kinsuk Acharyya, Sanjay K. Mishra, Neeraj Srivastava, Anil Bhardwaj  
**Journal:** *npj Space Exploration* (Nature Publishing Group), May 2026  
**Affiliation:** Physical Research Laboratory (PRL), Ahmedabad

#### Key Findings
- Analyzed **9 doubly shadowed craters** near the lunar South Pole using Chandrayaan-2 DFSAR
- Established refined radar criteria for ice detection:
  - **CPR > 1.0** (Circular Polarization Ratio — indicates volume scattering dominance)
  - **DOP < 0.13** (Degree of Polarization — indicates depolarized/random scattering)
- Found evidence of subsurface ice in **4 of 9 craters**
- Most compelling: **1.1 km crater within Faustini crater** with **lobate-rim morphology** (impact into ice-rich substrate)
- Temperatures in doubly shadowed craters: ~**25 K** (coldest in the solar system)

#### Methodology
- Used L-band and S-band full-polarimetric data
- Computed Stokes parameters → CPR and DOP
- Compared signatures of doubly shadowed craters with sunlit reference terrain
- Cross-validated with thermal models

#### Limitations
- **Binary classification only** (ice vs. no-ice) — no probabilistic scoring
- No machine learning or unsupervised methods applied
- No volumetric ice estimation attempted
- No mission planning (landing/traverse) component

> [!IMPORTANT]
> The PRL scientists who authored this paper are the **mentors for our problem statement**. Our pipeline builds directly on their detection criteria while extending them significantly.

---

### 1.2 DFSAR Instrument Papers

| Paper | Key Contribution |
|:---|:---|
| *"Chandrayaan-2 DFSAR: Performance Characterization and Initial Results"* (PSJ) | First L-band and S-band fully polarimetric SAR on the Moon; instrument capabilities |
| *"Retrieval of Lunar Surface Dielectric Constant using Chandrayaan-2 Full-Polarimetric SAR Data"* (IEEE TGRS) | Dielectric constant estimation from DFSAR |
| *"Dielectric Constant Estimation of Lunar Surface Using Mini-RF and Chandrayaan-2 SAR Data"* (IEEE TGRS) | Cross-instrument comparison for dielectric retrieval |
| *"Integrated Analysis of Water Ice Detection in Erlanger Crater"* (MDPI) | Multi-dataset ice detection approach |

---

## 2. Radar Polarimetry for Lunar Applications

### 2.1 CPR-Based Detection

- **Circular Polarization Ratio (CPR)** = ratio of same-sense to opposite-sense circular polarization
- CPR > 1 traditionally interpreted as **volume scattering** (ice signature)
- **Problem:** Surface roughness at wavelength scale can also produce CPR > 1 → **ambiguity**
- Solution by Sinha et al.: **Combine CPR > 1 with DOP < 0.13** to disambiguate

### 2.2 Cloude-Pottier H-Alpha Decomposition

- Extracts physical scattering mechanisms from the coherency matrix $[T]$
- **Entropy ($H$):** Randomness of scattering (0 = single mechanism, 1 = fully random)
- **Alpha ($\alpha$):** Dominant scattering type (0° = surface, 45° = volume, 90° = double-bounce)
- **Anisotropy ($A$):** Relative importance of secondary mechanisms
- **H-Alpha plane** divided into **9 classification zones** for unsupervised scattering classification

#### Gap in Literature
- H-Alpha decomposition has been applied to **terrestrial** and **some lunar** SAR data
- **No prior work** systematically combines H-Alpha zone classification with CPR/DOP for ice detection in doubly shadowed craters
- **Our contribution:** First fusion of Sinha et al. criteria with Cloude-Pottier zone classification

---

## 3. Machine Learning for Lunar Ice Detection

### 3.1 Current State
- **Limited application** of ML to lunar ice detection from radar data
- Most work uses simple thresholding on CPR/DOP
- Some terrestrial radar studies use **Random Forests**, **SVM**, and **deep learning** for scattering classification

### 3.2 Our Approach — Novel ML Fusion
| Method | Purpose | Novelty |
|:---|:---|:---|
| **Gaussian Mixture Models (GMM)** | Unsupervised clustering of polarimetric feature space | First application to DFSAR ice detection |
| **Isolation Forest** | Anomaly detection to find ice signatures as deviations from dry regolith | Novel for lunar radar |
| **H-Alpha Zone Classifier** | Physics-based scattering mechanism labeling | Extended from Sinha et al. framework |
| **Weighted Fusion** | Combining all methods with configurable weights | First multi-method fusion framework |

> [!NOTE]
> No existing literature combines physics-based radar criteria with unsupervised ML for lunar subsurface ice detection. This is a key novelty.

---

## 4. Landing Site Selection

### 4.1 Prior Approaches
- **Chandrayaan-3:** Used DEM-based slope and roughness analysis with manual site selection
- **Artemis Program (NASA):** Multi-criteria decision analysis with GIS overlay
- **JAXA SLIM:** Precision landing with terrain-relative navigation

### 4.2 Standard Criteria
- Slope ≤ 7°–12° (mission dependent)
- Surface roughness within acceptable limits
- Boulder density below threshold
- Adequate solar illumination for power
- Proximity to scientifically interesting targets

### 4.3 Our Approach
- **Multi-Attribute Utility Function** combining:
  - Slope safety score
  - Surface roughness score
  - Illumination fraction
  - **Proximity to ice-bearing regions** (novel weighting)
- Automated site ranking with configurable weights

---

## 5. Rover Traverse Path Planning

### 5.1 Traditional Approaches
| Method | Limitation |
|:---|:---|
| **A\* / Dijkstra** | Single-objective only; cannot balance competing goals |
| **RRT / PRM** | Probabilistic; poor for constrained environments |
| **Potential Fields** | Local minima problem; no global optimality |

### 5.2 Multi-Objective Approaches
- **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) — gold standard for multi-objective optimization
- Produces **Pareto-optimal front** of trade-off solutions
- Applied to Mars rover planning (NASA JPL), but **limited application to lunar south pole**

### 5.3 Our Innovation
- **Three simultaneous objectives:**
  1. Minimize path length
  2. Minimize slope & hazard exposure
  3. Maximize solar illumination coverage
- Physical constraints: rover speed, power generation, communication limits
- **First NSGA-II application** to ice-access traverse planning in lunar PSRs

---

## 6. Volumetric Ice Estimation

### 6.1 Current Methods
- **Simple empirical models:** Linear relationship between CPR and ice fraction
- **Forward radar models:** IEM (Integral Equation Model) for surface backscatter
- **Dielectric mixing models:** Maxwell Garnett or Bruggeman for ice/regolith mixtures

### 6.2 Our Approach — Bayesian MCMC Inversion
- **Novel for lunar ice estimation**
- Uses Markov Chain Monte Carlo sampling to invert physical parameters from SAR backscatter
- Estimates: ice fraction, layer thickness, density, surface roughness
- Produces **posterior probability distributions** with confidence intervals
- **Corner plots** showing parameter correlations

> [!IMPORTANT]
> No existing lunar ice study uses Bayesian MCMC for volumetric inversion. This represents a publication-worthy methodological contribution.

---

## 7. Summary of Gaps Our Pipeline Fills

| Domain | Existing State-of-Art | Our Contribution |
|:---|:---|:---|
| **Ice Detection** | Binary CPR/DOP thresholding | Multi-method fusion (threshold + H-Alpha + GMM + Isolation Forest) |
| **Scattering Analysis** | CPR and DOP only | Full Cloude-Pottier eigenvalue decomposition (H, A, α) |
| **ML for Ice** | Not applied to DFSAR | GMM clustering + Isolation Forest anomaly detection |
| **Landing Site** | Manual GIS overlay | Automated multi-attribute scoring with ice proximity |
| **Rover Traverse** | Single-objective or manual | NSGA-II tri-objective optimization |
| **Volume Estimation** | Simple empirical models | Bayesian MCMC physical inversion with uncertainty |
| **End-to-End Pipeline** | Separate disconnected tools | Fully integrated Python pipeline with interactive UI |

---

## 8. Key References

1. Sinha, R.K. et al. (2026). "Subsurface ice in doubly shadowed craters as revealed by Chandrayaan-2 DFSAR." *npj Space Exploration*.
2. Cloude, S.R. & Pottier, E. (1997). "An Entropy Based Classification Scheme for Land Applications of Polarimetric SAR." *IEEE TGRS*.
3. Deb, K. et al. (2002). "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II." *IEEE Trans. Evolutionary Computation*.
4. Foreman-Mackey, D. et al. (2013). "emcee: The MCMC Hammer." *PASP*.
5. Spudis, P.D. et al. (2010). "Initial results for the north pole of the Moon from Mini-SAR." *GRL*.
6. Thomson, B.J. et al. (2012). "An upper limit for ice in Shackleton crater." *GRL*.
7. Patterson, G.W. et al. (2017). "Bistatic radar observations of the Moon using Mini-RF." *Icarus*.
8. Li, S. et al. (2018). "Direct evidence of surface exposed water ice in the lunar polar regions." *PNAS*.
