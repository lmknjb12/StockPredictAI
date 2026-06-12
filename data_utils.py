import os
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

import pandas as pd

from finrl.meta.preprocessor.yahoodownloader import YahooDownloader


PYKRX_FEATURES = [
    "foreigner_net_buy_value",
    "institution_net_buy_value",
    "individual_net_buy_value",
    "foreigner_trade_volume",
    "institution_trade_volume",
    "individual_trade_volume",
]


def is_korean_ticker(ticker: str) -> bool:
    return ticker.isdigit() and len(ticker) == 6


def _to_yyyymmdd(date_value: str) -> str:
    return pd.Timestamp(date_value).strftime("%Y%m%d")


def _normalize_price_frame(price_frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    price_frame = price_frame.reset_index().rename(
        columns={
            "날짜": "date",
            "시가": "open",
            "고가": "high",
            "저가": "low",
            "종가": "close",
            "거래량": "volume",
            "거래대금": "amount",
            "등락률": "change",
            "index": "date",
        }
    )

    if "date" not in price_frame.columns:
        price_frame = price_frame.rename(columns={price_frame.columns[0]: "date"})

    price_frame["date"] = pd.to_datetime(price_frame["date"])
    price_frame["tic"] = ticker
    price_frame["adjcp"] = price_frame["close"]
    return price_frame


def _select_investor_columns(frame: pd.DataFrame, suffix: str) -> pd.DataFrame:
    column_mapping = {
        "외국인": f"foreigner_{suffix}",
        "외국인합계": f"foreigner_{suffix}",
        "기관": f"institution_{suffix}",
        "기관합계": f"institution_{suffix}",
        "개인": f"individual_{suffix}",
    }

    selected_columns = ["date"]
    rename_map = {}
    for source_column, target_column in column_mapping.items():
        if source_column in frame.columns:
            selected_columns.append(source_column)
            rename_map[source_column] = target_column

    if len(selected_columns) == 1:
        return pd.DataFrame({"date": frame["date"]})

    return frame[selected_columns].rename(columns=rename_map)


def _load_pykrx_data(start_date: str, end_date: str, ticker: str) -> pd.DataFrame:
    original_krx_id = os.environ.pop("KRX_ID", None)
    original_krx_pw = os.environ.pop("KRX_PW", None)

    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            from pykrx import stock
            from pykrx.website.comm.auth import set_auth_session

        set_auth_session(None)
    except ModuleNotFoundError as exc:
        raise ImportError("pykrx 패키지가 필요합니다. `pip install pykrx` 후 다시 실행하세요.") from exc

    start = _to_yyyymmdd(start_date)
    end = _to_yyyymmdd(end_date)

    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            price_frame = stock.get_market_ohlcv_by_date(start, end, ticker)
            value_frame = stock.get_market_trading_value_by_date(start, end, ticker)
            volume_frame = stock.get_market_trading_volume_by_date(start, end, ticker)
    finally:
        if original_krx_id is not None:
            os.environ["KRX_ID"] = original_krx_id
        if original_krx_pw is not None:
            os.environ["KRX_PW"] = original_krx_pw

    if price_frame.empty:
        raise ValueError(f"pykrx에서 {ticker} 데이터가 비어 있습니다. 날짜와 종목코드를 확인하세요.")

    price_frame = _normalize_price_frame(price_frame, ticker)

    if not value_frame.empty:
        value_frame = value_frame.reset_index().rename(columns={"날짜": "date", "index": "date"})
        if "date" not in value_frame.columns:
            value_frame = value_frame.rename(columns={value_frame.columns[0]: "date"})
        value_frame["date"] = pd.to_datetime(value_frame["date"])
    else:
        value_frame = pd.DataFrame({"date": price_frame["date"]})

    if not volume_frame.empty:
        volume_frame = volume_frame.reset_index().rename(columns={"날짜": "date", "index": "date"})
        if "date" not in volume_frame.columns:
            volume_frame = volume_frame.rename(columns={volume_frame.columns[0]: "date"})
        volume_frame["date"] = pd.to_datetime(volume_frame["date"])
    else:
        volume_frame = pd.DataFrame({"date": price_frame["date"]})

    value_frame = _select_investor_columns(value_frame, "net_buy_value")
    volume_frame = _select_investor_columns(volume_frame, "trade_volume")

    merged_frame = price_frame.merge(value_frame, on="date", how="left").merge(volume_frame, on="date", how="left")
    for feature_name in PYKRX_FEATURES:
        if feature_name not in merged_frame.columns:
            merged_frame[feature_name] = 0.0
        merged_frame[feature_name] = merged_frame[feature_name].fillna(0.0)

    return merged_frame.sort_values(["date", "tic"]).reset_index(drop=True)


def load_market_data(start_date: str, end_date: str, ticker_list: list[str]) -> pd.DataFrame:
    if all(is_korean_ticker(ticker) for ticker in ticker_list):
        frames = [_load_pykrx_data(start_date, end_date, ticker) for ticker in ticker_list]
        return pd.concat(frames, ignore_index=True)

    market_data = YahooDownloader(
        start_date=start_date,
        end_date=end_date,
        ticker_list=ticker_list,
    ).fetch_data()
    market_data = market_data.sort_values(["date", "tic"]).reset_index(drop=True)
    for feature_name in PYKRX_FEATURES:
        market_data[feature_name] = 0.0
    return market_data