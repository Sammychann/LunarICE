# LunarIce-360 — Approach Flow & Methodology

> Step-by-step methodology from raw data ingestion to final deliverables, with mathematical formulations.

---

## 🌊 Complete Approach Flow

```mermaid
flowchart TB
    subgraph Phase1["Phase 1: Data Ingestion & Preprocessing"]
        A1["Load DFSAR Data<br>(L-band & S-band Stokes: S1, S2, S3, S4)"] --> A2["Load DEM<br>(Digital Elevation Model)"]
        A2 --> A3["Validate Stokes Parameters<br>S1 ≥ 0, S1² ≥ S2²+S3²+S4²"]
        A3 --> A4["Apply Adaptive Lee<br>Speckle Filter"]
    end

    subgraph Phase2["Phase 2: Feature Extraction"]
        A4 --> B1["Compute CPR & DOP<br>per band"]
        A4 --> B2["m-chi Decomposition<br>Pv, Ps, Pd"]
        A4 --> B3["Cloude-Pottier H/A/α<br>Eigendecomposition"]
        A4 --> B4["Dual-Frequency<br>Cross-Features"]
        B1 --> B5["17-Feature Stack<br>(rows × cols × 17)"]
        B2 --> B5
        B3 --> B5
        B4 --> B5
    end

    subgraph Phase3["Phase 3: Ice Detection"]
        B5 --> C1["Threshold<br>CPR>1, DOP<0.13"]
        B5 --> C2["GMM Clustering<br>5 Components"]
        B5 --> C3["Isolation Forest<br>Anomaly Detection"]
        B5 --> C4["H-Alpha Zone<br>Classification"]
        C1 --> C5["Weighted Fusion<br>& Morphological Cleanup"]
        C2 --> C5
        C3 --> C5
        C4 --> C5
        C5 --> C6["Ice Probability Map"]
    end

    subgraph Phase4["Phase 4: Terrain & Safety"]
        A2 --> D1["Compute Slope<br>(Sobel Gradients)"]
        D1 --> D2["Surface Roughness<br>(RMS + Hurst Exponent)"]
        D2 --> D3["Ray-Trace Illumination<br>(216 Sun Positions)"]
        D3 --> D4["Composite Hazard Map"]
    end

    subgraph Phase5["Phase 5: Mission Planning"]
        C6 --> E1["Landing Site Scoring<br>Safety + Illumination +<br>Ice Proximity + Flatness"]
        D4 --> E1
        E1 --> E2["Top-3 Landing Sites"]
        E2 --> F1["NSGA-II Path Planning<br>3 Objectives"]
        D4 --> F1
        F1 --> F2["Pareto-Optimal<br>Traverse Paths"]
        F2 --> F3["Energy Profile<br>Simulation"]
    end

    subgraph Phase6["Phase 6: Volume Estimation"]
        C6 --> G1["Maxwell-Garnett<br>Dielectric Mixing"]
        G1 --> G2["Radar Forward Model<br>Surface + Volume Scattering"]
        G2 --> G3["MCMC Inversion<br>(emcee: 32w × 5000 steps)"]
        G3 --> G4["Ice Volume ± Uncertainty"]
    end

    subgraph Phase7["Phase 7: Output"]
        F2 --> H1["12 Publication Figures"]
        F3 --> H1
        G4 --> H1
        H1 --> H2["Interactive UI"]
    end
```

---

## 📐 Mathematical Formulations

### Phase 1: Preprocessing — Adaptive Lee Filter

$$\hat{I} = \bar{I} + W \cdot (I - \bar{I})$$

Where:
- $W = 1 - \frac{\sigma^2_{\text{noise}}}{\sigma^2_{\text{local}}}$, clipped to $[0, 1]$
- $\sigma^2_{\text{noise}} = \bar{I}^2$ (single-look speckle model)
- $\bar{I}$ = local mean via uniform filter (window size 5×5)

### Phase 2: Polarimetric Features

#### Circular Polarization Ratio (CPR)
$$CPR = \frac{S_1 - S_4}{S_1 + S_4} = \frac{|E_{SC}|^2}{|E_{OC}|^2}$$

Where $S_1$ = total power, $S_4$ = circular polarization difference.
- CPR > 1 → same-sense circular dominates → **volume scattering** (ice signature)

#### Degree of Polarization (DOP)
$$DOP = \frac{\sqrt{S_2^2 + S_3^2 + S_4^2}}{S_1}$$

- DOP < 0.13 → highly depolarized → **random volume scattering** (ice)
- DOP → 1 → fully polarized → surface scattering (rock)

#### m-chi Decomposition (Raney 2012)
$$m = DOP \cdot S_1, \quad \sin(2\chi) = \frac{-S_4}{m \cdot S_1}$$

$$P_v = S_1(1-m), \quad P_s, P_d \text{ conditional on sign of } \chi$$

#### Cloude-Pottier Eigendecomposition (2×2 Analytical)

Coherency matrix from Stokes:
$$J = \begin{pmatrix} (S_1+S_2)/2 & (S_3 - jS_4)/2 \\ (S_3 + jS_4)/2 & (S_1-S_2)/2 \end{pmatrix}$$

Analytical eigenvalues:
$$\lambda_{1,2} = \frac{tr(J) \pm \sqrt{tr(J)^2 - 4\det(J)}}{2}$$

Entropy:
$$H = -\sum_{i=1}^{2} p_i \log_2(p_i), \quad p_i = \frac{\lambda_i}{\lambda_1 + \lambda_2}$$

Anisotropy:
$$A = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2}$$

Alpha (scattering angle):
$$\alpha = \arctan\left(\frac{|v_2|}{|v_1|}\right)$$

### Phase 3: Ice Detection Fusion

