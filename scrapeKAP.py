import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)

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
    - The function sends a GET request to the KAP website and parses the HTML content to extract the relevant fund data.
    - The extracted data includes fund code, title, and founder, organized into a DataFrame.
    """
    base_url = "https://www.kap.org.tr/tr/YatirimFonlari/"
    url = base_url + url_end

    # Send a GET request to the URL
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all href tags
    href_tags = soup.find_all('a')

    # Filter href tags based on parent element's class name
    desired_classes = ["comp-cell _04 vtable", "comp-cell _08 vtable", "comp-cell _009 vtable"]
    href_list = []

    for tag in href_tags:
        parent_class = tag.find_parent().get('class', [])
        parent_class_name = " ".join(parent_class)  # Convert list of class names to single string
        if parent_class_name in desired_classes:
            href_list.append(tag.get_text(strip=True))

    # Create a DataFrame to store the href values
    data = {'Column1': [], 'Column2': [], 'Column3': []}

    for i, href in enumerate(href_list):
        remainder = (i + 1) % 3
        if remainder == 1:
            data['Column1'].append(href)
            data['Column2'].append('')
            data['Column3'].append('')
        elif remainder == 2:
            data['Column2'][-1] = href
        elif remainder == 0:
            data['Column3'][-1] = href

    df = pd.DataFrame(data)
    df.columns = ["CODE", "TITLE", "FOUNDER"]

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
    - This function sends a GET request to a specific KAP webpage and extracts relevant details using BeautifulSoup.
    - The extracted data is organized into a DataFrame, with two columns representing different details of the fund.
    """
    # Send a GET request to the URL
    response = requests.get(url_name)
    response.raise_for_status()  # Raise an error for bad status codes

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract text from each anchor tag and split it into parts
    data = []

    # Find all anchor tags with the specified class
    anchor_tags = soup.find_all('a', class_=lambda x: x and ('w-clearfix w-inline-block a-table-row' in x))
    for tag in anchor_tags:
        span_tag = tag.find('span')
        if span_tag:
            span_text = span_tag.get_text(strip=True)
            div_tags = tag.find_all('div', class_='comp-cell-row-div vtable infoColumn')
            if len(div_tags) >= 1:
                data.append([span_text, div_tags[0].get_text(strip=True)])

    # Create a DataFrame to store the extracted data
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
        A DataFrame containing detailed information about the funds, with multiple columns extracted from the webpage.

    Notes:
    ------
    - This function is similar to `get_fund_detail` but extracts more detailed information across multiple columns.
    - The first row is used as the header for the DataFrame, and empty strings are replaced with `NaN`.
    """
    # Send a GET request to the URL
    response = requests.get(url_name)
    response.raise_for_status()  # Raise an error for bad status codes

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract text from each anchor tag and split it into parts
    data = []

    # Find all anchor tags with the specified class
    anchor_tags = soup.find_all('a', class_=lambda x: x and ('w-clearfix w-inline-block a-table-row' in x))
    for tag in anchor_tags:
        span_tag = tag.find('span')
        row_data = []
        if span_tag:
            span_text = span_tag.get_text(strip=True)
            row_data.append(span_text)
        div_tags = tag.find_all('div', class_='comp-cell-row-div vtable infoColumn')
        for div_tag in div_tags:
            row_data.append(div_tag.get_text(strip=True))
        data.append(row_data)

    # Create a DataFrame to store the extracted data
    # Find the maximum length of row_data
    max_columns = max(len(row) for row in data)

    # Create column names dynamically
    columns = [f'Column{i}' for i in range(1, max_columns + 1)]

    # Create DataFrame
    df = pd.DataFrame(data, columns=columns)

    # Use the first row as the header
    df.columns = df.iloc[0]
    df = df[1:]

    # Replace empty strings with pd.NA and drop columns with all NaN values
    df = df.iloc[:, [0, 2]]

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

    data2_founder1 = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_kurucu_unvan")
    data2_founder1.columns = ["TITLE", "FOUNDER"]
    data2_founder2 = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_kurucu_unvan_2")
    data2_founder2.columns = ["TITLE", "FOUNDER"]
    data2_founder = pd.concat([data2_founder1, data2_founder2], ignore_index=True)
    data2_pmc1 = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_portfoy_ticaret_unvan")
    data2_pmc1.columns = ["TITLE", "MANAGER"]
    data2_pmc2 = get_fund_detail2("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_portfoy_yon_kurulus")
    data2_pmc2.columns = ["TITLE", "MANAGER"]
    data2_pmc3 = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_yonetici_unvan")
    data2_pmc3.columns = ["TITLE", "MANAGER"]
    data2_pmc = pd.concat([data2_pmc1, data2_pmc2, data2_pmc3], ignore_index=True)

    data2_isin = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_ISIN")
    data2_isin.columns = ["TITLE", "ISIN"]

    data2_rd = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_fonun_risk_degeri")
    data2_rd.columns = ["TITLE", "RD"]

    data2_type = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_fon_tur")
    data2_type.columns = ["TITLE", "TYPE"]

    data2_ini = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_fon_icerigi")
    data2_ini.columns = ["TITLE", "INTEREST"]

    data2_auditor = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_bdk")
    data2_auditor.columns = ["TITLE", "AUDITOR"]

    data2_ipo1 = get_fund_detail("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_halka_arz1")
    data2_ipo1.columns = ["TITLE", "IPO_DATE"]
    data2_ipo2 = get_fund_detail2("https://www.kap.org.tr/tr/fonlarTumKalemler/kpy81_acc1_halka_arz2")
    data2_ipo2.columns = ["TITLE", "IPO_DATE"]
    data2_ipo = pd.concat([data2_ipo1, data2_ipo2], ignore_index=True)
    data2_ipo['IPO_DATE'] = data2_ipo['IPO_DATE'].apply(lambda x: np.nan if (x is None or '-' in x) else x)

    dfs = [data1, data2_founder, data2_isin, data2_rd, data2_pmc, data2_type, data2_ini, data2_auditor, data2_ipo]

    # Merge all DataFrames on the 'TITLE' column
    funds = dfs[0]

    for df in dfs[1:]:
        funds = pd.merge(funds, df, on='TITLE', how='outer')

    funds['IPO_DATE'] = funds['IPO_DATE'].replace(' ', None)
    funds['IPO_DATE'] = pd.to_datetime(funds['IPO_DATE'], format='%d/%m/%Y', errors='coerce')

    return funds

funds = get_all()

funds.info()











