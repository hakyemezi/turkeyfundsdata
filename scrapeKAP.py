import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)

# KAP was rebuilt and the old markup this script relied on is gone. The
# "comp-cell _04 vtable" and "w-clearfix w-inline-block a-table-row" class
# names no longer match anything. The pages now render real <table> elements,
# so the tables are read directly instead of walking anchor tags by class.
BASE_URL = "https://www.kap.org.tr/tr/YatirimFonlari/"
ITEM_URL = "https://www.kap.org.tr/tr/fonlarTumKalemler/"

# The site rejects requests without a browser user agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "tr,en;q=0.8",
}

# The item pages are several megabytes each, so requests are spaced out
REQUEST_PAUSE = 0.5


def get_rows(url):
    """
    Downloads a KAP page and returns the text of every table body row on it.

    Parameters:
    ------------
    url : str
        The KAP page to read.

    Returns:
    --------
    list
        A list of rows, where each row is a list of the cell texts.

    Notes:
    ------
    - Header rows live in <thead> and are left out, so only data rows are returned.
    - Cell text is stripped, which is enough because the values are short.
    """
    time.sleep(REQUEST_PAUSE)

    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()  # Raise an error for bad status codes

    soup = BeautifulSoup(response.text, 'html.parser')

    rows = []
    for tr in soup.select("table tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    return rows


def fon_data(url_end):
    """
    Retrieves fund data from the KAP website based on the specified fund type.

    Parameters:
    ------------
    url_end : str
        The specific endpoint for the type of fund. Example: 'YF', 'EYF', 'OKS', etc.

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing the code, title, and founder of the funds retrieved from the KAP website.

    Notes:
    ------
    - Every umbrella fund gets its own table on the page, and each row of those
      tables holds the fund code, the fund name and the founder.
    - Rows that do not have all three cells are skipped.
    """
    url = BASE_URL + url_end

    rows = get_rows(url)

    data = [row[:3] for row in rows if len(row) >= 3]

    df = pd.DataFrame(data, columns=["CODE", "TITLE", "FOUNDER"])

    return df


def get_fund_detail(url_name):
    """
    Retrieves specific fund details from the KAP website.

    Parameters:
    ------------
    url_name : str
        The URL for the specific fund detail page.

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing the extracted details from the specified fund page.

    Notes:
    ------
    - These pages hold one table with two columns, the fund name and the value
      of the item being listed.
    """
    rows = get_rows(url_name)

    data = [row[:2] for row in rows if len(row) >= 2]

    df = pd.DataFrame(data, columns=['Column1', 'Column2'])

    return df


def get_fund_detail2(url_name):
    """
    Retrieves additional specific fund details from the KAP website, including multiple columns.

    Parameters:
    ------------
    url_name : str
        The URL for the specific fund detail page.

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing detailed information about the funds, with the
        fund name and the value of the listed item.

    Notes:
    ------
    - This function is similar to `get_fund_detail` but reads the pages that
      carry an extra "İhraç Sıra Numarası" column between the fund name and the
      value, so the middle column is dropped.
    - A fund with more than one issue spans several rows, and only its first
      row repeats the fund name. The follow up rows have two cells instead of
      three, so they take the name of the row above them.
    """
    rows = get_rows(url_name)

    data = []
    title = None
    for row in rows:
        if len(row) >= 3:
            title = row[0]
            data.append([title, row[2]])
        elif len(row) == 2 and title is not None:
            data.append([title, row[1]])

    df = pd.DataFrame(data, columns=['Column1', 'Column2'])

    return df


def get_all():
    """
    Retrieves and merges fund data from multiple categories on the KAP website.

    Returns:
    --------
    pd.DataFrame
        A merged DataFrame containing information on various fund categories, including code, title, type, and other details.

    Notes:
    ------
    - The function collects data from different fund types and combines it into a single DataFrame.
    - Various additional details such as ISIN, manager, risk value, and more are fetched and merged into the final DataFrame.
    - The fund title is used as the merge key, it matches across all of the pages.
    """
    url_ends = ['YF', 'EYF', 'OKS', 'BYF', 'GMF', 'GSF', 'YYF', 'VFF', 'KFF', 'PFF']

    # Initialize an empty DataFrame to hold all data
    data1 = pd.DataFrame()

    # Iterate through each URL end, collect data, and append to all_data DataFrame
    for url_end in url_ends:
        df = fon_data(url_end)
        df["KIND"] = url_end
        data1 = pd.concat([data1, df], ignore_index=True)

    data1['REPRESENTATIVE'] = pd.Series(np.nan, dtype=str)
    data1.loc[data1['KIND'] == 'YYF', 'REPRESENTATIVE'] = data1['FOUNDER']
    data1.drop('FOUNDER', axis=1, inplace=True)

    data2_founder1 = get_fund_detail(ITEM_URL + "kpy81_acc1_kurucu_unvan")
    data2_founder1.columns = ["TITLE", "FOUNDER"]
    data2_founder2 = get_fund_detail(ITEM_URL + "kpy81_acc1_kurucu_unvan_2")
    data2_founder2.columns = ["TITLE", "FOUNDER"]
    data2_founder = pd.concat([data2_founder1, data2_founder2], ignore_index=True)

    data2_pmc1 = get_fund_detail(ITEM_URL + "kpy81_acc1_portfoy_ticaret_unvan")
    data2_pmc1.columns = ["TITLE", "MANAGER"]
    data2_pmc2 = get_fund_detail2(ITEM_URL + "kpy81_acc1_portfoy_yon_kurulus")
    data2_pmc2.columns = ["TITLE", "MANAGER"]
    data2_pmc3 = get_fund_detail(ITEM_URL + "kpy81_acc1_yonetici_unvan")
    data2_pmc3.columns = ["TITLE", "MANAGER"]
    data2_pmc = pd.concat([data2_pmc1, data2_pmc2, data2_pmc3], ignore_index=True)

    data2_isin = get_fund_detail(ITEM_URL + "kpy81_acc1_ISIN")
    data2_isin.columns = ["TITLE", "ISIN"]

    data2_rd = get_fund_detail(ITEM_URL + "kpy81_acc1_fonun_risk_degeri")
    data2_rd.columns = ["TITLE", "RD"]

    data2_type = get_fund_detail(ITEM_URL + "kpy81_acc1_fon_tur")
    data2_type.columns = ["TITLE", "TYPE"]

    data2_ini = get_fund_detail(ITEM_URL + "kpy81_acc1_fon_icerigi")
    data2_ini.columns = ["TITLE", "INTEREST"]

    data2_auditor = get_fund_detail(ITEM_URL + "kpy81_acc1_bdk")
    data2_auditor.columns = ["TITLE", "AUDITOR"]

    data2_ipo1 = get_fund_detail(ITEM_URL + "kpy81_acc1_halka_arz1")
    data2_ipo1.columns = ["TITLE", "IPO_DATE"]
    data2_ipo2 = get_fund_detail2(ITEM_URL + "kpy81_acc1_halka_arz2")
    data2_ipo2.columns = ["TITLE", "IPO_DATE"]
    data2_ipo = pd.concat([data2_ipo1, data2_ipo2], ignore_index=True)
    data2_ipo['IPO_DATE'] = data2_ipo['IPO_DATE'].apply(lambda x: np.nan if (x is None or '-' in x) else x)

    # A fund can be listed more than once on the item pages, and duplicates
    # would multiply rows on every merge, so they are dropped up front
    dfs = [data1, data2_founder, data2_isin, data2_rd, data2_pmc, data2_type, data2_ini, data2_auditor, data2_ipo]
    dfs = [dfs[0]] + [df.drop_duplicates(subset='TITLE') for df in dfs[1:]]

    # Merge all DataFrames on the 'TITLE' column
    funds = dfs[0]

    for df in dfs[1:]:
        funds = pd.merge(funds, df, on='TITLE', how='outer')

    funds['IPO_DATE'] = funds['IPO_DATE'].replace(' ', None)
    funds['IPO_DATE'] = pd.to_datetime(funds['IPO_DATE'], format='%d/%m/%Y', errors='coerce')

    return funds


##examples:
# funds = get_all()

# funds.info()
