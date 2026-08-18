# Canadian Housing Policy — Evaluation Pipeline

---

## How to Run

The [**prediction pipeline**](https://github.com/rapsoj/canada-housing/blob/main/prediction/README.md) produces the following files in `prediction/`:

| File | Content |
|---|---|
| `persistence_baseline_predictions_train.csv` | Persistence baseline predictions (y_t = y_(t-1)) for the training set, all 3 targets |
| `persistence_baseline_predictions_test.csv` | Persistence baseline predictions (y_t = y_(t-1)) for the test set, all 3 targets |

Each file contains the following columns:

| Column | Content |
|---|---|
| `cma_canonical`, `date` | Identifiers |
| `total_true`, `house_true`, `land_true` | Actual values |
| `total_pred`, `house_pred`, `land_pred` | Persistence predictions (previous timestep's actual value, per CMA) |

Note: the first row of each CMA has `NaN` in the `*_pred` columns, since there is no prior value to shift within that split.

-------

**Once the files above are in place, run the evaluation:**

```bash
$ python evaluation/evaluation.py
```
**Output**

| File | Content |
|---|---|
| `evaluation/evals/persistence_baseline_metrics.json` | MDA, NMSE, NRMSE and NMAE for the persistence baseline, per target and split (train/test) |
| `evaluation/evals/plots/{split}_{target}_{cma}.png` | Actual vs. Predicted plots for 5 randomly-selected CMAs, per target and split |

Each row in `persistence_baseline_metrics.json` corresponds to one `(split, target)` pair, with columns:

| Column | Content |
|---|---|
| `split`, `target` | Identifiers (`train`/`test`, `total`/`house`/`land`) |
| `MDA` | Mean Directional Accuracy — share of correctly predicted up/down movements |
| `NMSE`, `NRMSE`, `NMAE` | Mean/root-mean/absolute squared error, normalized by the number of valid observations |