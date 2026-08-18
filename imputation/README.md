# Canadian Housing Policy — Imputation Pipeline

---

## How to Run

**1. Input data** — Cleaned source files are in:
```
data_cleaning/data/cleaned/cmhc/cmhc.csv
data_cleaning/data/cleaned/stats_can/cleaned_data.csv
data_cleaning/data/cleaned/cma_boundary/lcma000b21a_e.shp
```

**2. Run imputation pipeline** — cleans, merges and prepares features:
```bash
$ python imputation/data_imputation.py
```

---

## Imputation Pipeline Overview

### 1. Load Data and Inspect Structure

Load packages and inspect structure of different data sources: 

- StatsCan: with information on target variables, date and CMA identifier;
- CMHC: socioeconomic data, with date and CMA identifier;
- Spatial data.

**Summary — StatsCan data**

| Index | Time range | Interval | Start date |
|---|---|---|---|
| House | 1981–2026 | 1 year | 1/1/year ¹ |
| Land | 1981–2026 | 1 year | 1/1/year |
| Total | 1981–2026 | 1 year | 1/1/year ¹ |

¹ Exception: Halifax, Nova Scotia starts on 1/5/1984.

Out of the 24 CMAs, the following regions have a different starting date:

- **1/1/1995** — Charlottetown, Prince Edward Island
- **1/1/2016** — Guelph ON; Kelowna BC; Oshawa ON; Ottawa-Gatineau (QC part, ON/QC); Sherbrooke QC; Trois-Rivières QC

---

**Summary — CMHC data**

| Variable group | Time range | Interval | Reference date |
|---|---|---|---|
| Census | 2006–2021 | 5 years | 1/7/year |
| Core Housing Need | 2006–2021 | 5 years | 1/7/year |
| Rental Market Survey (RMS) | 1990–2025 ² | 1 year | 1/10/year |
| Starts and Completions Survey (SCSS) | 1990–2026 | 1 month | 1/1–12/year |
| Secondary Rental Market Survey (SRMS) | 2007–2025 | 1 year | 1/7/year |

² Exception: "RMS – Annual Average Rent Percent Change" starts in 1991.

---

### 2. Analyse Date Patterns per CMA

Group CMHC variables into groups, as shown [here](https://github.com/rapsoj/canada-housing/tree/main/data_cleaning/data/cleaned/cmhc), because data comes from various sources.

Example of grouping: `GROUP_PATTERNS["scss_starts_dwelling_type_*"]` ← `"SCSS – Construction Started"` — all variables of the form `"scss_starts_dwelling_type"` are grouped under `"SCSS – Construction Started"`.


**Summary — Missing values on `house`, `land` and `total` targets**

| CMA | Missing period |
|---|---|
| Charlottetown, Prince Edward Island | 1990–1994 |
| Guelph, Ontario | 1990–2016 |
| Halifax, Nova Scotia | 1981–1984 |
| Kelowna, British Columbia | 1990–2016 |
| Oshawa, Ontario | 1990–2016 |
| Ottawa-Gatineau, Quebec part, ON/QC | 1990–2016 |
| Sherbrooke, Quebec | 2006–2016 |
| Trois-Rivières, Quebec | 1990–2016 |

---

### 3. Interpolate Missing CMHC Values

Join StatsCan, CMHC and spatial datasets by CMA identifier and impute missing values using linear interpolation, per CMA. 

**Structure of the interpolation pipeline**: for each CMA, functions iterate through variable groups of `GROUP_PATTERNS` and apply a flat interpolation: the known value is held constant and distributed equally across all periods until the next observation — e.g., monthly for SCSS, yearly for RMS and SRMS, and every 5 years for Census and Core Housing Need.

---

### 4. Split Dataset into Train and Test Sets

80% train / 20% test split.

---

### 5. Data Preparation for Prediction Pipeline

**Output**

For each target in {total, house, land}, in `prediction/`:

| File | Content |
|---|---|
| `X_train_full_{target}.csv` / `y_train_full_{target}.csv` | Full training set, includes `cma_canonical` and `date` alongside the target column, for downstream use |
| `X_train_FS_{target}.csv` / `y_train_FS_{target}.csv` | Training set downsampled to 15%, for Feature Selection (FS) |
| `X_test_full_{target}.csv` / `y_test_full_{target}.csv` | Full test set (no downsampling), includes `cma_canonical` and `date` alongside the target column, for downstream use |
| `dropped_constant_features_{target}.txt` | List of columns dropped for being redundant (only one unique value): ensures reproducibility and that train/test always share the same columns |

