# CMHC / Statistics Canada Housing Dataset

## Data Dictionary

Geographic unit: Census Metropolitan Area
Source programs: CMHC (SCSS, RMS, SRMS, Core Housing Need) and Statistics Canada Census

---

# Common Columns

| Column   | Description                                                                                                                       |
| -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `geouid` | Census Metropolitan Area unique identifier (CMA_UID).                                                                             |
| `date`   | Reference date of observation. Monthly for SCSS, annual for RMS and SRMS, census reference year for Census and Core Housing Need. |

---

# SCSS — Starts and Completions Survey

Source: CMHC Starts and Completions Survey
Frequency: Monthly
Unit: Dwelling units unless otherwise noted

Dwelling types include: `single`, `semi_detached`, `row`, `apartment`, `all`.

## Construction Activity

### `scss_starts_dwelling_type_*`

Number of housing units on which construction began during the reference period.

### `scss_completions_dwelling_type_*`

Number of housing units completed during the reference period.

### `scss_under_construction_dwelling_type_*`

Number of dwelling units under construction at the end of the reference period.

### `scss_length_of_construction_dwelling_type_*`

Average number of months required to complete residential construction from start to completion.
Unit: Months.

---

## Market Absorption

### `scss_absorbed_units_dwelling_type_*`

Number of newly completed units that have been sold or rented.

### `scss_share_absorbed_at_completion_dwelling_type_*`

Percentage of completed units that were absorbed at the time of completion.
Unit: Percent.

### `scss_unabsorbed_inventory_dwelling_type_*`

Number of completed units not yet absorbed.

---

# RMS — Rental Market Survey

Source: CMHC Rental Market Survey
Frequency: Annual
Universe: Purpose-built rental apartment structures with three or more units

Bedroom types include: `studio`, `1_bedroom`, `2_bedroom`, `3_bedroom`, `total`.

### Vacancy and Availability

#### `rms_vacancy_rate_bedroom_type_*`

Percentage of rental units vacant and available for immediate occupancy on survey date.

#### `rms_availability_rate_bedroom_type_*`

Percentage of rental units vacant or becoming available within a short defined period.

---

### Rent Levels

#### `rms_average_rent_bedroom_type_*`

Average monthly rent of occupied units.
Unit: Canadian dollars.

#### `rms_median_rent_bedroom_type_*`

Median monthly rent of occupied units.
Unit: Canadian dollars.

#### `rms_average_rent_change_bedroom_type_*`

Annual percentage change in average rent.

---

### Supply

#### `rms_rental_universe_bedroom_type_*`

Total number of rental units in the survey universe.

#### `rms_summary_statistics`

Aggregate RMS indicator supplied by CMHC for overall rental market summary.

---

# SRMS — Secondary Rental Market Survey

Source: CMHC Secondary Rental Market Survey
Frequency: Annual

Covers condominium apartments and other secondary rental dwellings.

---

## Condominium Apartments

Structure sizes include: `3_19_units`, `20_49_units`, `50_99_units`, `100_units`, `total`.

### `srms_condo_universe_structure_size_*`

Total number of condominium apartments.

### `srms_rental_condo_universe_structure_size_*`

Number of condominium apartments used as rental units.

### `srms_percentage_condo_used_as_rental_structure_size_*`

Percentage of condominium apartments rented out.

### `srms_condo_vacancy_rate_structure_size_*`

Vacancy rate among rented condominium apartments.

---

## Condo Rents

Bedroom types include: `studio`, `1_bedroom`, `2_bedroom`, `3_bedroom`, `total`.

### `srms_condo_average_rent_bedroom_type_*`

Average monthly rent for condominium apartments.
Unit: Canadian dollars.

---

## Other Secondary Rentals

Dwelling types include:

* `single`
* `semi_row_duplex`
* `other_primarily_accessory_suites`
* `total`

### `srms_other_seconary_rental_universe_dwelling_type_*`

Estimated number of other secondary rental units.

---

# Statistics Canada Census Variables

Reference year: Census year
Units vary by measure

---

## Income

### `census_income_average_and_median_average_household_income_before_taxes`

Average total household income before income taxes.
Unit: Canadian dollars.

### `census_income_average_and_median_average_household_income_after_taxes`

Average total household income after income taxes.

### `census_income_average_and_median_median_household_income_before_taxes`

Median total household income before income taxes.

### `census_income_average_and_median_median_household_income_after_taxes`

Median total household income after income taxes.

---

## Dwelling Value

Values by structural dwelling type:
`single_detached`, `semi_detached`, `row`, `duplex`, `low_rise_apt`, `high_rise_apt`, `other`, `total`

### `census_dwelling_value_average_*`

Average value of owner-occupied dwellings.
Unit: Canadian dollars.

### `census_dwelling_value_median_*`

Median value of owner-occupied dwellings.

---

## Age of Population

### `census_all_households_age_of_population_*`

Population by age group within all households. Age bands include:
`0_14`, `15_24`, `25_34`, `35_44`, `45_54`, `55_64`, `total`, `total_65`.

### `census_65_and_over_age_of_population_*`

Population aged 65 and over by detailed age band:
`65_74`, `75_84`, `85`, `total`, `total_65`.

---

## Age of Primary Household Maintainer

### `census_all_households_age_of_primary_household_maintainer_*`

Age distribution of primary household maintainer.

### `census_65_and_over_age_of_primary_household_maintainer_*`

Age distribution of primary household maintainer for households aged 65 and over.

---

## Mobility

Mobility measures whether individuals changed residence.

### `census_mobility_1_of_all_households_age_of_primary_household_maintainer_*`

Mobility status one year prior to census.

### `census_mobility_5_of_all_households_age_of_primary_household_maintainer_*`

Mobility status five years prior to census.

### `census_mobility_1_of_65_and_over_age_of_primary_household_maintainer_*`

Mobility for population aged 65 and over, one-year horizon.

### `census_mobility_5_of_65_and_over_age_of_primary_household_maintainer_*`

Mobility for population aged 65 and over, five-year horizon.

Units: Percent or count depending on CMHC extraction.

---

# Core Housing Need — CMHC

Core housing need identifies households living in housing that does not meet adequacy, suitability, or affordability standards and who cannot afford alternative suitable housing.

Housing standards include:

* Adequacy
* Suitability
* Affordability
* One or more standards

---

## Counts

### `core_housing_need_housing_standards_households_in_core_housing_need_*`

Number of households in core housing need by housing standard category.

### `core_housing_need_housing_standards_households_tested_for_core_housing_need_*`

Total households assessed for core housing need by standard.

---

## Percentages

### `core_housing_need_housing_standards_of_households_in_core_housing_need_*`

Percentage of households in core housing need by housing standard category.

---

# Measurement Notes

* Counts represent dwelling units or households.
* Rent and income values are expressed in Canadian dollars.
* Rates and percentages are expressed as percent.
* Census data reflect conditions at the census reference date.
* RMS and SRMS are annual point-in-time surveys.
* SCSS is monthly administrative construction tracking.