$$P_{\text{ice}}(x,y) = w_1 \cdot T(x,y) + w_2 \cdot G(x,y) + w_3 \cdot F(x,y) + w_4 \cdot Z(x,y)$$

Where:
- $T$ = Threshold detection (binary: CPR > 1 ∧ DOP < 0.13)
- $G$ = GMM cluster probability (normalized membership to ice cluster)
- $F$ = Isolation Forest anomaly score (rescaled to [0,1])
- $Z$ = H-Alpha zone indicator (zones 8,9 → ice)
- Weights: $w_1 = 0.20, w_2 = 0.35, w_3 = 0.25, w_4 = 0.20$

Post-processing: **Morphological opening** with 3×3 structuring element to remove isolated pixels.

### Phase 4: Terrain Analysis

#### Slope
$$\text{slope} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$

Gradients computed via **Sobel operator** with $8 \cdot \Delta x$ normalization.

#### RMS Surface Roughness
$$R_{\text{RMS}} = \sqrt{E[z^2] - E[z]^2}$$

Computed over sliding window via `uniform_filter`.

#### Hurst Exponent (Fractal Roughness)
Per 64×64 patch variogram at lags $l = \{1, 2, 4, 8, 16, 32\}$:
$$\gamma(l) = E[(z(x+l) - z(x))^2]$$

Linear regression on $\log(\gamma)$ vs $\log(l)$ gives slope $= 2H$.

#### Ray-Traced Illumination
For each sun position $(\theta_{\text{az}}, \theta_{\text{el}})$:
- Cast rays via array shifting
- Check if terrain blocks line-of-sight
- Average over 36 azimuths × 6 elevations = **216 sun positions**

### Phase 5: Landing Site Selection

$$S_{\text{landing}} = w_s \cdot \text{Safety} + w_i \cdot \text{Illumination} + w_p \cdot \text{Proximity} + w_f \cdot \text{Flatness}$$

Where $(w_s, w_i, w_p, w_f) = (0.30, 0.25, 0.25, 0.20)$

**Proximity score** (Gaussian around ideal distance $d_0 = 3$ km):
$$\text{Proximity}(r) = \exp\left(-\frac{(r - d_0)^2}{2\sigma^2}\right)$$

Hard constraints: slope < 10°, local max slope within 11×11 window < 8°.

### Phase 6: NSGA-II Rover Traverse

**Decision Variables:** $\mathbf{x} = (r_1, c_1, r_2, c_2, \ldots, r_n, c_n)$ — $n$ waypoint positions

**Three Objectives:**
$$\min f_1(\mathbf{x}) = \sum_{\text{segments}} \text{energy\_cost}(s) \cdot \Delta s$$
$$\min f_2(\mathbf{x}) = \sum_{\text{segments}} \text{hazard}(s) \cdot \Delta s$$
$$\min f_3(\mathbf{x}) = \max_{\text{segments}} (1 - \text{illumination}(s)) \cdot \Delta s$$

**Constraint:** $\max(\text{slope along path}) \leq 20°$

**Energy model:**
$$P_{\text{loco}}(s) = P_{\text{base}} \times (1 + \tan(\text{slope}(s)))$$

**NSGA-II Parameters:** 100 population, 50 offspring, 200 generations, SBX crossover (η=15), polynomial mutation (η=20)

### Phase 7: Bayesian MCMC Volume Estimation

**Parameters:** $\boldsymbol{\theta} = (f_{\text{ice}}, r_{\text{cm}}, \rho_{\text{kg/m}^3}, d_{\text{m}})$

**Maxwell-Garnett mixing:**
$$\varepsilon_{\text{eff}} = \varepsilon_h \cdot \frac{\varepsilon_i + 2\varepsilon_h + 2f(\varepsilon_i - \varepsilon_h)}{\varepsilon_i + 2\varepsilon_h - f(\varepsilon_i - \varepsilon_h)}$$

**Surface scattering:**
$$\sigma_{\text{surf}} = |R(\varepsilon_{\text{eff}})|^2 \cdot \cos^2(\theta) \cdot e^{-(ks)^2}$$

**Volume scattering:**
$$\sigma_{\text{vol}} = f_{\text{ice}} \cdot d \cdot \left(\frac{2\pi}{\lambda}\right)^2 \cdot 0.01 \cdot e^{-2\alpha d}$$

**Log-likelihood:**
$$\ln \mathcal{L}(\boldsymbol{\theta}) = -\frac{1}{2}\left[\frac{(\text{CPR}_{\text{pred}} - \text{CPR}_{\text{obs}})^2}{\sigma_{\text{CPR}}^2} + \frac{(\sigma^0_{\text{pred}} - \sigma^0_{\text{obs}})^2}{\sigma_{\sigma^0}^2}\right]$$

**Ice volume per posterior sample:**
$$V_{\text{ice}} = f_{\text{ice}} \times A_{\text{detection}} \times d_{\text{depth}}$$

Final estimate: median ± 16th/84th percentile credible interval.

---

## 🔁 Pipeline Execution Summary

| Phase | Duration (est.) | Output |
|:---|:---|:---|
| 1. Preprocessing | ~2 seconds | Filtered Stokes parameters |
| 2. Feature Extraction | ~5 seconds | 17-feature datacube |
| 3. Ice Detection | ~10 seconds | Ice probability map |
| 4. Terrain Analysis | ~30 seconds | Hazard + illumination maps |
| 5. Landing Site | ~2 seconds | Top-3 ranked sites |
| 6. NSGA-II Traverse | ~60 seconds | Pareto front + paths |
| 7. Volume Estimation | ~120 seconds | Volume ± uncertainty |
| 8. Visualization | ~10 seconds | 12 figures |
| **Total** | **~4 minutes** | **Complete results package** |
