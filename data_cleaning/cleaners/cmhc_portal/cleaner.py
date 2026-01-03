from abc import ABC, abstractmethod
from enum import StrEnum
import io
import logging
import os
from pathlib import Path
import re
import time
import pandas as pd
import numpy as np
from typing import Dict, Any, Union

from base_cleaner import BaseCleaner

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# some categories have different formats for downloaded csvs, so we define an interface for parsing them
class CsvParser(ABC):
        @abstractmethod
        def parse(self, filepath: str, cma_code: str, col_prefix: str, logger: logging.Logger) -> pd.DataFrame:
            pass

        def _parse_csv(self, filepath: str) -> pd.DataFrame:
            with open(filepath, 'r', errors='replace') as file:
                lines = file.readlines()
                # remove first 2 lines, and then all the lines after the empty line
                lines = lines[2:]
                for i, line in enumerate(lines):
                    if line == '\n':
                        lines = lines[:i]
                        break
                
                df = pd.read_csv(io.StringIO(''.join(lines)), thousands=',')
                return df.iloc[:, :-1] # excess empty column
            

        def _convert_cells_to_numeric(self, df: pd.DataFrame, logger: logging.Logger) -> pd.Dataframe:
            def map(cell_raw) -> np.float64:
                try:
                    cell = re.sub(r'[,$% ]', '', str(cell_raw))
                    cell = np.float64(cell)
                    if np.isclose(cell, 0.0):
                        logger.warning(f"setting zero '{cell}' as nan")
                        return np.nan    
                    return cell
                except:
                    logger.warning(f"could not process cell value '{cell_raw}', setting as nan")

                    return np.nan 

            # assume first column is date, so don't convert
            df.iloc[:, 1:] = df.iloc[:, 1:].map(map)
            return df
        
        def _remove_nan_or_rating_cols(self, df: pd.DataFrame) -> pd.DataFrame:
            # delete any 'rating' columns that are just a letter, or nan
            return df.loc[:, ~df.apply(lambda col: col.dropna().astype(str).str.match(r'^[abcd] ?$').all())]


# column format for the final merged dataframe is:
# cma_code | year | month | other items...
# month is a 3 letter lowercase abbreviation

class DefaultCsvParser(CsvParser):
    def parse(self, filepath, cma_code, col_prefix, logger):
        df = self._parse_csv(filepath)
        df = self._convert_cells_to_numeric(df, logger)
        df = self._remove_nan_or_rating_cols(df)

        df = df.rename(columns={df.columns[0]: 'year'}) # year column missing a name
        df.insert(loc=0, column='cma_code', value=cma_code)
        df.columns = list(df.columns[:2]) + [col_prefix + '  ' + col for col in df.columns[2:]] # prefix all columns except year and cma_code
        df = df.rename(columns=lambda col: re.sub(r'[^a-zA-Z0-9]', '_', col)) # replace special characters with underscores in column names
        return df

class AbbreviatedMonthYearCsvParser(CsvParser):
    def parse(self, filepath, cma_code, col_prefix, logger):
        df = self._parse_csv(filepath)
        df = self._convert_cells_to_numeric(df, logger)
        df = self._remove_nan_or_rating_cols(df)
        
        df = df.rename(columns={df.columns[0]: 'year'}) # year column missing a name
        df.insert(loc=1, column='month', value=np.nan) # month column missing
        df[['month', 'year']] = df['year'].str.split(expand=True) # currently year column is of the form "month year", need to split it
        df['month'] = df['month'].map(lambda m: m.lower())
        df['year'] = df['year'].astype(np.int64)
        df.insert(loc=0, column='cma_code', value=cma_code)
        df['cma_code'] = df['cma_code'].astype(str)
        df.columns = list(df.columns[:3]) + [col_prefix + '  ' + col for col in df.columns[3:]] # prefix all columns except year month and cma_code
        df = df.rename(columns=lambda col: re.sub(r'[^a-zA-Z0-9]', '_', col)) # replace special characters with underscores in column names
        return df


