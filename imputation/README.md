# Canadian Housing Policy — Imputation Pipeline

---

## How to Run

**1. Input data** — place cleaned source files in:
```
data_cleaning/data/cleaned/cmhc/cmhc.csv
data_cleaning/data/cleaned/stats_can/cleaned_data.csv
data_cleaning/data/cleaned/cma_boundary/lcma000b21a_e.shp
```

**2. Run imputation pipeline** — cleans, merges and prepares features:
```bash
$ python imputation/data_imputation.py
```
Output: `prediction/X_train_FS.csv` and `prediction/y_train_FS.csv`

**3. Run predictions:**
```bash
$ python prediction/prediction.py
```

---

## Imputation Pipeline Overview

### 1. Load Data and Inspect Structure

Load packages and inspect structure of different data sources: StatsCan, CMHC and spatial data.

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

Group variables into patterns, as data came from various sources (StatsCan, CMHC).

Structure: `GROUP_PATTERNS['Variable_*']` ← `"Variable Group"`

---

### 3. Fill Missing Census Values

Join three different datasets and impute missing values using linear interpolation, per CMA.

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

Structure of interpolation pipeline: functions applied per CMA, iterating through variable groups.

`columns_by_group["Variable Group"]` ← `{'Variable_i'}` for i = 1…n

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
| `dropped_constant_features_{target}.txt` | List of columns dropped for being constant in training: ensures reproducibility and that train/test always share the same columns |

