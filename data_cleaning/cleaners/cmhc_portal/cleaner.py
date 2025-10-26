from enum import StrEnum
import io
import os
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

class Cleaner(BaseCleaner):
    CMHC_CMA_LIST = {
	"St. John's": "1640/3/St.%20John's",
	'Halifax': '0580/3/Halifax',
	'Ottawa': '1265/3/Ottawa',
	'Québec': '1400/3/Québec',
	'Sherbrooke': '1800/3/Sherbrooke',
	'Trois-Rivières': '2320/3/Trois-Rivières',
	'Montréal': '1060/3/Montréal',
    'Saguenay': '0180/3/Saguenay',
    'Drummondville': '0280/3/Drummondville',
	'Oshawa': '1250/3/Oshawa',
	'Toronto': '2270/3/Toronto',
	'Hamilton': '0610/3/Hamilton',
	'St. Catharines-Niagara': '1160/3/St.%20Catharines%20-%20Niagara',
	'Kitchener-Cambridge-Waterloo': '0850/3/Kitchener%20-%20Cambridge%20-%20Waterloo',
	'Guelph': '0460/3/Guelph',
	'London': '0950/3/London',
	'Windsor': '2640/3/Windsor',
	'Greater Sudbury': '2000/3/Greater%20Sudbury%20%2F%20Grand%20Sudbury',
    'Barrie': '0120/3/Barrie',
    'Kingston': '0700/3/Kingston',
    'Brantford': '0125/3/Brantford',
    'Peterborough': '1320/3/Peterborough',
    'Thunder Bay': '2240/3/Thunder Bay',
    'Belleville-Quinte West': '0122/3/Belleville - Quinte West',
	'Winnipeg': '2680/3/Winnipeg',
	'Regina': '1490/3/Regina',
	'Saskatoon': '1700/3/Saskatoon',
	'Calgary': '0140/3/Calgary',
	'Edmonton': '0340/3/Edmonton',
    'Red Deer': '1420/3/Red Deer',
    'Lethbridge': '0870/3/Lethbridge',
	'Kelowna': '0670/3/Kelowna',
	'Vancouver': '2410/3/Vancouver',
	'Victoria': '2440/3/Victoria',
    'Charlottetown': '3300/3/Charlottetown',
    'Abbotsford - Mission': '0110/3/Abbotsford - Mission',
    'Nanaimo': '1100/3/Nanaimo',
    'Kamloops': '0650/3/Kamloops',
    'Chilliwack': '0210/3/Chilliwack',
	'Saint John': '1600/3/Saint%20John',
	'Fredericton': '0370/3/Fredericton',
	'Moncton': '1040/3/Moncton'
	}

    class CategoryHead(StrEnum):
        HOUSING_STOCK = 'Population, Households and Housing Stock'
        NEW_CONSTRUCTION = 'New Housing Construction'
        PRIMARY_RENTAL_MARKET = 'Primary Rental MARKET'
        SECONDARY_RENTAL_MARKET = 'Secondary Rental Market'


    SCRAPE_TARGETS = [
        (CategoryHead.HOUSING_STOCK, 'Age of Primary Household Maintainer', 'household', 'age'),
        (CategoryHead.HOUSING_STOCK, 'Mobility of Primary Household Maintainer', 'household', 'mobility'),
        (CategoryHead.HOUSING_STOCK, 'Household Type', 'household', 'type'),
        (CategoryHead.HOUSING_STOCK, 'Household Size', 'household', 'size'),
        (CategoryHead.HOUSING_STOCK, 'Immigrant Households', 'household', 'immigrant'),
        (CategoryHead.HOUSING_STOCK, 'Households with Seniors', 'household', 'senior'),
        (CategoryHead.HOUSING_STOCK, 'Households with Children Under 18', 'household', 'children'),
        (CategoryHead.HOUSING_STOCK, 'Activity Limitations', 'household', 'activity-limits'),
        (CategoryHead.HOUSING_STOCK, 'Aboriginal Households', 'household', 'aboriginal'),
        (CategoryHead.HOUSING_STOCK, 'Shelter Costs', 'shelter', ''),
        (CategoryHead.HOUSING_STOCK, 'Mortgages', 'household', 'mortgage'),
        (CategoryHead.HOUSING_STOCK, 'Household Income', 'household', 'income'),
        (CategoryHead.HOUSING_STOCK, 'Condominiums', 'household', 'condominium'),
        (CategoryHead.HOUSING_STOCK, 'Housing Suitability', 'household', 'suitability'),
        (CategoryHead.HOUSING_STOCK, 'Value of Owner-occupied Dwellings ($)', 'household', 'value'),
        (CategoryHead.HOUSING_STOCK, 'Period of Construction and Condition of Dwelling', 'condition', '')
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
        for category_head, category_name, download_directory, file_postfix in self.SCRAPE_TARGETS:
            dataframe = self.scrape_category(category_head, category_name, download_directory, file_postfix)
            dataframes.append(dataframe)
        
        self.logger.debug(f"obtained {dataframes} from category {category_name}")
        self.logger.info(f"obtained {len(dataframes)} dataframes in total")

        merged_dataframes = self.merge_dataframes(dataframes)

        if format == 'dataframe':
            return merged_dataframes
        else:
            return merged_dataframes.to_numpy()


    def clean_data(self, raw_data: Union[pd.DataFrame, np.ndarray]) -> Union[pd.DataFrame, np.ndarray]:
        return raw_data # temporary

    def scrape_category(self, category_head:str, category_name: str, download_directory: str, file_postfix: str) -> pd.DataFrame:
        dataframes = []
        for cma, cma_code in self.CMHC_CMA_LIST.items():
            dataframes_for_cma = self.retry_func(self.scrape_cma,
                cma,
                cma_code,
                category_head,
                category_name,
                'dwelling',
                [],
                True,
                download_directory,
                file_postfix)
            dataframes.extend(dataframes_for_cma)
        
        self.logger.debug(f"obtained {dataframes} from category {category_name}")
        self.logger.info(f"obtained {len(dataframes)} dataframes from category {category_name}")
        return pd.concat(dataframes)

    def scrape_cma(self, cma: str, cma_code: str, category_head: str, category_name: str, sub_cat_type: str, sub_categories: list[str], historic: bool, download_directory: str, file_postfix: str) -> list[pd.DataFrame]:
        download_dir = os.path.join(os.getcwd(), 'raw', download_directory)


        # check if we've already scraped this data
        if file_postfix != '':
            existing_filename = cma + ' - ' + ' - ' + file_postfix + '.csv'
        else:
            existing_filename = cma + ' - ' + '.csv'
        existing_filename = os.path.join(download_dir, existing_filename)
        if os.path.exists(existing_filename):
            self.logger.info(f"using cached '{existing_filename}'")
            return [self.read_chmc_portal_csv(existing_filename, cma_code, category_name)]
        

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
        dropdown_xpath = '//a[@class="subsection-link" and text()="' + category_head + '"]'
        dropdown = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
        
        # Click on the dropdown
        dropdown.click()
        
        # Wait for metric link to be clickable
        link_xpath = '//a[text()="' + category_name + '"]'
        #link_xpath = "//a[text()='Average Rent ($)'][contains(@href, 'categoryLevel2=Rental%20Condominium%20Apartments')]"
        link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, link_xpath)))
        
        # Click on the metric link
        link.click()
        
        # Wait for the "Historical Time Periods" link to be clickable
        if historic:
            historical_link_xpath = '//a[text()="Historical Time Periods"]'
            historical_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, historical_link_xpath)))
            
            # Click on the "Historical Time Periods" link
            historical_link.click()
    
            # Pause for five seconds
            time.sleep(5)
            
        dataframes = []
        # Loop through sub-categories
        if len(sub_categories) > 0:
            for cat in sub_categories:
            
                # Wait for the dropdown to be clickable
                if sub_cat_type == 'dimension':
                    dropdown_xpath = '//a[@id="filterBydimension-18Link" and contains(@class, "menu-link")]'
                elif sub_cat_type == 'dwelling':
                    dropdown_xpath = '//a[@id="filterBydwelling_type_desc_enLink" and contains(@class, "menu-link")]'
                dropdown = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
                
                # Click on the dropdown
                dropdown.click()
                
                # Wait for the sub-category option to be clickable
                if sub_cat_type == 'dimension':
                    dropdown_xpath = '//a[@data-key="dimension-18" and @data-value="' + cat + '"]'
                elif sub_cat_type == 'dwelling':
                    dropdown_xpath = '//a[@data-key="dwelling_type_desc_en" and @data-value="' + cat + '"]'
                subcat_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, subcat_option_xpath)))
                
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
                if file_postfix != '':
                    new_filename = cma + ' - ' + cat.replace("/", "or") + ' - ' + file_postfix + '.csv'
                else:
                    new_filename = cma + ' - ' + cat.replace("/", "or") + '.csv'
                
                # Create the full paths for both the original and new filenames
                original_filepath = os.path.join(download_dir, most_recent_filename)
                new_filepath = os.path.join(download_dir, new_filename)
                
                # Rename the file
                os.rename(original_filepath, new_filepath)
                
                # Wait for a short time to ensure the rename operation completes
                time.sleep(1)

                dataframes.append(self.read_chmc_portal_csv(new_filepath, cma_code, category_name + ' - ' + cat))
                
            # Close the browser window
            driver.quit()
    
        # Proceed if no subcategories are present
        else:
    
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
            if file_postfix != '':
                new_filename = cma + ' - ' + ' - ' + file_postfix + '.csv'
            else:
                new_filename = cma + ' - ' + '.csv'
            
            # Create the full paths for both the original and new filenames
            original_filepath = os.path.join(download_dir, most_recent_filename)
            new_filepath = os.path.join(download_dir, new_filename)
            
            # Rename the file
            os.rename(original_filepath, new_filepath)
            
            # Wait for a short time to ensure the rename operation completes
            time.sleep(1)

            # Close the browser window
            driver.quit()

            dataframes.append(self.read_chmc_portal_csv(new_filepath, cma_code, category_name))
        
        self.logger.debug(f"obtained {dataframes} dataframes from cma {cma}: {cma_code}")
        self.logger.info(f"obtained {len(dataframes)} dataframes from cma {cma}: {cma_code}")
        return dataframes
    
    # files downloaded from the portal have non-standard csv formatting
    def read_chmc_portal_csv(self, filepath: str, cma_code: str, col_prefix: str) -> pd.DataFrame:
        with open(filepath, 'r', errors='replace') as file:
            lines = file.readlines()

            # remove first 2 lines, and then all the lines after the empty line
            lines = lines[2:]
            for i, line in enumerate(lines):
                if line == '\n':
                    lines = lines[:i]
            
            df = pd.read_csv(io.StringIO(''.join(lines)), thousands=',')
            df = df.iloc[:, :-1] # excess empty column

            def convert_to_numeric(cell) -> Union[np.int64, float]:
                try:
                    if isinstance(cell, str):
                        cell = cell.replace(',', '').replace(' ', '').strip()
                    cell = np.int64(cell)
                    if cell == 0:
                        self.logger.warning(f"setting zero in {filepath} as nan")
                        return np.nan    
                    return cell
                except:
                    self.logger.warning(f"could not process cell value '{cell}' in {filepath}, setting as nan")

                    return np.nan
            df = df.map(convert_to_numeric)

            df = df.rename(columns={df.columns[0]: "year"}) # year column missing a name
            df.insert(loc=0, column='cma_code', value=cma_code)
            df.columns = list(df.columns[:2]) + [col_prefix + '  ' + col for col in df.columns[2:]] # prefix all columns except year and cma_code
            df = df.rename(columns=lambda col: re.sub(r'[^a-zA-Z0-9]', '_', col)) # replace special characters with underscores in column names
            return df

    def merge_dataframes(self, dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        merged = dataframes[0]
        for dataframe in dataframes[1:]:
            merged = pd.merge(merged, dataframe, on=['year', 'cma_code'])

        merged.sort_values(by=['cma_code', 'year'], inplace=True)
        return merged

    # to handle network issues with selenium and the CHMC portal
    def retry_func(self, func, *args, **kwargs):
        NUM_ATTEMPTS = 3
        for attempt in range(NUM_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < NUM_ATTEMPTS - 1:
                    self.logger.warning(f"Attempt {attempt + 1} failed with error: {e}")
                else:
                    self.logger.error("Max retries reached. Raising exception.")
                    raise e