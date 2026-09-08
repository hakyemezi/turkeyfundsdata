import time
import requests
import pandas as pd
from datetime import datetime, timedelta

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 200)
pd.set_option('display.expand_frame_repr', False)
pd.options.display.float_format = '{:,.2f}'.format

# The old /api/DB/BindHistoryInfo and /api/DB/BindHistoryAllocation endpoints
# were removed and now answer 404 on both fonturkey.com.tr and tefas.gov.tr.
# These are the endpoints the site uses today. They take JSON instead of form
# data, want dates as YYYYMMDD, and return the rows under "resultList".
INFO_URL = "https://fonturkey.com.tr/api/funds/fonGnlBlgSiraliGetirDosya"
ALLOCATION_URL = "https://fonturkey.com.tr/api/funds/dagilimSiraliGetirDosya"

# The API answers 200 with an empty resultList instead of an error when a
# request covers too long a period, so requests have to stay inside one month.
MAX_CHUNK_DAYS = 30

# It also answers 200 with an empty resultList when requests arrive too fast,
# so every call waits a little and a suspicious empty answer is retried.
REQUEST_PAUSE = 2.0
RETRY_PAUSE = 15.0
MAX_RETRIES = 4

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://fonturkey.com.tr/",
}

# The new API returns camelCase names. These are mapped back to the column
# names the old version of this script produced, so existing code keeps working.
INFO_COLUMNS = {
    "tarih": "TARIH",
    "fonKodu": "FONKODU",
    "fonUnvan": "FONUNVAN",
    "fiyat": "FIYAT",
    "tedPaySayisi": "TEDPAYSAYISI",
    "kisiSayisi": "KISISAYISI",
    "portfoyBuyukluk": "PORTFOYBUYUKLUK",
    "borsaBultenFiyat": "BORSABULTENFIYAT",
}

ALLOCATION_KEY_COLUMNS = {
    "tarih": "TARIH",
    "fonKodu": "FONKODU",
    "fonUnvan": "FONUNVAN",
}


def post_json(url, body):
    """
    Sends one request to the fund API and returns the rows it answered with.

    Parameters:
    ------------
    url : str
        The API endpoint to post to.
    body : dict
        The JSON payload describing the fund type and date range.

    Returns:
    --------
    list
        The list of records under "resultList", or an empty list if the
        request kept failing.

    Notes:
    ------
    - The API answers 200 with an empty result both when it is being called too
      quickly and when it genuinely has no data, so an empty answer is retried
      a few times before it is accepted as real.
    - A non-200 answer is retried as well.
    """
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_PAUSE)
        try:
            response = requests.post(url, headers=HEADERS, json=body, timeout=60)
        except requests.RequestException as error:
            print(f"Request failed: {error}")
            time.sleep(RETRY_PAUSE)
            continue

        if response.status_code != 200:
            print(f"Request failed with status code {response.status_code}")
            time.sleep(RETRY_PAUSE)
            continue

        rows = response.json().get("resultList") or []
        if rows:
            return rows

        # Empty answer: back off and try again, it is usually throttling
        if attempt < MAX_RETRIES - 1:
            print(f"Empty answer for {body['basTarih']}-{body['bitTarih']}, retrying")
            time.sleep(RETRY_PAUSE)

    return []


