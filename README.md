# Turkey Fund Data — TEFAS prices and KAP fund reference data in Python

Two dependency-light Python scripts for **Turkish mutual funds and pension funds (BES)**: daily prices and full portfolio allocations from **TEFAS**, and the fund reference data — **ISIN, founder, portfolio manager, risk value, IPO date, interest-free status** — from **KAP**.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Data](https://img.shields.io/badge/coverage-3%2C527%20funds-orange)](#coverage)

If you have ever tried to join a TEFAS price series to *what the fund actually is* — who runs it, what its ISIN is, whether it is interest-free, when it was launched — you have hit the gap this repository fills. Price data for Turkish funds is well served by several libraries. **Fund reference data is not.** `scrapeKAP.py` is the part you will not easily find elsewhere.

---

## What you get

| | `tefas.py` | `scrapeKAP.py` |
|---|---|---|
| **Source** | [TEFAS](https://www.tefas.gov.tr/) / fonturkey.com.tr JSON API | [KAP](https://www.kap.org.tr/) — Public Disclosure Platform |
| **Gives you** | Daily price, AUM, investor count, 54 portfolio allocation columns | ISIN, founder, manager, auditor, risk value, fund type, IPO date, interest content |
| **Granularity** | One row per fund per day | One row per fund |
| **Typical size** | ~2,000 rows per trading day, 63 columns | 3,527 rows, 12 columns |

Both return plain `pandas` DataFrames. No classes, no config files, no API key.

---

## Quick start

```bash
git clone https://github.com/hakyemezi/turkeyfundsdata.git
cd turkeyfundsdata
pip install -r requirements.txt
```

**Fund prices and allocations**

```python
from tefas import get_fund_data, get_fund_data_for_years

# One period, up to 30 days
df = get_fund_data(fontip="YAT", bastarih="01.09.2026", bittarih="05.09.2026")

# Longer history, split into chunks and paced automatically
df = get_fund_data_for_years(0.5, "YAT")     # last 6 months
df = get_fund_data_for_years(5, "EMK")       # last 5 years of pension funds
```

`fontip` is `"YAT"` for mutual funds or `"EMK"` for pension funds.

**Fund reference data**

```python
from scrapeKAP import get_all, fon_data

funds = get_all()                # all 3,527 funds with full metadata
equity_funds = fon_data("YF")    # one category only
```

---

## Sample output

`get_fund_data` — price and allocation, joined:

| TARIH | FONKODU | FONUNVAN | FIYAT | KISISAYISI | PORTFOYBUYUKLUK | DT | VMTL | HS | ... |
|---|---|---|---|---|---|---|---|---|---|
| 2026-08-03 | AAL | ATA PORTFÖY PARA PİYASASI (TL) FONU | 3.465327 | 4,581 | 2,145,552,900.64 | 15.81 | 19.72 | 0.00 | ... |

`get_all` — fund reference data:

| CODE | TITLE | KIND | ISIN | MANAGER | RD | TYPE | INTEREST | IPO_DATE |
|---|---|---|---|---|---|---|---|---|
| BON | A1 CAPİTAL PORTFÖY BORÇLANMA ARAÇLARI FONU | YF | TRYA1PS00059 | A1 CAPİTAL PORTFÖY YÖNETİMİ A.Ş | NaN | NaN | NaN | 2025-10-14 |
| EAE | AGESA HAYAT VE EMEKLİLİK A.Ş. ALTIN EMEKLİLİK YATIRIM FONU | EYF | TRYCUHE00487 | AK PORTFÖY YÖNETİMİ A.Ş. | 6 | Kıymetli Madenler Fonu | Faiz içerir | 2025-09-02 |

Risk value, fund type and interest content are `NaN` for the first row because KAP publishes those three items for pension funds only — the second row is a pension fund. `FOUNDER`, `REPRESENTATIVE` and `AUDITOR` are omitted here for width.

Join the two frames on `FONKODU` / `CODE` to get prices with full fund context.

---

## Coverage

`get_all()` returns every fund KAP publishes, across ten categories:

| Code | Category | Funds |
|---|---|---|
| `YF` | Securities mutual funds — *yatırım fonları* | 2,147 |
| `GSF` | Venture capital funds — *girişim sermayesi* | 601 |
| `GMF` | Real estate funds — *gayrimenkul* | 336 |
| `EYF` | Pension funds — *emeklilik yatırım fonları* | 288 |
| `OKS` | Auto-enrolment pension funds — *OKS* | 112 |
| `BYF` | Exchange traded funds — *borsa yatırım fonları* | 34 |
| `YYF` | Foreign funds sold in Turkey | 9 |
| `VFF` `KFF` `PFF` | Housing, participation and project finance funds | currently none listed |

Field completeness on the merged result: ISIN and founder 100%, auditor 99.7%, manager 97.6%, IPO date 67.3%. Risk value, fund type and interest content are published by KAP for pension funds only (~12%).

---

## Portfolio allocation columns

`tefas.py` returns one percentage column per instrument type. The API returns them as bare short codes with no labels attached, so here is the full mapping:

<details>
<summary><b>All 54 allocation codes</b></summary>

| Code | Turkish | English |
|---|---|---|
| `HS` | Hisse Senedi | Equity |
| `DT` | Devlet Tahvili | Government bond |
| `HB` | Hazine Bonosu | Treasury bill |
| `EUT` | Eurobonds | Eurobonds |
| `BB` | Banka Bonosu | Bank bill |
| `FB` | Finansman Bonosu | Commercial paper |
| `OST` | Özel Sektör Tahvili | Corporate bond |
| `KBA` | Kamu Dış Borçlanma Araçları | Public external debt instruments |
| `OSDB` | Özel Sektör Dış Borçlanma Araçları | Corporate external debt instruments |
| `KIBD` | Döviz Cinsi Kamu İç Borçlanma Araçları | FX-denominated public domestic debt |
| `DB` | Döviz Ödemeli Bono | FX-settled bill |
| `DOT` | Dövize Ödemeli Tahvil | FX-settled bond |
| `VDM` | Varlığa Dayalı Menkul Kıymetler | Asset-backed securities |
| `R` | Repo | Repo |
| `TR` | Ters-Repo | Reverse repo |
| `BPP` | Borsa İstanbul Para Piyasası | Borsa İstanbul money market |
| `TPP` | Takasbank Para Piyasası | Takasbank money market |
| `BTAA` | BİST Taahhütlü İşlem Pazarı Alım | BİST committed transactions, buy |
| `BTAS` | BİST Taahhütlü İşlem Pazarı Satım | BİST committed transactions, sell |
| `VM` | Vadeli Mevduat | Time deposit |
| `VMTL` | Mevduat (TL) | Deposit, TRY |
| `VMD` | Mevduat (Döviz) | Deposit, FX |
| `VMAU` | Mevduat (Altın) | Deposit, gold |
| `KH` | Katılım Hesabı | Participation account |
| `KHTL` | Katılma Hesabı (TL) | Participation account, TRY |
| `KHD` | Katılma Hesabı (Döviz) | Participation account, FX |
| `KHAU` | Katılma Hesabı (Altın) | Participation account, gold |
| `KKS` | Kamu Kira Sertifikaları | Public lease certificates (sukuk) |
| `KKSTL` | Kamu Kira Sertifikaları (TL) | Public lease certificates, TRY |
| `KKSD` | Kamu Kira Sertifikaları (Döviz) | Public lease certificates, FX |
| `KKSYD` | Kamu Yurt Dışı Kira Sertifikaları | Public foreign lease certificates |
| `OSKS` | Özel Sektör Kira Sertifikaları | Corporate lease certificates |
| `OKSYD` | Özel Sektör Yurt Dışı Kira Sertifikaları | Corporate foreign lease certificates |
| `KM` | Kıymetli Madenler | Precious metals |
| `KMBYF` | Kıymetli Madenler Cinsinden BYF | Precious metal ETFs |
| `KMKBA` | Kıymetli Madenler Cinsinden Kamu Borçlanma Araçları | Precious metal public debt instruments |
| `KMKKS` | Kıymetli Madenler Cinsinden Kamu Kira Sertifikaları | Precious metal public lease certificates |
| `YHS` | Yabancı Hisse Senedi | Foreign equity |
| `YBA` | Yabancı Borçlanma Aracı | Foreign debt instrument |
| `YBKB` | Yabancı Kamu Borçlanma Araçları | Foreign public debt instruments |
| `YBOSB` | Yabancı Özel Sektör Borçlanma Araçları | Foreign corporate debt instruments |
| `YMK` | Yabancı Menkul Kıymet | Foreign security |
| `YBYF` | Yabancı Borsa Yatırım Fonları | Foreign ETFs |
| `BYF` | Borsa Yatırım Fonları Katılma Payları | ETF units |
| `YYF` | Yatırım Fonları Katılma Payları | Mutual fund units |
| `FKB` | Fon Katılma Belgesi | Fund participation certificate |
| `GYY` | Gayrimenkul Yatırımları | Real estate investments |
| `GAS` | Gayrimenkul Sertifikası | Real estate certificate |
| `GYKB` | Gayrimenkul Yatırım Fonları Katılma Payları | Real estate fund units |
| `GSYY` | Girişim Sermayesi Yatırımları | Venture capital investments |
| `GSYKB` | Girişim Sermayesi Yatırım Fonları Katılma Payları | Venture capital fund units |
| `T` | Türev Araçları | Derivatives |
| `VINT` | Vadeli İşlemler Nakit Teminatları | Futures cash collateral |
| `D` | Diğer | Other |

</details>

---

## Notes on the data sources

**The TEFAS API fails silently.** It answers HTTP 200 with an empty result in two cases: when a request covers more than about one month, and when requests arrive too quickly. Neither is an error you can catch. `get_fund_data` therefore refuses ranges longer than 30 days instead of handing back nothing, and `get_fund_data_for_years` splits the period into chunks, paces the requests and retries empty answers.

**Both sources have changed before.** The older `/api/DB/BindHistoryInfo` and `/api/DB/BindHistoryAllocation` endpoints now return 404; these scripts target the endpoints the site uses today. KAP was rebuilt and its pages are now read as HTML tables rather than by CSS class name. If either source changes again the scripts will need updating — issues and pull requests are welcome.

**Be considerate.** Both sources are public but neither is a high-volume API. The scripts pace themselves; please do not remove that.

---

## Türkçe

Türkiye'deki **yatırım fonları** ve **emeklilik yatırım fonları (BES)** için iki Python scripti.

- **`tefas.py`** — TEFAS üzerinden günlük fon fiyatı, portföy büyüklüğü, yatırımcı sayısı ve 54 kalemlik **portföy dağılımı**. Fon tipi `"YAT"` (yatırım fonu) veya `"EMK"` (emeklilik fonu).
- **`scrapeKAP.py`** — KAP üzerinden fon künyesi: **ISIN kodu, kurucu, portföy yöneticisi, bağımsız denetim kuruluşu, risk değeri, fon türü, halka arz tarihi, faiz içeriği**. 3.527 fon, on kategori: yatırım fonu, emeklilik yatırım fonu, OKS, borsa yatırım fonu, gayrimenkul, girişim sermayesi.

İkisi de `pandas` DataFrame döndürür. `FONKODU` ile `CODE` üzerinden birleştirerek fiyat serisine fonun künyesini ekleyebilirsiniz.

TEFAS API'si 30 günden uzun aralıklarda ve çok hızlı gelen isteklerde **hata vermeden boş sonuç** döner. Bu yüzden uzun dönemler için `get_fund_data_for_years` kullanın; dönemi parçalara böler, istekleri yavaşlatır ve boş dönen parçaları tekrar dener.

---

## Related

- [besFundLens](https://github.com/hakyemezi/besFundLens) — analytics engine built on this data: decomposes pension fund AUM change into market effect and estimated investor flow, classifies funds by what they actually hold, and writes bilingual reports.

## Contributing

Issues and pull requests are welcome, particularly if a data source changes and something breaks.

## License

[MIT](LICENSE)