class YearMonthCsvParser(CsvParser):
    def parse(self, filepath, cma_code, col_prefix, logger):
        df = self._parse_csv(filepath)
        df = self._convert_cells_to_numeric(df, logger)
        df = self._remove_nan_or_rating_cols(df)

        df = df.rename(columns={df.columns[0]: 'year'}) # year column missing a name
        df.insert(loc=1, column='month', value=np.nan) # month column missing
        df[['year', 'month']] = df['year'].str.split(expand=True) # currently year column is of the form "year month", need to split it
        df['year'] = df['year'].astype(np.int64)
        df['month'] = df['month'].map(lambda m: m[:3].lower()) # shorten month to 3 letters
        df.insert(loc=0, column='cma_code', value=cma_code)
        df['cma_code'] = df['cma_code'].astype(str)
        df.columns = list(df.columns[:3]) + [col_prefix + '  ' + col for col in df.columns[3:]] # prefix all columns except year and cma_code
        df = df.rename(columns=lambda col: re.sub(r'[^a-zA-Z0-9]', '_', col)) # replace special characters with underscores in column names
        return df
    
class StartsSaarParser(YearMonthCsvParser):
    # the starts (SAAR) scrape target's downloaded file, unlike other targets, does not have the csv header line so we have to add one
    def _parse_csv(self, filepath: str) -> pd.DataFrame:
            with open(filepath, 'r', errors='replace') as file:
                lines = file.readlines()
                # remove first 2 lines, and then all the lines after the empty line
                lines = lines[2:]
                lines = [',Starts,\n'] + lines # add our starts (saar) header
                for i, line in enumerate(lines):
                    if line == '\n':
                        lines = lines[:i]
                        break
                
                df = pd.read_csv(io.StringIO(''.join(lines)), thousands=',')
                return df.iloc[:, :-1] # excess empty column
        


