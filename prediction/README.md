# Canadian Housing Policy — Prediction Pipeline

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

## Prediction Pipeline Overview