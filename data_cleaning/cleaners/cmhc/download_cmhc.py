#!/usr/bin/env python3
"""
cmhc_downloader.py

Usage:
    python cmhc_downloader.py

Expects:
    config.yaml
"""

import yaml
import argparse
import tempfile
import subprocess
from pathlib import Path

import re
from typing import Dict, List, Tuple, Optional
import pandas as pd

from multiprocessing import Pool, cpu_count
from tqdm import tqdm


# ----------------------------
# Config Loader
# ----------------------------

def load_config(path: Path = Path("config.yaml")) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ----------------------------
# Utilities
# ----------------------------

def ensure_dirs(raw_base: Path, processed_dir: Path):
    raw_base.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)


def parse_uids(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"UID CSV not found: {path}")
    df = pd.read_csv(path, dtype=str)

    candidates = [c for c in df.columns if c.strip().lower() == "cma_uid"]
    if not candidates:
        for c in df.columns:
            if "cma" in c.lower() and "uid" in c.lower():
                candidates = [c]
                break

    if not candidates:
        raise ValueError("Could not find cma_uid column in the UID CSV.")

    uid_col = candidates[0]
    return df[uid_col].dropna().astype(str).str.strip().tolist()


def parse_options_yaml(path: Path) -> Dict[str, Dict[str, List[Optional[str]]]]:
    if not path.exists():
        raise FileNotFoundError(f"options.yaml not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    normalized = {}
    for survey, series_dict in data.items():
        normalized[survey] = {}
        for series, dims in series_dict.items():
            if dims is None:
                normalized[survey][series] = [None]
            else:
                normalized[survey][series] = [
                    None if d is None else d for d in dims
                ]
    return normalized


def download_job(args):
    survey, series, dimension, uid, out_path, r_template = args
    try:
        run_r_and_save(
            survey,
            series,
            dimension,
            uid,
            out_path,
            r_template
        )
        return (survey, series, dimension, out_path)
    except Exception as e:
        print(f"Error: {e}")
        return None


def r_quote(val: Optional[str]) -> str:
    if val is None:
        return "NA"
    s = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def sanitize_filename(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9_\-]+', '_', s).strip('_')


def python_friendly(s: str) -> str:
    s2 = s.strip().lower()
    s2 = re.sub(r'[^0-9a-z]+', '_', s2)
    s2 = re.sub(r'__+', '_', s2).strip('_')
    return s2


def build_r_template(breakdown: str) -> str:
    return f"""
library(cmhc)

vacancy_data <- get_cmhc(
  survey = {{survey}},
  series = {{series}},
  dimension = {{dimension}},
  breakdown = "{breakdown}",
  geo_uid = "{{geo_uid}}"
)

write.csv(vacancy_data, "data.csv", row.names = FALSE)
"""


def run_r_and_save(
    survey: str,
    series: str,
    dimension: Optional[str],
    geo_uid: str,
    out_path: Path,
    r_template: str
) -> None:

    r_code = r_template.format(
        survey=r_quote(survey),
        series=r_quote(series),
        dimension=r_quote(dimension),
        geo_uid=geo_uid
    )

    with tempfile.TemporaryDirectory() as td:
        script_path = Path(td) / "run.R"
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(r_code)

        proc = subprocess.run(
            ["Rscript", str(script_path)],
            cwd=td,
            capture_output=True,
            text=True
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"Rscript failed for {survey} / {series} / {dimension} / {geo_uid}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )

        src = Path(td) / "data.csv"
        if not src.exists():
            raise FileNotFoundError("R run succeeded but data.csv not found")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        src.replace(out_path)


# ----------------------------
# Data Assembly
# ----------------------------

def to_pothole(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'[^0-9a-z]+', '_', s)
    s = re.sub(r'__+', '_', s)
    return s.strip('_')


def collect_and_pivot(
    all_files: List[Tuple[str, str, Optional[str], Path]]
) -> pd.DataFrame:

    long_frames = []

    for survey, series, dimension_name, fpath in all_files:
        try:
            df = pd.read_csv(fpath, dtype=str)
        except Exception:
            continue

        # Identify required columns
        geo_cols = [c for c in df.columns if "geo" in c.lower()]
        date_cols = [c for c in df.columns if "date" in c.lower()]
        value_cols = [c for c in df.columns if c.lower() == "value"]

        if not geo_cols or not date_cols or not value_cols:
            continue

        geo_col = geo_cols[0]
        date_col = date_cols[0]
        value_col = value_cols[0]

        df = df.rename(columns={
            geo_col: "GeoUID",
            date_col: "Date",
            value_col: "Value"
        })

        # Detect actual dimension column if specified
        dim_col = None

        if dimension_name:
            dim_norm = to_pothole(dimension_name)

            for c in df.columns:
                if to_pothole(c) == dim_norm:
                    dim_col = c
                    break

        # Build survey identifier per row
        if dim_col:
            df["_survey_id"] = (
                survey + "_" +
                series + "_" +
                dim_col + "_" +
                df[dim_col].astype(str)
            )
        else:
            df["_survey_id"] = survey + "_" + series

        df["_survey_id"] = df["_survey_id"].apply(to_pothole)

        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

        long_frames.append(
            df[["GeoUID", "Date", "_survey_id", "Value"]]
        )

    if not long_frames:
        return pd.DataFrame(columns=["GeoUID", "Date"])

    long_df = pd.concat(long_frames, ignore_index=True)

    wide_df = (
        long_df
        .pivot_table(
            index=["GeoUID", "Date"],
            columns="_survey_id",
            values="Value",
            aggfunc="first"
        )
        .reset_index()
    )

    wide_df.columns.name = None

    return wide_df


# ----------------------------
# Main
# ----------------------------

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing series folders"
    )
    args = parser.parse_args()

    config = load_config()

    uid_csv = Path(config["paths"]["uid_csv"])
    options_yaml = Path(config["paths"]["options_yaml"])
    raw_base = Path(config["paths"]["raw_base"])
    processed_dir = Path(config["paths"]["processed_dir"])
    breakdown = config["r"]["breakdown"]

    ensure_dirs(raw_base, processed_dir)

    r_template = build_r_template(breakdown)

    uids = parse_uids(uid_csv)
    options = parse_options_yaml(options_yaml)

    all_saved_files = []

    for survey, series_dict in options.items():
        for series, dims in series_dict.items():

            series_folder = raw_base / sanitize_filename(series)

            if series_folder.exists() and not args.overwrite:
                print(f"Skipping existing folder: {series_folder}")
                continue

            series_folder.mkdir(parents=True, exist_ok=True)

            dims_to_iter = dims if dims else [None]

            jobs = []

            for dimension in dims_to_iter:
                for uid in uids:

                    dim_label = "NA" if dimension is None else sanitize_filename(str(dimension))
                    fname = f"{sanitize_filename(series)}__{sanitize_filename(survey)}__{dim_label}__{uid}.csv"
                    out_path = series_folder / fname

                    if out_path.exists() and not args.overwrite:
                        continue

                    jobs.append(
                        (survey, series, dimension, uid, out_path, r_template)
                    )

            if not jobs:
                continue

            # Create ONE pool per series
            with Pool(processes=max(1, cpu_count() - 1)) as pool:
                results = list(tqdm(
                    pool.imap_unordered(download_job, jobs),
                    total=len(jobs),
                    desc=f"{survey} | {series}"
                ))

            for r in results:
                if r:
                    all_saved_files.append(r)

    # Always rebuild file list from disk based on options.yaml
    all_saved_files = []

    for survey, series_dict in options.items():
        for series, dims in series_dict.items():

            series_folder = raw_base / sanitize_filename(series)

            if not series_folder.exists():
                continue

            for f in series_folder.glob("*.csv"):

                # filename format:
                # series__survey__dimension__uid.csv
                parts = f.stem.split("__")

                if len(parts) >= 4:
                    dim_part = parts[2]
                    dimension_name = None if dim_part == "NA" else dim_part
                else:
                    dimension_name = None

                all_saved_files.append((survey, series, dimension_name, f))

    combined = collect_and_pivot(all_saved_files)

    out_file = processed_dir / "cmhc.csv"
    combined.to_csv(out_file, index=False)

    print(f"Combined data written to {out_file}")


if __name__ == "__main__":
    main()