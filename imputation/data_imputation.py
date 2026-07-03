import pandas as pd
import geopandas as gpd
import os
import numpy as np
import re
import random
import matplotlib.pyplot as plt


from pathlib import Path
from scipy.interpolate import UnivariateSpline
from sklearn.model_selection import train_test_split

#### LOAD DATA AND INSPECT STRUCTURE ######

# data_cleaning/imputation -> data_cleaning -> repo src
ROOT = Path(__file__).resolve().parent.parent

cmhc_df = pd.read_csv(ROOT / "data_cleaning/data/cleaned/cmhc/cmhc.csv")
stats_can_df = pd.read_csv(ROOT / "data_cleaning/data/cleaned/stats_can/cleaned_data.csv")
shapes_df = gpd.read_file(ROOT / "data_cleaning/data/cleaned/cma_boundary/lcma000b21a_e.shp")

datasets = {
    "CMHC": cmhc_df,
    "StatsCan": stats_can_df,
    "Shapes": shapes_df
}

for name, d in datasets.items():
    rows, cols = d.shape

    print(f"--- {name} ---")
    print(f"Size: {d.size} | Rows: {rows} | Cols: {cols}")
    print(d.iloc[0])
    print("\n")

#Certify Date is in datetime
cmhc_df['Date'] = pd.to_datetime(cmhc_df['Date'], errors='coerce')
stats_can_df['date'] = pd.to_datetime(stats_can_df['date'], errors='coerce')

#CMA of interest
CMA_LIST = [
    "Edmonton, Alberta", "Greater Sudbury, Ontario", "Halifax, Nova Scotia",
    "Hamilton, Ontario", "Kitchener-Cambridge-Waterloo, Ontario", "London, Ontario",
    "Montréal, Quebec", "Ottawa-Gatineau, Ontario part, Ontario/Quebec", "Québec, Quebec",
    "Regina, Saskatchewan", "Saskatoon, Saskatchewan", "St. Catharines-Niagara, Ontario",
    "St. John's, Newfoundland and Labrador", "Vancouver, British Columbia",
    "Victoria, British Columbia", "Windsor, Ontario", "Winnipeg, Manitoba",
    "Charlottetown, Prince Edward Island", "Guelph, Ontario", "Kelowna, British Columbia",
    "Oshawa, Ontario", "Ottawa-Gatineau, Quebec part, Ontario/Quebec", "Sherbrooke, Quebec",
    "Trois-Rivières, Quebec"
]

#Filter StatsCan to only have CMA of interest
stats_can_df = stats_can_df[stats_can_df['geo'].isin(CMA_LIST)]


#### ANALYSE DATE PATTERNS PER CMA ######

# Group variables in patterns, as data came from various sources: StatsCan, CMHC. Structure: GROUP_PATTERNS['Variable_*'] <- "Variable Group"

