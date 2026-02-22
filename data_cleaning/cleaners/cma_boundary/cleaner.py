import os
from pathlib import Path
from typing import Dict, Any, Union, List

import requests
import zipfile

import pandas as pd
from base_cleaner import BaseCleaner

class Cleaner(BaseCleaner):
    """Cleaner for CMA cartographic boundary shapefile (no cleaning required)"""

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source": "Statistics Canada",
            "description": "CMA cartographic boundary shapefile (2021)",
            "update_frequency": "As needed",
            "type": "Spatial / Shapefile"
        }

    def download_data(self, format: str = "dataframe") -> Path:
        """
        Download the shapefile ZIP and extract to data/raw/cma_boundary/.
        Returns the path to the extracted .shp file.
        """
        url = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcma000b21a_e.zip"
        target_dir = Path("data") / "raw" / "cma_boundary"
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_path = target_dir / "lcma000b21a_e.zip"

        # Skip download if already extracted shapefile exists
        shp_candidates = list(target_dir.glob("*.shp"))
        if shp_candidates:
            shp_path = shp_candidates[0]
            self.logger.info(f"Shapefile already present at {shp_path}, skipping download")
            return shp_path

        self.logger.info(f"Downloading CMA boundary ZIP from {url}")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()

        with open(zip_path, "wb") as f:
            f.write(resp.content)

        self.logger.info(f"Download complete — extracting to {target_dir}")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)

        # find a .shp file in the extraction directory
        shp_files = list(target_dir.glob("*.shp"))
        if not shp_files:
            # If none found in root, search recursively
            shp_files = list(target_dir.rglob("*.shp"))

        if not shp_files:
            raise FileNotFoundError(f"No .shp file found in extracted archive at {target_dir}")

        shp_path = shp_files[0]
        self.logger.info(f"Downloaded and extracted shapefile: {shp_path}")

        return shp_path

    def clean_data(self, raw_data: Union[Path, str]) -> List[pd.DataFrame]:
        """
        No cleaning required. Load shapefile as a GeoDataFrame (if geopandas available)
        and return it in a list (pipeline expects a list of DataFrames).
        """
        shp_path = Path(raw_data)

        # Prefer geopandas for shapefiles (GeoDataFrame is a pandas DataFrame subclass).
        try:
            import geopandas as gpd
        except Exception as e:
            self.logger.error(
                "geopandas is required to load shapefiles into a GeoDataFrame. "
                "Install it (e.g. pip install geopandas) or modify the cleaner to handle the file differently."
            )
            raise

        self.logger.info(f"Loading shapefile {shp_path} with geopandas")
        gdf = gpd.read_file(shp_path)

        self.logger.info(f"Loaded GeoDataFrame with {len(gdf)} features")
        return [gdf]

    def validate_output(self, df: pd.DataFrame) -> bool:
        """
        Basic validation: ensure the GeoDataFrame has geometry and is not empty.
        """
        if not super().validate_output(df):
            return False

        # geometry column check for GeoDataFrame; fallback to 'geometry' name
        if "geometry" not in df.columns:
            self.logger.error("Output GeoDataFrame missing 'geometry' column")
            return False

        if len(df) == 0:
            self.logger.error("Output GeoDataFrame is empty")
            return False

        return True