import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error

# evaluation -> repo src
ROOT = Path(__file__).resolve().parent.parent
PREDICTION_DIR = ROOT / "prediction"
EVALS_DIR = ROOT / "evaluation" / "evals"
PLOTS_DIR = EVALS_DIR / "plots"
METRICS_DIR = EVALS_DIR / "metrics"

TARGETS = ['total', 'house', 'land']
SPLITS = ['train', 'test']
N_RANDOM_CMAS = 2
RANDOM_SEED = 42


def load_predictions(split: str) -> pd.DataFrame:

    """
    Loads persistence_baseline_predictions_{split}.csv, expected to contain
    columns: cma_canonical, date, {target}_true, {target}_pred for each target.
    """

    path = PREDICTION_DIR / f"persistence_baseline_predictions_{split}.csv"
    df = pd.read_csv(path, parse_dates=['date'])
    return df.sort_values(['cma_canonical', 'date']).reset_index(drop=True)


def mean_directional_accuracy_grouped(df: pd.DataFrame, true_col: str, pred_col: str,
                                       group_col: str = 'cma_canonical') -> float:

    """
    Same idea as a plain diff()-based MDA, but computed within each group
    (CMA) separately before aggregating, so the diff at the boundary between
    two different CMAs is never compared.
    """

    def per_group_directions(g):
        true_dir = np.sign(g[true_col].diff())
        pred_dir = np.sign(g[pred_col].diff())
        return pd.DataFrame({'true_dir': true_dir, 'pred_dir': pred_dir})

    directions = df.groupby(group_col, group_keys=False).apply(per_group_directions).dropna()

    if directions.empty:
        return np.nan
    correct = (directions['true_dir'] == directions['pred_dir']).sum()
    return correct / len(directions)


def calculate_all_metrics(df: pd.DataFrame, target: str, group_col: str = 'cma_canonical') -> dict:

    """
    Computes MDA, NMSE, NRMSE, NMAE for a given target, over all rows in df
    where both the true and predicted values are available.
    """

    true_col, pred_col = f'{target}_true', f'{target}_pred'

    valid_mask = df[true_col].notna() & df[pred_col].notna()
    df_valid = df.loc[valid_mask]
    actuals_aligned = df_valid[true_col]
    predictions_aligned = df_valid[pred_col]

    if len(actuals_aligned) == 0:
        return {'MDA': np.nan, 'NMSE': np.nan, 'NRMSE': np.nan, 'NMAE': np.nan}

    mse = mean_squared_error(actuals_aligned, predictions_aligned)
    mae = mean_absolute_error(actuals_aligned, predictions_aligned)
    mda = mean_directional_accuracy_grouped(df_valid, true_col, pred_col, group_col)

    # Normalization by number of observations, matching the original approach
    data_range = len(actuals_aligned)

    nmse, nrmse, nmae = np.nan, np.nan, np.nan
    if data_range > 0:
        nmse = mse / (data_range ** 2)
        nrmse = np.sqrt(mse) / data_range
        nmae = mae / data_range

    return {'MDA': mda, 'NMSE': nmse, 'NRMSE': nrmse, 'NMAE': nmae}


def print_metrics(metrics: dict, split: str, target: str):
    label = f"Persistence Model ({split.capitalize()}, target={target})"
    print(f"{label} - NMSE: {metrics['NMSE']:.4f}")
    print(f"{label} - NRMSE: {metrics['NRMSE']:.4f}")
    print(f"{label} - NMAE: {metrics['NMAE']:.4f}")
    print(f"{label} - MDA: {metrics['MDA']:.2f}")


def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))


def plot_random_cmas(df: pd.DataFrame, target: str, split: str,
                      n: int = N_RANDOM_CMAS, seed: int = RANDOM_SEED,
                      save_dir: Path = PLOTS_DIR):

    """
    Saves one Actual vs Predicted plot per randomly-chosen CMA, using the
    predictions already present in df (no recomputation of the baseline).
    """

    true_col, pred_col = f'{target}_true', f'{target}_pred'

    unique_cmas = df['cma_canonical'].unique().tolist()
    random.seed(seed)
    random_cmas = random.sample(unique_cmas, min(n, len(unique_cmas)))

    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Persistence Model ({split.capitalize()}, target={target}): "
          f"Actual vs Predicted for {len(random_cmas)} random CMAs ---")

    for cma in random_cmas:
        cma_data = df[df['cma_canonical'] == cma].sort_values('date')
        cma_comparison_df = cma_data[['date', true_col, pred_col]].dropna()

        if cma_comparison_df.empty:
            print(f"  Skipping {cma}: no overlapping actual/predicted values.")
            continue

        plt.figure(figsize=(12, 6))
        plt.plot(cma_comparison_df['date'], cma_comparison_df[true_col],
                  label='Actual', marker='o', linestyle='-')
        plt.plot(cma_comparison_df['date'], cma_comparison_df[pred_col],
                  label='Persistence Prediction', marker='x', linestyle='--')
        plt.title(f'Persistence Model ({split.capitalize()}): Actual vs. Predicted '
                  f'for {cma} — {target}')
        plt.xlabel('Date')
        plt.ylabel(f'{target} value')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        out_path = save_dir / f"{split}_{target}_{sanitize_filename(cma)}.png"
        plt.savefig(out_path)
        plt.close()
        print(f"  Saved plot for {cma} -> {out_path}")


if __name__ == "__main__":
    
    # Nested dict: {split: {target: {metric_name: value}}}
    all_metrics = {}

    for split in SPLITS:
        df = load_predictions(split)
        all_metrics[split] = {}

        for target in TARGETS:
            metrics = calculate_all_metrics(df, target)
            print_metrics(metrics, split, target)
            # Cast numpy floats to native Python floats so json.dump can serialize them
            all_metrics[split][target] = {k: float(v) for k, v in metrics.items()}

            plot_random_cmas(df, target, split)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = METRICS_DIR / "persistence_baseline_metrics.json"
    with open(summary_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\nSaved metrics summary -> {summary_path}")