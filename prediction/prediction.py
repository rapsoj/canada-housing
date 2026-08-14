import pandas as pd
from pathlib import Path


# data_cleaning/prediction -> data_cleaning -> repo src
ROOT = Path(__file__).resolve().parent.parent
PREDICTION_DIR = ROOT / "prediction"
TARGETS = ['total', 'house', 'land']

def load_target_y(split, target):
    """
    Loads y_{split}_full_{target}.csv, which is expected to have columns:
    ['cma_canonical', 'date', target]. This requires the imputation export
    step to have been updated to carry identifiers alongside the target
    values (see prepare_data_for_feature_selection / build_{split}_data).
    """
    path = PREDICTION_DIR / f"y_{split}_full_{target}.csv"
    df = pd.read_csv(path, parse_dates=['date'])
    missing = {'cma_canonical', 'date', target} - set(df.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing columns {missing}. "
            "Make sure the imputation export step saves 'cma_canonical' and "
            "'date' alongside the target values."
        )
    
    return df.sort_values(['cma_canonical', 'date']).reset_index(drop=True)


def calculate_persistence_predictions(df: pd.DataFrame, target: str) -> pd.Series:

    """
    Persistence baseline: prediction for step t, y_hat_t, is the actual value at step t-1,
    within the same group (CMA). The first row of each CMA is always NaN (no prior value to shift).
    """

    df_sorted = df.sort_values(by=['cma_canonical', 'date'])
    predictions = df_sorted.groupby('cma_canonical')[target].shift(1)

    return predictions.reindex(df.index)

def compute_persistence_baseline_for_target(split: str, target: str) -> pd.DataFrame:

    df = load_target_y(split, target)
    out = df[['cma_canonical', 'date', target]].copy()
    out[f'{target}_pred'] = calculate_persistence_predictions(df, target)

    return out.rename(columns={target: f'{target}_true'})

def compute_persistence_baseline(split: str, targets: list) -> pd.DataFrame:

    # Merge on the identifiers rather than
    # assuming identical row order/count across targets.

    merged = None
    for target in targets:
        target_df = compute_persistence_baseline_for_target(split, target)
        merged = target_df if merged is None else merged.merge(
            target_df, on=['cma_canonical', 'date'], how='outer'
        )

    return merged.sort_values(['cma_canonical', 'date']).reset_index(drop=True)

def save_predictions(df, split):
    out_path = PREDICTION_DIR / f"persistence_baseline_predictions_{split}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {split} persistence baseline predictions -> {out_path}")
    

if __name__ == "__main__":
    for split in ('train', 'test'):
        preds = compute_persistence_baseline(split, TARGETS)
        save_predictions(preds, split)