GROUP_PATTERNS = {
    # ---------------------------------------------------------
    # SCSS — Starts and Completions Survey
    # ---------------------------------------------------------
    # Construction Activity
    "scss_starts_dwelling_type_": "SCSS – Construction Started",
    "scss_completions_dwelling_type_": "SCSS – Construction Ended",
    "scss_under_construction_dwelling_type_": "SCSS – Under Construction ",
    "scss_length_of_construction_dwelling_type_": "SCSS – Construction Length",

    # Market Absorption
    "scss_absorbed_units_dwelling_type_": "SCSS – Market Absorption",
    "scss_share_absorbed_at_completion_dwelling_type_": "SCSS – Market Absorption Share",
    "scss_unabsorbed_inventory_dwelling_type_": "SCSS – Market Unabsorption",

    # ---------------------------------------------------------
    # RMS — Rental Market Survey
    # ---------------------------------------------------------
    # Vacancy & Availability
    "rms_vacancy_rate_bedroom_type_": "RMS – Vacancy Rate",
    "rms_availability_rate_bedroom_type_": "RMS – Availability Rate",

    # Rent Levels
    "rms_average_rent_bedroom_type_": "RMS – Average Rent",
    "rms_median_rent_bedroom_type_": "RMS – Median Rent",
    "rms_average_rent_change_bedroom_type_": "RMS – Annual Average Rent Percent Change",

    # Supply
    "rms_rental_universe_bedroom_type_": "RMS – Supply of Rental Units",
    "rms_summary_statistics": "RMS – Aggregate Indicator",

    # ---------------------------------------------------------
    # SRMS — Secondary Rental Market Survey
    # ---------------------------------------------------------
    # Condo Universe
    "srms_condo_universe_structure_size_": "SRMS – Total Condo Universe",
    "srms_rental_condo_universe_structure_size_": "SRMS – Condo for Rent Universe",
    "srms_percentage_condo_used_as_rental_structure_size_": "SRMS – Share of Condo for Rent",
    "srms_condo_vacancy_rate_structure_size_": "SRMS – Condo Vacancy Rate",

    # Condo Rents
    "srms_condo_average_rent_bedroom_type_": "SRMS – Condo Average Rent",

    # Other Secondary Rentals
    "srms_other_seconary_rental_universe_dwelling_type_": "SRMS – Other Secondary Rentals",

    # ---------------------------------------------------------
    # Census — Income
    # ---------------------------------------------------------
    "census_income_average_and_median_average_household_income_before_taxes": "Census – Average Household Income Before Taxes",
    "census_income_average_and_median_average_household_income_after_taxes": "Census – Average Household Income After Taxes",
    "census_income_average_and_median_median_household_income_before_taxes": "Census – Median Household Income Before Taxes",
    "census_income_average_and_median_median_household_income_after_taxes": "Census – Median Household Income After Taxes",

    # ---------------------------------------------------------
    # Census — Dwelling Value
    # ---------------------------------------------------------
    "census_dwelling_value_average_": "Census – Average Dwelling Value",
    "census_dwelling_value_median_": "Census – Median Dwelling Value",

    # ---------------------------------------------------------
    # Census — Age of Population
    # ---------------------------------------------------------
    "census_all_households_age_of_population_": "Census – Age of Population",
    "census_65_and_over_age_of_population_": "Census – Age of Population (65+)",

    # ---------------------------------------------------------
    # Census — Age of Primary Household Maintainer
    # ---------------------------------------------------------
    "census_all_households_age_of_primary_household_maintainer_": "Census – Age of Maintainer",
    "census_65_and_over_age_of_primary_household_maintainer_": "Census – Age of Maintainer (65+)",

    # ---------------------------------------------------------
    # Census — Mobility
    # ---------------------------------------------------------
    "census_mobility_1_of_all_households_age_of_primary_household_maintainer_": "Census – Mobility Status 1 Year Prior to Census",
    "census_mobility_5_of_all_households_age_of_primary_household_maintainer_": "Census – Mobility Status 5 Years Prior to Census",
    "census_mobility_1_of_65_and_over_age_of_primary_household_maintainer_": "Census – Mobility Status 1 Year Prior to Census (65+)",
    "census_mobility_5_of_65_and_over_age_of_primary_household_maintainer_": "Census – Mobility Status 5 Years Prior to Census (65+)",

    # ---------------------------------------------------------
    # Core Housing Need — CMHC
    # ---------------------------------------------------------
    # Counts
    "core_housing_need_housing_standards_households_in_core_housing_need_": "Core Housing In Need – Counts",
    "core_housing_need_housing_standards_households_tested_for_core_housing_need_": "Core Housing Tested for Need – Counts",

    # Percentages
    "core_housing_need_housing_standards_of_households_in_core_housing_need_": "Core Housing in Need – Percentages",

}


def get_group_for_column(col):

    # Check for exact matches first for the newly requested feature groups
   
    if col in ["total_lag_1"]:
        return "Lagged target"

    for pattern, group in GROUP_PATTERNS.items():
        if col.startswith(pattern):
            return group
    return "UNMATCHED"


### FILL MISSING CENSUS VALUES ###

