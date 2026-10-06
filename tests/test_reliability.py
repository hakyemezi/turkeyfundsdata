import pandas as pd
import pytest
import requests
import tefas
import scrapeKAP as kap


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(tefas.time, 'sleep', lambda _: None)


def record(code='AAA', title='Fund', **extra):
    return dict(tarih='2026-08-03', fonKodu=code, fonUnvan=title, **extra)


def test_missing_values_unmatched_keys_and_renamed_fund_survive(monkeypatch):
    values = iter([[record(fiyat=None, tedPaySayisi=10), record('BBB', fiyat=2)],
                   [record(title='New title', hs=0), record('CCC', hs=None)]])
    monkeypatch.setattr(tefas, 'post_json', lambda *a: next(values))
    frame = tefas.get_fund_data()
    assert set(frame.FONKODU) == {'AAA', 'BBB', 'CCC'}
    assert pd.isna(frame.set_index('FONKODU').loc['AAA', 'FIYAT'])
    assert frame.set_index('FONKODU').loc['AAA', 'HS'] == 0
    assert pd.api.types.is_numeric_dtype(frame.TEDPAYSAYISI)
    assert frame.attrs['coverage']['title_mismatches'] == 1
    assert frame.attrs['coverage']['status'] == 'partial'


def test_conflicting_fund_date_rejected(monkeypatch):
    monkeypatch.setattr(tefas, 'post_json', lambda *a: [record(fiyat=1), record(fiyat=2)])
    with pytest.raises(ValueError, match='Conflicting'):
        tefas.get_fund_data()


def test_json_retry_and_transport_failure(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): raise ValueError('invalid JSON')
    calls = []
    monkeypatch.setattr(tefas.requests, 'post', lambda *a, **kw: calls.append(kw) or Response())
    with pytest.raises(tefas.FetchError):
        tefas.post_json('https://example.invalid', {})
    assert len(calls) == tefas.MAX_RETRIES


def test_valid_empty_distinguished_from_failure(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'resultList': []}
    monkeypatch.setattr(tefas.requests, 'post', lambda *a, **kw: Response())
    assert tefas.post_json('x', {}) == []
    def fail(*a, **kw): raise requests.Timeout('timeout')
    monkeypatch.setattr(tefas.requests, 'post', fail)
    with pytest.raises(tefas.FetchError): tefas.post_json('x', {})


def test_partial_history_requires_opt_in_and_reports_windows(monkeypatch):
    ranges = []
    def fetch(**kw):
        ranges.append((pd.to_datetime(kw['bastarih'], dayfirst=True), pd.to_datetime(kw['bittarih'], dayfirst=True)))
        raise tefas.FetchError('unavailable')
    monkeypatch.setattr(tefas, 'get_fund_data', fetch)
    with pytest.raises(tefas.IncompleteHistoryError):
        tefas.get_fund_data_for_years(.2, 'EMK', end_date='2026-09-10')
    with pytest.warns(RuntimeWarning):
        frame = tefas.get_fund_data_for_years(.2, 'EMK', end_date='2026-09-10', allow_partial=True)
    assert not frame.attrs['coverage']['complete']
    assert all((b-a).days < 30 for a,b in ranges)
    windows = frame.attrs['coverage']['windows']
    for left, right in zip(windows, windows[1:]):
        assert pd.Timestamp(left['end']) + pd.Timedelta(days=1) == pd.Timestamp(right['start'])


@pytest.mark.parametrize('years', [0, -1, 6, float('nan'), float('inf')])
def test_invalid_years(years):
    with pytest.raises(ValueError): tefas.get_fund_data_for_years(years, 'EMK')


def test_kap_duplicates_and_empty_markup(monkeypatch):
    frame = pd.DataFrame({'TITLE': [' A  Fund ', 'A Fund'], 'ISIN': ['x', 'x']})
    assert len(kap.unique_titles(frame)) == 1
    frame.loc[1, 'ISIN'] = 'y'
    with pytest.raises(ValueError, match='Conflicting'): kap.unique_titles(frame)
    class Response:
        text = '<html>Maintenance</html>'
        def raise_for_status(self): pass
    monkeypatch.setattr(kap.requests, 'get', lambda *a, **kw: Response())
    with pytest.raises(ValueError, match='No KAP table'): kap.get_rows('x')
