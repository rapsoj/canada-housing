# Canadian Housing Policy — Prediction Pipeline

---

## How to Run

The [**imputation pipeline**](https://github.com/rapsoj/canada-housing/blob/main/imputation/README.md) produces the following files in `prediction/`, for each target in {total, house, land}:

| File | Content |
|---|---|
| `X_train_full_{target}.csv` / `y_train_full_{target}.csv` | Full training set, includes `cma_canonical` and `date` alongside the target column, for downstream use |
| `X_train_FS_{target}.csv` / `y_train_FS_{target}.csv` | Training set downsampled to 15%, for Feature Selection (FS) |
| `X_test_full_{target}.csv` / `y_test_full_{target}.csv` | Full test set (no downsampling), includes `cma_canonical` and `date` alongside the target column, for downstream use |
| `dropped_constant_features_{target}.txt` | List of columns dropped for being redundant (only one unique value): ensures reproducibility and that train/test always share the same columns |

-----

**Once the files above are in place, run the predictions:**

```bash
$ python prediction/prediction.py
```

**Output** 

| File | Content |
|---|---|
| `persistence_baseline_predictions_train.csv` | Persistence baseline predictions (y_t = y_(t-1)) for the training set, all 3 targets |
| `persistence_baseline_predictions_test.csv` | Persistence baseline predictions (y_t = y_(t-1)) for the test set, all 3 targets |

The files are stored in `prediction/`. Each one contains the following columns:

| Column | Content |
|---|---|
| `cma_canonical`, `date` | Identifiers |
| `total_true`, `house_true`, `land_true` | Actual values |
| `total_pred`, `house_pred`, `land_pred` | Persistence predictions (previous timestep's actual value, per CMA) |


Note: the first row of each CMA has `NaN` in the `*_pred` columns, since there is no prior value to shift within that split.