def clean_geo_name(name) -> str:
    name = str(name).lower().strip()

    # Normalize hyphens early for consistent checks
    name = re.sub(r'\s*-\s*', '-', name)

    # Special handling for Ottawa-Gatineau to preserve distinction
    if 'ottawa-gatineau' in name:
        # Prioritize checking for Quebec part
        if 'quebec part' in name or 'partie du quebec' in name:
            return 'ottawa-gatineau-quebec'
        elif 'ontario part' in name or 'ontario/quebec' in name:
            return 'ottawa-gatineau-ontario'

    # Remove text inside parentheses (e.g., "(Ontario part / partie de l'Ontario)")
    name = re.sub(r'\([^)]*\)', '', name).strip()

    # Handle common alternative names or parts separated by '/'
    if '/' in name:
        name = name.split('/')[0].strip()

    # Split by comma and take the first part (removes ", Ontario", ", Quebec", etc.)
    name = name.split(',')[0].strip()

    # Remove dots (e.g., "st.")
    name = name.replace('.', '')

    # Replace multiple spaces with a single space
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

#Create a function to map a CMA name to its canonical name (if it exists)
def get_canonical_cma_name(name, cleaned_map) -> str:
    cleaned_name = clean_geo_name(name)
    return cleaned_map.get(cleaned_name, None)

# 1. Create a dictionary of cleaned canonical names from CMA_LIST
# This will be our set of reference names
cleaned_cma_map = {
    clean_geo_name(cma): cma for cma in CMA_LIST
}

# 2. Apply the mapping to shapes_df['CMANAME']
shapes_df['CMANAME_canonical'] = shapes_df['CMANAME'].apply(lambda x: get_canonical_cma_name(x, cleaned_cma_map))

# 3. Apply the mapping to stats_can_df['geo']
stats_can_df['geo_canonical'] = stats_can_df['geo'].apply(lambda x: get_canonical_cma_name(x, cleaned_cma_map))


### Join the three different datasets in one by using common CMAPUID and GeoUID

#1. Type alignment for the first join
shapes_df['cmapuid_int'] = shapes_df['CMAPUID'].astype(int)

#2. Save relevant Spatial Metadata info in a dictionary

RELEVANT_SHAPE_INFO = {}
for index, row in shapes_df.iterrows():
    cma_name = row['CMANAME_canonical']
    if pd.notna(cma_name):
        RELEVANT_SHAPE_INFO[cma_name] = [row['LANDAREA'], row['geometry']]

#3. First Join: Merging CMHC with Spatial Metadata (Shapes)

chmc_stats_shapes_df = pd.merge(
    cmhc_df,
    shapes_df[['cmapuid_int', 'CMANAME_canonical']],
    left_on='GeoUID',
    right_on='cmapuid_int',
    how='left'
)

#Filter for relevant CMA
chmc_stats_shapes_df = chmc_stats_shapes_df[chmc_stats_shapes_df['CMANAME_canonical'].isin(CMA_LIST)]

#4. Second join: Merging CMHC + Spatial Metadata with unique StatsCan values

#Fix name to fit column title: lower with optional dash
chmc_stats_shapes_df = chmc_stats_shapes_df.rename(columns={'CMANAME_canonical': 'cma_canonical'})


# Extract unique statistical values to avoid row duplication, just to make sure
stats_values_unique = stats_can_df[['geo', 'date', 'total', 'house', 'land']].drop_duplicates(['geo', 'date']) #dguid_numeric could be used, optionally


chmc_stats_shapes_df = pd.merge(
    chmc_stats_shapes_df,
    stats_values_unique,
    left_on=['cma_canonical', 'Date'],
    right_on=['geo', 'date'],
    how= "outer"
)

# Fill missing 'cma_canonical' values using 'geo' from stats_can_df if available
chmc_stats_shapes_df['cma_canonical'] = chmc_stats_shapes_df.apply(
    lambda row: get_canonical_cma_name(row['geo'], cleaned_cma_map)
    if pd.isna(row['cma_canonical']) else row['cma_canonical'],
    axis=1
)

# Create a mapping from canonical CMA name to cmapuid_int from the shapes_df
cma_canonical_to_cmapuid_map = shapes_df.dropna(subset=['CMANAME_canonical']).set_index('CMANAME_canonical')['cmapuid_int'].to_dict()

# Fill missing 'cmapuid_int' values using the 'cma_canonical' column
chmc_stats_shapes_df['cmapuid_int'] = chmc_stats_shapes_df.apply(
    lambda row:
        cma_canonical_to_cmapuid_map.get(row['cma_canonical']) if pd.isna(row['cmapuid_int']) else row['cmapuid_int'],
    axis=1
)

