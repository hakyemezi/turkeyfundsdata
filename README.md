# Turkish Fund Data Scripts
This repository contains two Python scripts that retrieve and process data related to investment funds in Turkey. These scripts are designed to fetch fund prices, asset distributions, and general fund information from publicly available sources.
## Scripts
### tefas.py
**Purpose:** Retrieves fund prices and asset distributions from [TEFAS (Turkish Electronic Fund Trading Platform)](https://www.tefas.gov.tr/)

**Description:** The script fetches and merges data related to fund prices and asset allocations based on user-specified parameters such as fund type, start date, and end date.
It supports retrieving data for specific date ranges and allows for easy analysis and visualization of the fund's historical performance.

**Usage Example:**
```python
fund_df = get_fund_data_for_years(0.5, "YAT")
print(fund_df)
```
This retrieves and prints six months of data for the fund type "YAT".

### scrapeKAP.py
**Purpose:** Scrapes general information about investment funds from [KAP (Public Disclosure Platform)](https://www.kap.org.tr/)

**Description:** The script fetches information such as the fund’s code, title, founder, manager, ISIN, risk level, and IPO date.
The data is retrieved by scraping multiple pages of the KAP website, consolidating details into a structured format suitable for further analysis.

**Usage Example:**
```python
funds = get_all()
print(funds.head())
```
This retrieves and prints the first few rows of a DataFrame containing comprehensive details about various funds listed on KAP.

## Setup and Installation
**Clone the Repository:**
```bash
git clone https://github.com/hakyemezi/turkeyfundsdata.git
cd turkish-fund-data
```
**Install Required Packages: Ensure you have the necessary Python packages installed:**
```bash
pip install -r requirements.txt
```
**Run the Scripts:** You can run each script directly in your Python environment. Ensure you have a working internet connection as the scripts fetch data from online sources.

## Notes
**Data Source Reliability:** The data is sourced directly from the official websites, ensuring accuracy and relevance. However, any changes in the website structure may require updates to the scripts.

**Customization:** The scripts can be customized to retrieve specific data points or to handle larger datasets by adjusting the parameters and modifying the code accordingly.

## Contributions
Contributions are welcome! If you find any issues or have ideas for enhancements, feel free to open an issue or submit a pull request.