def get_fund_data(fontip="EMK", sfontur="", fonkod="", fongrup="", bastarih="01.08.2026", bittarih="30.08.2026", fonturkod="", fonunvantip="", kurucukod="", dil="TR"):
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
        The start date in "DD.MM.YYYY" format.
    bittarih : str, optional
        The end date in "DD.MM.YYYY" format.
    fonturkod : str, optional
        The code of the fund type. Default is an empty string.
    fonunvantip : str, optional
        The type of fund title. Default is an empty string.
    kurucukod : str, optional
        The code of the founder. Default is an empty string.
    dil : str, optional
        The language of the fund titles, "TR" or "en". Default is "TR".

    Returns:
    --------
    pd.DataFrame
        Returns a DataFrame containing merged fund information and allocation data.

    Notes:
    ------
    - The date range must stay inside one month. Use get_fund_data_for_years for
      longer periods, it splits the period into chunks the API accepts.
    - Data is fetched from the API for the specified date range.
    - JSON data is normalized and converted into a DataFrame.
    - Missing data is set to `NaN` and then filled with zero.
    - Numerical columns in the DataFrame are properly formatted.
    """
    start = datetime.strptime(bastarih, "%d.%m.%Y")
    end = datetime.strptime(bittarih, "%d.%m.%Y")

    if (end - start).days > MAX_CHUNK_DAYS:
        print(f"Date range is longer than {MAX_CHUNK_DAYS} days, the API will return nothing. Use get_fund_data_for_years instead.")
        return None

    # The API wants missing parameters as null rather than as an empty string
    body = {
        "dil": dil,
        "fonTipi": fontip or None,
        "sfonTurKod": sfontur or None,
        "fonKod": fonkod or None,
        "fonGrup": fongrup or None,
        "basTarih": start.strftime("%Y%m%d"),
        "bitTarih": end.strftime("%Y%m%d"),
        "fonTurKod": fonturkod or None,
        "fonUnvanTip": fonunvantip or None,
        "kurucuKod": kurucukod or None,
        "fonTurAciklama": None,
    }

    info_rows = post_json(INFO_URL, body)
    if not info_rows:
        print(f"No fund information returned for {bastarih} - {bittarih}")
        return None

    df_info = pd.json_normalize(info_rows).rename(columns=INFO_COLUMNS)
    df_info['TARIH'] = pd.to_datetime(df_info['TARIH'])

    # Some fields arrive as null or as "-", so they are coerced to numbers
    # first and only then filled, which keeps the columns out of object dtype
    value_columns = [column for column in df_info.columns if column not in ['TARIH', 'FONKODU', 'FONUNVAN']]
    df_info[value_columns] = df_info[value_columns].apply(pd.to_numeric, errors='coerce').fillna(0).astype('float64')
    df_info['KISISAYISI'] = df_info['KISISAYISI'].astype(int)

    allocation_rows = post_json(ALLOCATION_URL, body)
    if not allocation_rows:
        print(f"No allocation data returned for {bastarih} - {bittarih}")
        return None

    df_allocation = pd.json_normalize(allocation_rows).rename(columns=ALLOCATION_KEY_COLUMNS)
    df_allocation['TARIH'] = pd.to_datetime(df_allocation['TARIH'])
    if 'bilFiyat' in df_allocation.columns:
        df_allocation = df_allocation.drop(columns=['bilFiyat'])

    # The allocation endpoint returns short asset codes such as bb, hs, kh.
    # They are upper cased so that they read like the other columns.
    allocation_columns = [column for column in df_allocation.columns if column not in ['TARIH', 'FONKODU', 'FONUNVAN']]
    df_allocation[allocation_columns] = df_allocation[allocation_columns].apply(pd.to_numeric, errors='coerce').fillna(0).astype('float64')
    df_allocation = df_allocation.rename(columns={column: column.upper() for column in allocation_columns})

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
    - Each request covers a maximum of 30 days, which is what the API accepts.
    - Chunks that come back empty are skipped so that one bad window does not
      lose the whole period.
    - The results from all chunked requests are concatenated and returned as a single DataFrame.
    """
    if years > 5:
        years = 5

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)

    dataframes = []
    chunk_start = start_date
    while chunk_start < end_date:
        chunk_end = chunk_start + timedelta(days=MAX_CHUNK_DAYS)
        if chunk_end > end_date:
            chunk_end = end_date

        print(f"Fetching {chunk_start.strftime('%d.%m.%Y')} - {chunk_end.strftime('%d.%m.%Y')}")
        fund_df = get_fund_data(fontip=fontip,
                                bastarih=chunk_start.strftime('%d.%m.%Y'),
                                bittarih=chunk_end.strftime('%d.%m.%Y'))
        if fund_df is not None:
            dataframes.append(fund_df)

        chunk_start = chunk_end + timedelta(days=1)

    if not dataframes:
        print("No data could be retrieved for the requested period")
        return None

    final_df = pd.concat(dataframes, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=['TARIH', 'FONKODU'], ignore_index=True)
    return final_df


##examples:
# fund_df = get_fund_data_for_years(0.5, "YAT")

# fund_df = get_fund_data(fontip="YAT", bastarih="01.08.2026", bittarih="30.08.2026")