#Fill missing dates using CMHC date (has more data) on Stats Canada date
chmc_stats_shapes_df['date'] = chmc_stats_shapes_df['date'].fillna(chmc_stats_shapes_df['Date'])

#Drop columns Date and geo, due to redundacy
chmc_stats_shapes_df = chmc_stats_shapes_df.drop(columns=['Date', 'geo'], errors='ignore')


### SPLIT DATASET INTO TRAIN AND TEST SETS

def split_logic(group) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_idx = int(len(group) * 0.8)
    return group.iloc[:split_idx], group.iloc[split_idx:]

# Apply the split logic per CMA

temp_df = chmc_stats_shapes_df.sort_values(by=['cma_canonical', 'date']).copy()
train_list = []
test_list = []

for _, group in temp_df.groupby('cma_canonical', sort=False):
    train_part, test_part = split_logic(group)
    train_list.append(train_part)
    test_list.append(test_part)

# Concatenate back into the final split dataframes
x_train = pd.concat(train_list)
x_test = pd.concat(test_list)

# Clean up memory
del temp_df

### GET GROUP'S COLUMNS TO ITERATE THROUGH DIFFERENT GROUPS. Structure: columns_by_group["Variable Group"]<- {'Variable_i'}i=1:n, n being "Variable Group" size.

columns_by_group = {}

for col in cmhc_df.columns:
    group = get_group_for_column(col)
    if group != "UNMATCHED":
        if group not in columns_by_group:
            columns_by_group[group] = []
        columns_by_group[group].append(col)

#Previously seen that these columns are fully composed of NA, i.e. 100% missing values, for most CMAs, so not informative for upstream work.

groups_to_exclude = [
    "SRMS – Condo Average Rent",
    "SRMS – Condo for Rent Universe",
    "SRMS – Share of Condo for Rent",
    "SRMS – Other Secondary Rentals",
    "SRMS – Condo Vacancy Rate"
]

columns_to_drop = []
for group, cols in columns_by_group.items():
    if group in groups_to_exclude:
        columns_to_drop.extend(cols)

# Ensure only columns present in the DataFrame are dropped
columns_to_drop_train = [col for col in columns_to_drop if col in x_train.columns]
columns_to_drop_test = [col for col in columns_to_drop if col in x_test.columns]

x_train = x_train.drop(columns=columns_to_drop_train, errors='ignore')
x_test = x_test.drop(columns=columns_to_drop_test, errors='ignore')

### INTERPOLATION METHODS PER CMA

def linear_impute(df, cols, distribute=False) -> pd.DataFrame:

    """
    Imputation for Census variables (2006–2021, 5-year intervals), Core Housing Needs (2006-2021, 5 year intervals) originally. Can be extended to other variables.

    - Performs linear interpolation at the annual level.
    - Extends the timeline backwards to 1990.
    - Expands each annual value to all timestamps within that year.
    - distribute=False -> constant value within each year.
    - distribute=True -> smooth distribution within each year.
    """

    df = df.copy()
    df["year"] = df["date"].dt.year

    # Dynamically determine the full_years range based on the DataFrame's date column
    min_year = df['date'].dt.year.min() if not df['date'].empty else 1990 # Fallback to 1990 if no dates
    max_year = df['date'].dt.year.max() if not df['date'].empty else 2021 # Fallback to 2022 if no dates
    full_years = np.arange(min_year, max_year + 1)

    for col in cols:

        def transform(x):
            # Aggregate observed values at the yearly level
            yearly = x.groupby(df.loc[x.index, "year"]).mean()

            # Ensure full coverage from the dynamic full_years range
            yearly = yearly.reindex(full_years)

            # Linear interpolation across years
            yearly_imputed = yearly.interpolate(method="linear", limit_direction="both")

            out = pd.Series(index=x.index) #out = x.copy()

            for yr, val in zip(full_years, yearly_imputed):
                idx = df.loc[x.index, "year"] == yr

                if distribute:
                    # Smooth distribution within the year
                    n = idx.sum()
                    if n > 1:
                        # FIX: Use .iloc to access by integer position, not label
                        prev_val = yearly_imputed.iloc[max(0, list(full_years).index(yr)-1)]
                        step = (val - prev_val) / n
                        seq = np.array([prev_val + i*step for i in range(n)])
                    else:
                        seq = np.full(idx.sum(), val)
                else:
                    # Constant value within the year
                    seq = np.full(idx.sum(), val)

                out[idx] = seq

            return x.fillna(out)

        df[col] = df.groupby("cmapuid_int")[col].transform(transform)

    df.drop(columns="year", inplace=True)
    return df


