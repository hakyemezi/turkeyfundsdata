import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 200)
pd.set_option('display.expand_frame_repr', False)
pd.options.display.float_format = '{:,.2f}'.format

def get_fund_data(fontip="EMK", sfontur="", fonkod="", fongrup="", bastarih="29.02.2024", bittarih="01.03.2024", fonturkod="", fonunvantip=""):
    """
    Fetches and merges fund data based on specified parameters.

    Parameters:
    ------------
    fontip : str, optional
        The type of fund. Default is "EMK".
    sfontur : str, optional
        Subtype of the fund. Default is an empty string.
    fonkod : str, optional
        The code of the fund. Default is an empty string.
    fongrup : str, optional
        The group of the fund. Default is an empty string.
    bastarih : str, optional
        The start date in "DD.MM.YYYY" format. Default is "29.02.2024".
    bittarih : str, optional
        The end date in "DD.MM.YYYY" format. Default is "01.03.2024".
    fonturkod : str, optional
        The code of the fund type. Default is an empty string.
    fonunvantip : str, optional
        The type of fund title. Default is an empty string.

    Returns:
    --------
    pd.DataFrame
        Returns a DataFrame containing merged fund information and allocation data.

    Notes:
    ------
    - Data is fetched from the API for the specified date range.
    - JSON data is normalized and converted into a DataFrame.
    - Missing data is set to `NaN` and then filled with zero.
    - Numerical columns in the DataFrame are properly formatted.
    """
    body = {
        "fontip": fontip,
        "sfontur": sfontur,
        "fonkod": fonkod,
        "fongrup": fongrup,
        "bastarih": bastarih,
        "bittarih": bittarih,
        "fonturkod": fonturkod,
        "fonunvantip": fonunvantip,
    }

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://fonturkey.com.tr/TarihselVeriler.aspx",
    }

    info = "https://fonturkey.com.tr/api/DB/BindHistoryInfo"

    response_info = requests.post(info, headers=headers, data=body)
    if response_info.status_code != 200:
        print(f"Request failed with status code {response_info.status_code}")
        return None
    df_info = pd.json_normalize(response_info.json()["data"])
    df_info['TARIH'] = pd.to_numeric(df_info['TARIH'], errors='coerce')
    df_info['TARIH'] = pd.to_datetime(df_info['TARIH'], unit='ms').dt.strftime('%Y-%m-%d')
    df_info['TARIH'] = pd.to_datetime(df_info['TARIH'])
    df_info[['TARIH', 'FONKODU', 'FONUNVAN']] = df_info[['TARIH', 'FONKODU', 'FONUNVAN']].astype({'TARIH': 'datetime64[ns]', 'FONKODU': 'object', 'FONUNVAN': 'object'})
    df_info['BORSABULTENFIYAT'] = df_info['BORSABULTENFIYAT'].replace('-', np.nan)
    df_info = df_info.fillna(0)
    df_info.iloc[:, 3:] = df_info.iloc[:, 3:].astype('float64')
    df_info['KISISAYISI'] = df_info['KISISAYISI'].astype(int)

    allocation = "https://fonturkey.com.tr/api/DB/BindHistoryAllocation"

    response_allocation = requests.post(allocation, headers=headers, data=body)
    df_allocation = pd.json_normalize(response_allocation.json()["data"])
    df_allocation['TARIH'] = pd.to_numeric(df_allocation['TARIH'], errors='coerce')
    df_allocation['TARIH'] = pd.to_datetime(df_allocation['TARIH'], unit='ms').dt.strftime('%Y-%m-%d')
    df_allocation['TARIH'] = pd.to_datetime(df_allocation['TARIH'])
    df_allocation[['TARIH', 'FONKODU', 'FONUNVAN']] = df_allocation[['TARIH', 'FONKODU', 'FONUNVAN']].astype({'TARIH': 'datetime64[ns]', 'FONKODU': 'object', 'FONUNVAN': 'object'})
    if 'BilFiyat' in df_allocation.columns:
        df_allocation = df_allocation.drop(columns=['BilFiyat'])
    df_allocation = df_allocation.fillna(0)
    df_allocation.iloc[:, 3:] = df_allocation.iloc[:, 3:].astype('float64')

    df_merged = pd.merge(df_info, df_allocation, on=['TARIH', 'FONKODU', 'FONUNVAN'])
    df_merged.insert(loc=df_merged.columns.get_loc('FIYAT') + 1, column='FIYAT_6DEC', value=df_merged["FIYAT"])
    df_merged["FIYAT_6DEC"] = df_merged["FIYAT_6DEC"].map(lambda x: "{:.6f}".format(x))
    df_merged["TEDPAYSAYISI"] = df_merged["TEDPAYSAYISI"].map(lambda x: "{:.6f}".format(x))
    return df_merged

def get_fund_data_for_years(years, fontip):
    """
    Fetches and combines fund data over a specified number of years.

    Parameters:
    ------------
    years : float
        Specifies how many years' worth of data to retrieve.
        A maximum of 5 years can be specified. Example: 0.5 (6 months of data), 1 (1 year of data).
    fontip : str
        The type of the fund. Example: "YAT"

    Returns:
    --------
    pd.DataFrame
        Returns a final DataFrame that merges all fund data retrieved over the specified period.

    Notes:
    ------
    - API requests are made in chunks to cover the specified period.
    - Each request covers a maximum of 60 days of data.
    - The results from all chunked requests are concatenated and returned as a single DataFrame.
    """
    if years > 5:
        years = 5
    years = years
    max_days = timedelta(days=365 * years)
    end_date = datetime.now()
    start_date = end_date - max_days
    date1 = end_date
    date2 = start_date

    dataframes = []
    while (date1 - start_date).days > 60:
        date2 = date1 - timedelta(days=60)
        fund_df = get_fund_data(fontip=fontip, bastarih=date2.strftime('%d.%m.%Y'),
                                bittarih=date1.strftime('%d.%m.%Y'))
        date1 = date2 - timedelta(days=1)
        dataframes.append(fund_df)
    else:
        fund_df = get_fund_data(fontip=fontip, bastarih=start_date.strftime('%d.%m.%Y'),
                                bittarih=date1.strftime('%d.%m.%Y'))
        dataframes.append(fund_df)

    final_df = pd.concat(dataframes, ignore_index=True)
    return final_df


##examples:
fund_df = get_fund_data_for_years(0.5,"YAT")

fund_df = get_fund_data(fontip="YAT", bastarih="30.06.2024", bittarih="29.08.2024")