class Cleaner(BaseCleaner):
    CMHC_CMA_LIST = {
	# "St. John's": "1640/3/St.%20John's",
	# 'Halifax': '0580/3/Halifax',
	# 'Ottawa': '1265/3/Ottawa',
	# 'Québec': '1400/3/Québec',
	# 'Sherbrooke': '1800/3/Sherbrooke',
	# 'Trois-Rivières': '2320/3/Trois-Rivières',
	# 'Montréal': '1060/3/Montréal',
    # 'Saguenay': '0180/3/Saguenay',
    # 'Drummondville': '0280/3/Drummondville',
	# 'Oshawa': '1250/3/Oshawa',
	'Toronto': '2270/3/Toronto',
	# 'Hamilton': '0610/3/Hamilton',
	# 'St. Catharines-Niagara': '1160/3/St.%20Catharines%20-%20Niagara',
	# 'Kitchener-Cambridge-Waterloo': '0850/3/Kitchener%20-%20Cambridge%20-%20Waterloo',
	# 'Guelph': '0460/3/Guelph',
	# 'London': '0950/3/London',
	# 'Windsor': '2640/3/Windsor',
	# 'Greater Sudbury': '2000/3/Greater%20Sudbury%20%2F%20Grand%20Sudbury',
    # 'Barrie': '0120/3/Barrie',
    # 'Kingston': '0700/3/Kingston',
    # 'Brantford': '0125/3/Brantford',
    # 'Peterborough': '1320/3/Peterborough',
    # 'Thunder Bay': '2240/3/Thunder Bay',
    # 'Belleville-Quinte West': '0122/3/Belleville - Quinte West',
	# 'Winnipeg': '2680/3/Winnipeg',
	# 'Regina': '1490/3/Regina',
	# 'Saskatoon': '1700/3/Saskatoon',
	# 'Calgary': '0140/3/Calgary',
	# 'Edmonton': '0340/3/Edmonton',
    # 'Red Deer': '1420/3/Red Deer',
    # 'Lethbridge': '0870/3/Lethbridge',
	# 'Kelowna': '0670/3/Kelowna',
	# 'Vancouver': '2410/3/Vancouver',
	# 'Victoria': '2440/3/Victoria',
    # 'Charlottetown': '3300/3/Charlottetown',
    # 'Abbotsford - Mission': '0110/3/Abbotsford - Mission',
    # 'Nanaimo': '1100/3/Nanaimo',
    # 'Kamloops': '0650/3/Kamloops',
    # 'Chilliwack': '0210/3/Chilliwack',
	# 'Saint John': '1600/3/Saint%20John',
	# 'Fredericton': '0370/3/Fredericton',
	# 'Moncton': '1040/3/Moncton'
	}

    class CategoryHead(StrEnum):
        HOUSING_STOCK = 'Population, Households and Housing Stock'
        NEW_CONSTRUCTION = 'New Housing Construction'
        PRIMARY_RENTAL_MARKET = 'Primary Rental Market'
        SECONDARY_RENTAL_MARKET = 'Secondary Rental Market'

    class ScrapeTarget:
        def __init__(self, category_head: str, category_name: str, download_directory: str, file_postfix: str, parser: CsvParser = None,
                     historic: bool = True, sub_categories: list[str] = [], sub_cat_type: str = 'dwelling', multipart_download = False,
                     category_index = 1, expected_columns = -1):
            self.category_head = category_head
            self.category_name = category_name
            self.download_directory = download_directory
            self.file_postfix = file_postfix
            if parser is None:
                parser = DefaultCsvParser()
            self.parser = parser
            self.historic = historic
            self.sub_categories = sub_categories
            self.sub_cat_type = sub_cat_type
            self.multipart_download = multipart_download
            self.category_index = category_index # in case the category_name appears more than once under the category_head drop down
            self.expected_columns = expected_columns # after parsing, assert this value is true


    SCRAPE_TARGETS = [
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Age of Primary Household Maintainer', 'household', 'age', expected_columns=9),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Mobility of Primary Household Maintainer', 'household', 'mobility', expected_columns=9),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Household Type', 'household', 'type', expected_columns=9),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Household Size', 'household', 'size', expected_columns=8),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Immigrant Households', 'household', 'immigrant', expected_columns=7),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Households with Seniors', 'household', 'senior', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Households with Children Under 18', 'household', 'children', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Activity Limitations', 'household', 'activity-limits', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Aboriginal Households', 'household', 'aboriginal', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Shelter Costs', 'shelter', 'shelter-costs', expected_columns=8),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Mortgages', 'household', 'mortgage', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Household Income', 'household', 'income', expected_columns=9),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Condominiums', 'household', 'condominium', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Housing Suitability', 'household', 'suitability', expected_columns=5),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Value of Owner-occupied Dwellings ($)', 'household', 'value', expected_columns=10),
        ScrapeTarget(CategoryHead.HOUSING_STOCK, 'Period of Construction and Condition of Dwelling', 'condition', 'period-construction', expected_columns=6),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Starts (Actual)', 'new_construction', 'starts-actual', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Starts (SAAR)', 'new_construction', 'starts-saar', parser=StartsSaarParser(), historic=False, expected_columns=4),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Completions', 'new_construction', 'completions', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Under Construction Inventory', 'new_construction', 'inventory-construction', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Length of Construction (in months)', 'new_construction', 'length-construction', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Absorbed Units (Homeowner + Condo)', 'new_construction', 'absorbed', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, '% of Absorbed Units at Completion (Homeowner + Condo)', 'new_construction', 'absorbed-percent', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Inventory of Completed and Unabsorbed Units (Homeowner + Condo)', 'new_construction', 'inventory-completed-unabsorbed', parser=AbbreviatedMonthYearCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Absorbed Unit Prices ($)', 'new_construction', 'prices-absorbed', parser=YearMonthCsvParser(), expected_columns=10),
        ScrapeTarget(CategoryHead.NEW_CONSTRUCTION, 'Unabsorbed Unit Prices ($)', 'new_construction', 'prices-unabsorbed', parser=YearMonthCsvParser(), expected_columns=10),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, 'Vacancy Rate (%)', 'primary_rental', 'vacancy', parser=YearMonthCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, 'Availability Rate (%)', 'primary_rental', 'availability', parser=YearMonthCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, 'Average Rent ($)', 'primary_rental', 'rent-average', parser=YearMonthCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, '% Change of Average Rent', 'primary_rental', 'percent-change', parser=YearMonthCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, 'Median Rent ($)', 'primary_rental', 'rent-median', parser=YearMonthCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, 'Rental Universe', 'primary_rental', 'universe', parser=YearMonthCsvParser(), expected_columns=8),
        ScrapeTarget(CategoryHead.PRIMARY_RENTAL_MARKET, 'Summary Statistics', 'primary_rental', 'summary', parser=YearMonthCsvParser(), expected_columns=9),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Estimated Number of Households', 'secondary_rental', 'estimated_households', historic=False, expected_columns=6),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Average Rent ($)', 'secondary_rental', 'average_rent_other_dwellings', historic=False, category_index=1, expected_columns=6),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Vacancy Rate (%)', 'secondary_rental', 'vacancy_rate', historic=False, expected_columns=7),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Average Rent ($)', 'secondary_rental', 'average_rent_condominium_apartments', historic=False, category_index=2, expected_columns=7),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Estimated Number of Condominium Units', 'secondary_rental', 'estimated_condos', historic=False, expected_columns=7),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Estimated Number of Condominium Units used for Rental', 'secondary_rental', 'estimated_condos_rentals', historic=False, expected_columns=7),
        ScrapeTarget(CategoryHead.SECONDARY_RENTAL_MARKET, 'Percentage (%) of All Condominiums used for Rental', 'secondary_rental', 'percent_estimated_condos_rent', historic=False, expected_columns=7),
    ]


    def get_metadata(self) -> Dict[str, Any]:
        return {
            'source': 'CHMC Housing Market Information Portal',
            'description': 'data from Canada Housing and Mortgage Corporation\'s web portal',
            'update_frequency': 'on-demand',
            'type': 'synthetic' #TODO figure out what this item is for
        }
        

    def download_data(self, format: str = 'dataframe') -> Union[pd.DataFrame, np.ndarray]:
        if format not in ['dataframe', 'array']:
            raise ValueError(f'{format} is not a valid value for format parameter')

        dataframes = []
        for scrape_target in self.SCRAPE_TARGETS:
            dataframe = self.scrape_category(scrape_target)
            dataframes.append(dataframe)
        
        self.logger.debug(f"obtained {dataframes}")
        self.logger.info(f"obtained {len(dataframes)} dataframes in total")

        merged_dataframes = self.merge_dataframes(dataframes)

        if format == 'dataframe':
            return merged_dataframes
        else:
            return merged_dataframes.to_numpy()


    def clean_data(self, raw_data: Union[pd.DataFrame, np.ndarray]) -> Union[pd.DataFrame, np.ndarray]:
        return raw_data # temporary

    def scrape_category(self, scrape_target: ScrapeTarget) -> pd.DataFrame:
        dataframes = []
        for cma, cma_code in self.CMHC_CMA_LIST.items():
            dataframes_for_cma = self.retry_func(self.scrape_cma,
                cma,
                cma_code,
                scrape_target)
            dataframes.extend(dataframes_for_cma)
        
        self.logger.debug(f"obtained {dataframes} from category {scrape_target.category_name}")
        self.logger.info(f"obtained {len(dataframes)} dataframes from category {scrape_target.category_name}")
        return pd.concat(dataframes)

    def scrape_cma(self, cma: str, cma_code: str, scrape_target: ScrapeTarget) -> list[pd.DataFrame]:
        download_dir = os.path.join(os.getcwd(), 'raw', scrape_target.download_directory)


        # check if we've already scraped this data
        if scrape_target.file_postfix != '':
            existing_filename = cma + ' - ' + ' - ' + scrape_target.file_postfix + '.csv'
        else:
            existing_filename = cma + ' - ' + '.csv'
        existing_filename = os.path.join(download_dir, existing_filename)
        if os.path.exists(existing_filename):
            self.logger.info(f"using cached '{existing_filename}'")

            dataframe = scrape_target.parser.parse(existing_filename, cma_code, scrape_target.download_directory + '_' + scrape_target.file_postfix, self.logger)
            if scrape_target.expected_columns != -1 and scrape_target.expected_columns != len(dataframe.columns):
                raise AssertionError(f"expected {scrape_target.expected_columns} columns for '{scrape_target.category_name}' scrape target but there were {len(dataframe.columns)}")
            
            return [dataframe]
        

        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,  # Disable download prompt
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        
        url = "https://www03.cmhc-schl.gc.ca/hmip-pimh/en/TableMapChart?id=7175&t=3#TableMapChart/" + cma_code
        driver.get(url)

        # Accept the terms and conditions popup
        # Check the checkbox
        checkbox_xpath = '//input[@id="iAccept"]'
        checkbox = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, checkbox_xpath)))
        driver.execute_script("arguments[0].click();", checkbox)
        
        # Click the 'get started' button
        button_xpath = '//p[@class="introOverlaygetStartedButton"]/a[@class="button"]'
        button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        button.click()
        
        # Wait for the dropdown to be clickable
        dropdown_xpath = '//a[@class="subsection-link" and text()="' + scrape_target.category_head + '"]'
        dropdown = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
        
        # Click on the dropdown
        dropdown.click()
        
        # Wait for metric link to be clickable
        link_xpath = f'//a[text()="{scrape_target.category_head}"]/following::a[text()="{scrape_target.category_name}"][{scrape_target.category_index}]'
        link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, link_xpath)))
        
        # Click on the metric link
        link.click()
        
        # Wait for the "Historical Time Periods" link to be clickable
        if scrape_target.historic:
            historical_link_xpath = '//a[text()="Historical Time Periods"]'
            historical_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, historical_link_xpath)))
            
            # Click on the "Historical Time Periods" link
            historical_link.click()

            # Wait for "Historical Time Periods" chart to display
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return jQuery.active') == 0)
            time.sleep(1) # to be extra safe
            
            
        dataframes = []
        # Loop through sub-categories
        if len(scrape_target.sub_categories) > 0:
            raise NotImplementedError("this flow is untested. Delete this line, but use with caution!")
            for cat in scrape_target.sub_categories:
            
                # Wait for the dropdown to be clickable
                if scrape_target.sub_cat_type == 'dimension':
                    dropdown_xpath = '//a[@id="filterBydimension-18Link" and contains(@class, "menu-link")]'
                elif scrape_target.sub_cat_type == 'dwelling':
                    dropdown_xpath = '//a[@id="filterBydwelling_type_desc_enLink" and contains(@class, "menu-link")]'
                dropdown = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
                
                # Click on the dropdown
                dropdown.click()
                
                # Wait for the sub-category option to be clickable
                if scrape_target.sub_cat_type == 'dimension':
                    dropdown_xpath = '//a[@data-key="dimension-18" and @data-value="' + cat + '"]'
                elif scrape_target.sub_cat_type == 'dwelling':
                    dropdown_xpath = '//a[@data-key="dwelling_type_desc_en" and @data-value="' + cat + '"]'
                subcat_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, scrape_target.subcat_option_xpath)))
                
                # Click on the sub-category option
                subcat_option.click()
                
                # Pause for five seconds
                time.sleep(5)
                
                # Wait for the "Export" button to be clickable
                export_button_xpath = '//a[@id="exportTableLink" and contains(@class, "button secondary")]'
                export_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, export_button_xpath)))
                
                # Click on the "Export" button
                export_button.click()
                
                # Wait for the "Export to Spreadsheet (CSV)" option to be clickable
                export_csv_xpath = '//a[@data-export-type="csv"]'
                export_csv_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, export_csv_xpath)))
                
                # Click on the "Export to Spreadsheet (CSV)" option
                export_csv_option.click()
                
                # Wait to ensure the export completes
                time.sleep(5)
                
                # Get the list of files in the download directory
                files = os.listdir(download_dir)
                
                # Filter out directories, if any
                files = [file for file in files if os.path.isfile(os.path.join(download_dir, file))]
                
                # Sort files based on modification time (newest first)
                sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                
                # Assume at least one file is present
                most_recent_filename = sorted_files[0]
                
                # Specify the new filename
                if scrape_target.file_postfix != '':
                    new_filename = cma + ' - ' + cat.replace("/", "or") + ' - ' + scrape_target.file_postfix + '.csv'
                else:
                    new_filename = cma + ' - ' + cat.replace("/", "or") + '.csv'
                
                # Create the full paths for both the original and new filenames
                original_filepath = os.path.join(download_dir, most_recent_filename)
                new_filepath = os.path.join(download_dir, new_filename)
                
                # Rename the file
                os.rename(original_filepath, new_filepath)
                
                # Wait for a short time to ensure the rename operation completes
                time.sleep(1)

                dataframes.append(scrape_target.parser.parse(new_filepath, cma_code, scrape_target.category_name + ' - ' + cat, self.logger))
                
            # Close the browser window
            driver.quit()
    
        # Proceed if no subcategories are present
        else:
            # Click on the "Export to Spreadsheet (CSV)" option and download the file
            downloaded_file = self.download_file(download_dir, lambda: self.select_download(driver))

            # Specify the new filename
            if scrape_target.file_postfix != '':
                new_filename = cma + ' - ' + ' - ' + scrape_target.file_postfix + '.csv'
            else:
                new_filename = cma + ' - ' + '.csv'
            
            # Create the full paths for both the original and new filenames
            original_filepath = os.path.join(download_dir, downloaded_file)
            new_filepath = os.path.join(download_dir, new_filename)
            
            # Rename the file
            os.rename(original_filepath, new_filepath)
            
            # Wait for a short time to ensure the rename operation completes
            time.sleep(1)

            # Close the browser window
            driver.quit()

            dataframe = scrape_target.parser.parse(new_filepath, cma_code, scrape_target.download_directory + '_' + scrape_target.file_postfix, self.logger)
            if scrape_target.expected_columns != -1 and scrape_target.expected_columns != len(dataframe.columns):
                raise AssertionError(f"expected {scrape_target.expected_columns} columns for '{scrape_target.category_name}' scrape target but there were {len(dataframe.columns)}")

            dataframes.append(dataframe)
    
        self.logger.debug(f"obtained {dataframes} dataframes from cma {cma}: {cma_code}")
        self.logger.info(f"obtained {len(dataframes)} dataframes from cma {cma}: {cma_code}")
        return dataframes

    # given func lambda that starts a download, wait until it's finished downloading and then return the filepath
    def download_file(self, download_dir: str, func, *args, **kwargs) -> str:
        # delete any old unfinished downloads
        [f.unlink() for f in Path(download_dir).glob("*.crdownload")]

        func(*args, **kwargs)

        # Wait for the file to be fully downloaded by checking for incomplete downloads
        FILE_DOWNLOAD_MAX_WAIT_TIME = 10
        FILE_DOWNLOAD_CHECK_INTERVAL = 0.5
        num_checks = 0
        while True:
            files = os.listdir(download_dir)
            crdownload_files = [f for f in files if f.endswith('.crdownload')]
            if not crdownload_files:
                break
            if num_checks * FILE_DOWNLOAD_CHECK_INTERVAL >= FILE_DOWNLOAD_MAX_WAIT_TIME:
                raise ConnectionError("exceeded maximum wait time to download file")
            num_checks += 1
            time.sleep(FILE_DOWNLOAD_CHECK_INTERVAL)
        
        # Get the list of files in the download directory
        files = os.listdir(download_dir)
        
        # Filter out directories, if any
        files = [file for file in files if os.path.isfile(os.path.join(download_dir, file))]
        
        # Sort files based on modification time (newest first)
        sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
        
        # Assume at least one file is present
        return sorted_files[0]
    
    def select_download(self, driver: any):
        # Wait for the "Export" button to be clickable
        export_button_xpath = '//a[@id="exportTableLink" and contains(@class, "button secondary")]'
        export_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, export_button_xpath)))
        
        # Click on the "Export" button
        export_button.click()
        
        # Wait for the "Export to Spreadsheet (CSV)" option to be clickable
        export_csv_xpath = '//a[@data-export-type="csv"]'
        export_csv_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, export_csv_xpath)))

        # download the file
        export_csv_option.click()

    def merge_dataframes(self, dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        merged = dataframes[0]
        for dataframe in dataframes[1:]:
            merged = pd.merge(merged, dataframe, on=['year', 'cma_code'])

        merged['month'] = merged['month'].astype(str)
        merged['year'] = merged['year'].astype(np.int64)
        merged.sort_values(by=['cma_code', 'year'], inplace=True)
        return merged

    # to handle network issues with selenium and the CHMC portal
    def retry_func(self, func, *args, **kwargs):
        NUM_ATTEMPTS = 5
        for attempt in range(NUM_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < NUM_ATTEMPTS - 1:
                    self.logger.warning(f"Attempt {attempt + 1} failed with error: {e}")
                else:
                    self.logger.error("Max retries reached. Raising exception.")
                    raise e

# ITEMS TO FIX
# that 'list index out of range' error that inconsistently pops up