def impute_full_pipeline(df, columns_by_group, census_distribute=False):

    """
    Full automatic imputation pipeline.
    Applies the imputation function to each group of variables.

    Parameters
    ----------
    df : pd.DataFrame
        Original dataset.
    columns_by_group : dict
        Mapping from group name → list of columns.
    census_distribute : bool
        Whether Census/Core Housing Need should distribute values within each year.

    Returns
    -------
    pd.DataFrame
        Fully imputed dataset.
    """

    df_out = df.copy()

    for group, cols in columns_by_group.items():

        existing_cols = [c for c in cols if c in df_out.columns]

        if not existing_cols:
            print(f"Skipping group: {group} (No matching columns found in DataFrame)")
            continue

        if group == "RMS – Annual Average Rent Percent Change":
           print(f"Skipping group: {group} (will be computed after imputation)")
           continue


        print(f"→ Processing group: {group} ({len(existing_cols)} columns)")

     
        df_out = linear_impute(
                df_out, existing_cols,
                distribute=census_distribute)
        
        print(f"Imputation on {group} is finished.")


    return df_out


def compute_rms_percent_change(df, avg_rent_col, pct_change_col) -> pd.DataFrame:

    """
    Computes RMS Annual Percent Rent Change from RMS Average Rent.
    - Percent change is derived, not interpolated.
    - Applies pct_change() at the annual level.
    - Creates a new column with suffix '_imputed'.
    """

    df = df.copy()
    df["year"] = df["date"].dt.year

    def transform(x):
        yearly = x.groupby(df.loc[x.index, "year"]).mean()
        pct = yearly.pct_change(fill_method=None) * 100

        out = x.copy()
        for yr, val in pct.items():
            out[df.loc[x.index, "year"] == yr] = val

        return out

    # To avoid overwriting on existing column
    pct_change_col = f"{pct_change_col}_imputed"

    df[pct_change_col] = df.groupby("cmapuid_int")[avg_rent_col].transform(transform)
    df.drop(columns="year", inplace=True)
    return df


# Computing RMS percent change, given RMS imputted results


def apply_all_rms_changes(df_imputed, columns_by_group) -> pd.DataFrame:

    """
    Computes annual percent changes from the imputed Rent columns.
    """

    df_out = df_imputed.copy()

    # Exact name of the group skipped during the initial pipeline
    target_group = "RMS – Annual Average Rent Percent Change"

    if target_group not in columns_by_group:
        print(f"Warning: Group '{target_group}' not found in dictionary.")
        return df_out

    # Percent change columns (e.g., rms_average_rent_change_bedroom_type_1_bedroom)
    pct_cols = columns_by_group[target_group]

    for pct_col in pct_cols:

        # Identify the base column by removing '_change'
        # Example: 'rms_average_rent_change_bedroom_type_1_bedroom' -> 'rms_average_rent_bedroom_type_1_bedroom'

        base_rent_col = pct_col.replace("_change", "")

        if base_rent_col in df_out.columns:
            print(f"Deriving: {pct_col}_imputed from {base_rent_col}")

            # Call to the compute_rms_percent_change function
            # Note: This function internally creates the _imputed suffix and leaves pct_col intact
            df_out = compute_rms_percent_change(
                df=df_out,
                avg_rent_col=base_rent_col,
                pct_change_col=pct_col
            )
        else:
            print(f"Warning: Base column '{base_rent_col}' not found to derive '{pct_col}'")

    return df_out


x_train_imputed = impute_full_pipeline(
    x_train,
    columns_by_group,
    census_distribute=False
)

