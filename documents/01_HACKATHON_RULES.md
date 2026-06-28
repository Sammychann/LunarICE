# Bharatiya Antariksh Hackathon (BAH) 2026 — Rules & Guidelines

> **Organized by:** Indian Space Research Organisation (ISRO)  
> **Platform:** Hack2skill  
> **Edition:** 3rd (BAH 2026)  
> **Problem Statement #8:** Detection & Characterization of Subsurface Ice in Lunar South Polar Regions

---

## 📅 Key Dates

| Milestone | Date |
|:---|:---|
| Registration & Idea Submission Opens | June 10, 2026 |
| **Registration Deadline** | **July 1, 2026** |
| Final Shortlist Announcement | July 20, 2026 |
| Induction Session | July 21, 2026 |
| **Grand Finale (30-hour Hackathon)** | **August 6–7, 2026** |

---

## 👥 Eligibility

| Criterion | Details |
|:---|:---|
| Team Size | **3–4 members** |
| Participants | Undergraduate, Graduate, Postgraduate, PhD students / Research scholars |
| Geography | **India only** (enrolled in recognized Indian institutions) |
| Cross-College | Members can be from different colleges/universities |
| Fee | **Free** |
| Working Professionals | ❌ **Not eligible** |

---

## 🏆 Benefits & Rewards

- **Mentorship** from ISRO scientists, PRL researchers, and domain experts
- **Potential internship** opportunity with ISRO
- **National-level recognition** on a prestigious platform
- **Travel reimbursement** for finalists
- **Networking** with innovators, researchers, and industry leaders

---

## 📝 Submission Requirements

### Registration Phase (Before July 1)
- Register online via [hack2skill.com/event/bah2026](https://hack2skill.com/event/bah2026/)
- Submit initial **idea/approach** document describing your methodology

### Grand Finale (August 6–7)
- **30-hour continuous hackathon**
- Build a working solution addressing the problem statement
- Present to ISRO judges and domain experts

---

## 📊 Evaluation Criteria

> [!IMPORTANT]
> These are the criteria by which ISRO judges will evaluate solutions. Our pipeline must excel in each.

| # | Criterion | What Judges Look For |
|:---:|:---|:---|
| 1 | **Scientific Robustness** | Rigorous ice detection methodology grounded in peer-reviewed science |
| 2 | **Accuracy & Clarity** | Precise data analysis, clear interpretation of radar parameters |
| 3 | **Feasibility of Landing Site** | Realistic landing site with safety, illumination, and terrain analysis |
| 4 | **Efficiency & Safety of Rover Traverse** | Optimized path avoiding hazards while maintaining power |
| 5 | **Innovation** | Novel methods, tools, or combinations beyond standard approaches |
| 6 | **Presentation & Documentation** | Clear, professional documentation and visual communication |

---

## 🧭 Strategic Notes for Winning

> [!TIP]
> **Key differentiators** based on the evaluation criteria:

### Scientific Edge
- Our pipeline implements **Sinha et al. (2026) criteria** (CPR > 1, DOP < 0.13) — the very criteria developed by the **PRL scientists who are mentoring this PS**
- We go beyond simple thresholding by adding **Cloude-Pottier H-Alpha decomposition**, **GMM clustering**, and **Isolation Forest** anomaly detection

### Innovation
- **Multi-method fusion** for ice detection (no other team is likely to combine all four methods)
- **NSGA-II multi-objective optimization** for rover traverse (not just A* or Dijkstra)
- **Bayesian MCMC volumetric inversion** — a research-grade approach to ice quantification
- End-to-end pipeline from raw SAR data to mission planning

### Presentation
- Interactive **Streamlit UI** for live demonstration
- Publication-quality visualizations
- Structured documentation ready for IEEE paper submission

---

## 📎 Data Provided by ISRO

- **Chandrayaan-2 DFSAR data** of a target doubly shadowed crater in the lunar south polar region
- Data from ISRO Space Science Data Center (SSDC) / PRADAN portal
- Mentoring by **Physical Research Laboratory (PRL), Ahmedabad** scientists
