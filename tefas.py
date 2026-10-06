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


class FetchError(RuntimeError):
    """The endpoint failed; this is not a valid empty response."""


class IncompleteHistoryError(FetchError):
    """A requested history contains failed or unresolved empty windows."""


def post_json(url, body):
    """Retry transport, JSON/schema errors and empty responses.

    An all-empty sequence returns []; mixed errors/empty responses raise because
    absence cannot be established. Empty results still need coverage review.
    """
    errors = []
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_PAUSE)
        try:
            response = requests.post(url, headers=HEADERS, json=body, timeout=60)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("resultList"), list):
                raise ValueError("Expected a resultList array")
            rows = payload["resultList"]
            if not all(isinstance(row, dict) for row in rows):
                raise ValueError("Expected resultList records")
            if rows:
                return rows
        except (requests.RequestException, ValueError) as error:
            errors.append(str(error))
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_PAUSE)
    if errors:
        raise FetchError(f"Failed to fetch {url}: {errors[-1]}")
    return []


def _normalize_rows(rows, mapping):
    frame = pd.json_normalize(rows).rename(columns=mapping)
    required = ["TARIH", "FONKODU", "FONUNVAN"]
    if frame.empty:
        return pd.DataFrame(columns=required)
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")
    frame["TARIH"] = pd.to_datetime(frame["TARIH"], errors="raise").dt.normalize()
    if frame[required].isna().any().any():
        raise ValueError("Null fund identity/date in source")
    frame["FONKODU"] = frame["FONKODU"].astype(str).str.strip()
    if frame["FONKODU"].eq("").any():
        raise ValueError("Empty fund code in source")
    frame = frame.drop_duplicates()
    if frame.duplicated(["TARIH", "FONKODU"]).any():
        raise ValueError("Conflicting records for the same fund and date")
    for column in frame.columns.difference(required):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


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
    - Missing numeric data stays missing; numerical fields stay numeric.
    - Source coverage and unmatched keys are recorded in DataFrame.attrs.
    """
    start = datetime.strptime(bastarih, "%d.%m.%Y")
    end = datetime.strptime(bittarih, "%d.%m.%Y")

    if end < start or (end - start).days >= MAX_CHUNK_DAYS:
        raise ValueError(f"Use an ordered range of at most {MAX_CHUNK_DAYS} inclusive days")

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

    info = _normalize_rows(post_json(INFO_URL, body), INFO_COLUMNS)
    allocation = _normalize_rows(post_json(ALLOCATION_URL, body), ALLOCATION_KEY_COLUMNS)
    allocation = allocation.drop(columns=["bilFiyat"], errors="ignore")
    keys = ["TARIH", "FONKODU"]
    allocation = allocation.rename(columns={
        c: c.upper() for c in allocation.columns if c not in keys + ["FONUNVAN"]
    })
    merged = info.merge(allocation, on=keys, how="outer", suffixes=("", "_ALLOCATION"),
                        validate="one_to_one", indicator=True)
    title_mismatch = (merged["FONUNVAN"].notna() & merged["FONUNVAN_ALLOCATION"].notna()
                      & merged["FONUNVAN"].ne(merged["FONUNVAN_ALLOCATION"]))
    coverage = {
        "start": start.date().isoformat(), "end": end.date().isoformat(),
        "general_rows": len(info), "allocation_rows": len(allocation),
        "general_only": int(merged["_merge"].eq("left_only").sum()),
        "allocation_only": int(merged["_merge"].eq("right_only").sum()),
        "title_mismatches": int(title_mismatch.sum()),
        "unmatched_keys": merged.loc[merged["_merge"].ne("both"), keys]
            .assign(TARIH=lambda x: x["TARIH"].astype(str)).to_dict("records"),
    }
    coverage["status"] = ("empty" if merged.empty else
                          "partial" if coverage["general_only"] or coverage["allocation_only"]
                          else "ok")
    merged["FONUNVAN"] = merged["FONUNVAN"].combine_first(merged["FONUNVAN_ALLOCATION"])
    merged = merged.drop(columns=["FONUNVAN_ALLOCATION", "_merge"])
    # Preserve the historical display column without changing the numeric fields.
    if "FIYAT" in merged:
        merged["FIYAT_6DEC"] = merged["FIYAT"].map(
            lambda value: f"{value:.6f}" if pd.notna(value) else None)
    merged.attrs["coverage"] = coverage
    return merged


def get_fund_data_for_years(years, fontip, *, allow_partial=False, end_date=None):
    """Fetch up to five years, using 30 inclusive days per request.

    By default unresolved empty, partial or failed windows raise instead of
    silently returning incomplete history. Opt in with allow_partial=True and
    inspect result.attrs['coverage']; persist it separately when exporting CSV.
    Coverage describes requests and joins, not a verified publication calendar.
    """
    import math
    import warnings

    if not math.isfinite(years) or years <= 0 or years > 5:
        raise ValueError("years must be finite, greater than zero and at most five")
    end = pd.Timestamp(end_date or datetime.now()).normalize().to_pydatetime()
    start = end - timedelta(days=max(1, int(365 * years)))
    frames, windows = [], []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=MAX_CHUNK_DAYS - 1), end)
        window = {"start": current.date().isoformat(), "end": chunk_end.date().isoformat()}
        try:
            frame = get_fund_data(fontip=fontip, bastarih=current.strftime("%d.%m.%Y"),
                                  bittarih=chunk_end.strftime("%d.%m.%Y"))
            window.update(frame.attrs["coverage"])
            if not frame.empty:
                frames.append(frame)
        except (FetchError, ValueError) as error:
            window.update(status="failed", error=str(error))
        windows.append(window)
        current = chunk_end + timedelta(days=1)
    incomplete = [w for w in windows if w["status"] != "ok"]
    if incomplete and not allow_partial:
        raise IncompleteHistoryError(f"History has unresolved windows: {incomplete}")
    if incomplete:
        warnings.warn("Partial history returned; inspect result.attrs['coverage']", RuntimeWarning)
    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=list(INFO_COLUMNS.values()))
    result.attrs["coverage"] = {"complete": not incomplete, "windows": windows}
    return result