x_train_imputed = apply_all_rms_changes(x_train_imputed, columns_by_group)


### QUICK VISUALIZATION OF RESULTS ####

def plot_group(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    group_name: str,
    columns_by_group: dict,
    cma: str,
    variables=None,
    show_missing=False,
    max_cols=6
):

    """
    Visualizes original vs imputed values for a given group and GeoUID.

    Parameters
    ----------
    variables : None, str, or list of str
        - None → plot all variables in the group (default)
        - str → plot only that variable
        - list[str] → plot only those variables
    """

    if group_name not in columns_by_group:
        raise ValueError(f"Group '{group_name}' not found in columns_by_group.")

    group_cols = columns_by_group[group_name]

    if len(group_cols) == 0:
        print(f"Group '{group_name}' has no columns.")
        return

    if variables is None:
        cols = group_cols
    elif isinstance(variables, str):
        cols = [variables]
    else:
        cols = variables

    # Validate selected variables
    cols = [c for c in cols if c in group_cols]
    if len(cols) == 0:
        print(f"No valid variables selected for group '{group_name}'.")
        return

    # Limit number of columns
    if len(cols) > max_cols:
        print(f"Group '{group_name}' has {len(cols)} selected variables. Showing first {max_cols}.")
        cols = cols[:max_cols]

    # Filter by GeoUID
    df_o = df_original[df_original["cma_canonical"] == cma].copy()
    df_i = df_imputed[df_imputed["cma_canonical"] == cma].copy()

    if df_o.empty:
        print(f"No data found for CMA {cma}.")
        return

    # Ensure datetime
    df_o["date"] = pd.to_datetime(df_o["date"])
    df_i["date"] = pd.to_datetime(df_i["date"])

    plt.figure(figsize=(16, 7))

    for col in cols:
        if col not in df_i.columns:
            print(f"Column '{col}' missing in imputed dataset. Skipping.")
            continue

        # Original values
        plt.plot(
            df_o["date"], df_o[col],
            "o", alpha=0.5,
            label=f"{col} (original)"
        )

        # Imputed values
        plt.plot(
            df_i["date"], df_i[col],
            "-", alpha=0.8,
            label=f"{col} (imputed)"
        )

        # Highlight missing original values
        if show_missing:
            missing_mask = df_o[col].isna()
            plt.scatter(
                df_o["date"][missing_mask],
                df_i[col][missing_mask],
                color="red", s=40, marker="x",
                label=f"{col} (imputed over missing)"
            )

    plt.title(f"Group: {group_name} — CMA {cma}", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.grid(alpha=0.3)
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.tight_layout()
    plt.show()


# Example: Check imputation results for Census variables

"""
plot_group(
x_train,
x_train_imputed,
"Census – Age of Population",
columns_by_group,
cma="London, Ontario",
variables="census_all_households_age_of_population_25_34"
)
"""

### DATA PREPARATION FOR FEATURE SELECTION

#Keep a copy of the imputed training data with all features
#x_train_imputed_all = x_train_imputed.copy()

#Create one which doesn't have variables linearly dependent on the target
x_train_imputed = x_train_imputed.dropna(subset=['house', 'land'])

def prepare_data_for_feature_selection(df, drop_target_nan=True):

    df_copy = df.copy()

    df_copy = df_copy.sort_values(by=['cma_canonical', 'date']).reset_index(drop=True)

    # --- Identify columns to exclude from lagging and being direct features ---
    base_excluded_cols = [
        'total',       #The target variable itself
        'cmapuid_int', #Identifier
        'house',       # Excluded from being a predictor (lagged or not)
        'land' ,        # Excluded from being a predictor (lagged or not)
        'date',         #Excluded because it's not a relevant feature
        'GeoUID'        #Excluded because it's not a relevant feature  
    ]

    # --- Identify all numerical columns present in the DataFrame ---
    all_numerical_cols = df_copy.select_dtypes(include=np.number).columns.tolist()

    # --- Determine which columns will be lagged (all numerical except time features and explicitly excluded) ---
    cols_to_lag = [
        col for col in all_numerical_cols
        if col not in base_excluded_cols
    ]

    # Special handling for 'total' to ensure 'total_lag_1' and 'total_lag_12' are created and used.
    if 'total' in all_numerical_cols:
        # Ensure 'total' is in cols_to_lag to generate its lags
        if 'total' not in cols_to_lag:
            cols_to_lag.append('total')

    # --- Create lag features for selected numerical columns ---
    lagged_series = []
    lagged_feature_names = []

    for col in cols_to_lag:
        new_lag_col_name_1 = f'{col}_lag_1'
        lagged_series.append(df_copy.groupby('cma_canonical')[col].shift(1).rename(new_lag_col_name_1))
        lagged_feature_names.append(new_lag_col_name_1)

    # Concatenate all lagged features at once
    if lagged_series:
        df_copy = pd.concat([df_copy] + lagged_series, axis=1)

    # --- Construct the final set of feature columns for X in feature selection ---
    # These are only the new lagged features after removing direct time components.
    final_feature_cols = lagged_feature_names

    X_all_features = df_copy[final_feature_cols]
    y = df_copy['total']
    cma_col = df_copy['cma_canonical']

    # Impute NaNs in X_all_features first, as suggested by the model context.
    # Use ffill then bfill within each CMA group.
    X_imputed = X_all_features.groupby(cma_col).ffill().bfill()
    # As a fallback, fill any remaining NaNs (e.g., if a group was entirely NaN after shifting)
    X_imputed = X_imputed.fillna(0) # Ensure no NaNs in features for SFS

    # Combine X_imputed and y
    combined_df = pd.concat([X_imputed, y], axis=1)

    # Apply dropna conditionally, only on the target variable 'total' for training data.
    if drop_target_nan:
        # For training, drop rows where the target 'total' is NaN.
        combined_df_cleaned = combined_df.dropna(subset=['total'])
    else:
        # For test set, we might want to keep rows with NaN targets for prediction,
        # but features must be clean (already handled by X_imputed).
        # No additional dropping on features is needed here, just ensure target is aligned.
        combined_df_cleaned = combined_df #X_imputed is already clean

    X_final = combined_df_cleaned[X_imputed.columns] # Re-select columns in case any were dropped
    y_final = combined_df_cleaned['total']

    # Add a check to ensure X_final and y_final are not empty
    if X_final.empty or y_final.empty:
        raise ValueError("DataFrame became empty after NaN handling. Adjust imputation or dropna strategy.")

    return X_final, y_final

# Define filenames for saving/loading
X_TRAIN_FS_FILE = ROOT / "prediction" / "X_train_FS.csv"
Y_TRAIN_FS_FILE = ROOT / "prediction" / "y_train_FS.csv"

if os.path.exists(X_TRAIN_FS_FILE) and os.path.exists(Y_TRAIN_FS_FILE):
    print(f"Loading X_train_fs and y_train_fs from {X_TRAIN_FS_FILE} and {Y_TRAIN_FS_FILE}...")
    X_train_fs = pd.read_csv(X_TRAIN_FS_FILE)
    y_train_fs = pd.read_csv(Y_TRAIN_FS_FILE).squeeze() # Use squeeze for Series

else:
    print("Files not found. Preparing data for feature selection and saving...")
    # Using x_train_imputed to ensure all original CMHC features are considered before exclusion rules are applied
    X_final_full, y_final_full = prepare_data_for_feature_selection(x_train_imputed, drop_target_nan=True)

    X_train_fs, _, y_train_fs, _ = train_test_split(X_final_full, y_final_full, test_size=0.85, random_state=42)

    constant_features = X_train_fs.columns[X_train_fs.nunique() == 1]

    if not constant_features.empty:
       print(f"Constant features to drop: {list(constant_features)}")
       X_train_fs = X_train_fs.drop(columns=constant_features)

    # Save to CSV files

    X_train_fs.to_csv(X_TRAIN_FS_FILE, index=False)
    y_train_fs.to_csv(Y_TRAIN_FS_FILE, index=False, header=True) # Save header for y for consistency
    print(f"Saved X_train_fs to {X_TRAIN_FS_FILE}")
    print(f"Saved y_train_fs to {Y_TRAIN_FS_FILE}")

    print(f"X_train_fs shape: {X_train_fs.shape}")




