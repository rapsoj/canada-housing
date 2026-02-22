"""
Example data cleaner that works entirely in memory.
Located in: cleaners/example/cleaner.py
To use: python data_cleaning.py --cleaner-name example
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Union

from pathlib import Path
import os
import requests
import zipfile

from base_cleaner import BaseCleaner


class Cleaner(BaseCleaner):
    """Example cleaner that generates and processes synthetic in-memory data"""

    def get_metadata(self) -> Dict[str, Any]:
        """Provide information about this data source"""
        return {
            'source': 'Statistics Canada',
            'description': 'Data related to Canadian housing prices from Statistics Canada',
            'update_frequency': 'Variable',
            'type': 'Survey'
        }

    def download_data(self, format: str = "dataframe"):
        url = "https://www150.statcan.gc.ca/n1/tbl/csv/18100205-eng.zip"
        target_dir = Path("data/raw/stats_can")
        target_dir.mkdir(parents=True, exist_ok=True)

        csv_path = target_dir / "18100205.csv"

        # Skip download if file already exists
        if csv_path.exists():
            self.logger.info(f"File already exists at {csv_path}, skipping download")
            return csv_path

        self.logger.info(f"Downloading from {url}")

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        zip_path = target_dir / "18100205-eng.zip"
        with open(zip_path, "wb") as f:
            f.write(response.content)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)

        self.logger.info(f"Downloaded and extracted to {csv_path}")

        return csv_path


    def clean_data(self, raw_data: Union[pd.DataFrame, np.ndarray]) -> Union[pd.DataFrame, np.ndarray]:
        """Load and clean Statistics Canada housing price data"""

        path = os.path.join(
            "data",
            "raw",
            "stats_can",
            "housing_price",
            "18100205.csv"
        )

        df = pd.read_csv(path, encoding="utf-8-sig")

        # Select required columns
        df = df[[
            "REF_DATE",
            "GEO",
            "New housing price indexes",
            "VALUE",
            "DGUID"
        ]]

        # Pivot wide
        df = df.pivot_table(
            index=["REF_DATE", "GEO", "DGUID"],
            columns="New housing price indexes",
            values="VALUE"
        ).reset_index()

        # Rename index columns
        df = df.rename(columns={
            "REF_DATE": "date",
            "GEO": "geo",
            "DGUID": "dguid",
            "Total (house and land)": "total",
            "House only": "house",
            "Land only": "land"
        })

        # Convert date to datetime
        df["date"] = pd.to_datetime(df["date"], errors="raise")

        # Ensure column order
        df = df[["date", "geo", "dguid", "total", "house", "land"]]

        self.logger.info(f"Cleaned DataFrame with {len(df)} rows")

        return [df]


    def validate_output(self, df: pd.DataFrame) -> bool:
        """Validate cleaned Statistics Canada housing price data"""

        if not super().validate_output(df):
            return False

        expected_columns = ["date", "geo", "dguid", "total", "house", "land"]
        if not all(col in df.columns for col in expected_columns):
            self.logger.error("Missing expected columns")
            return False

        # Ensure date column is datetime convertible
        if pd.to_datetime(df["date"], errors="coerce").isna().any():
            self.logger.error("Invalid values found in date column")
            return False

        # Ensure numeric columns are numeric
        numeric_cols = ["total", "house", "land"]
        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                self.logger.error(f"Column {col} is not numeric")
                return False

        # Basic null check on key columns
        if df[["date", "geo"]].isna().any().any():
            self.logger.error("Null values found in key columns")
            return False

        return True