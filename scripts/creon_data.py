import sys
import os
import time
from datetime import datetime

# root 경로를 sys.path에 추가하여 config 및 core 모듈 임포트 가능하게 함
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from config import TICKER, MARKET_DATA_FILE, DATA_INTERVAL
from core.utils.common import setup_logger, atomic_write_json
from core.utils.creon import CreonSession, get_stock_price, get_investor_data, get_account_balance, get_market_index
from core.utils.indicators import calculate_indicators

# 로거 설정
logger = setup_logger("DataCollector")

# 실시간 지표 계산을 위한 데이터 버퍼 (최근 100개 유지)
history = []

def main():
    logger.info("📡 [DeepThink] 고도화 데이터 수집 엔진 시작")
    
    session = CreonSession(logger)
    if not session.connect():
        return

    while True:
        try:
            if not session.check_connection():
                logger.warning("Creon 연결 끊김, 재연결 시도...")
                if not session.connect():
                    time.sleep(10)
                    continue

            # 1. 가격, 수급, 지수 데이터 수집
            price_info = get_stock_price(TICKER)
            investor_info = get_investor_data(TICKER)
            market_index = get_market_index()
            
            # 2. 히스토리 업데이트
            history.append({
                "close": price_info["close"],
                "volume": price_info["volume"],
                "foreigner": investor_info["foreigner"],
                "institution": investor_info["institution"],
                "individual": investor_info["individual"]
            })
            if len(history) > 100: history.pop(0)
            
            # 3. 실시간 기술적 지표 계산 (NumPy 기반 리스트 전달)
            indicators = calculate_indicators(history)
            
            # 4. 계좌 정보
            account_info = get_account_balance(session.account, session.goods, TICKER)
            
            # 5. 데이터 패키징
            data = {
                "time": str(datetime.now()),
                "close": price_info["close"],
                "volume": price_info["volume"],
                "foreigner": investor_info["foreigner"],
                "institution": investor_info["institution"],
                "individual": investor_info["individual"],
                "market_index": market_index["price"],
                "market_change_pct": market_index["change_pct"],
                "cash": account_info["cash"],
                "qty": account_info["qty"],
                "stock_value": float(account_info["qty"] * price_info["close"]),
                "indicators": indicators
            }

            # 6. 원자적 파일 저장
            if atomic_write_json(MARKET_DATA_FILE, data):
                # 1분(약 6회)에 한 번만 상태 보고
                if int(time.time()) % 60 < DATA_INTERVAL:
                    logger.info(f"📡 [상태정상] {int(price_info['close']):,}원 | KOSPI: {market_index['price']:.2f}")
            else:
                logger.error("데이터 저장 실패")

        except Exception as e:
            logger.error(f"데이터 수집 중 오류: {e}")

        time.sleep(DATA_INTERVAL)

if __name__ == "__main__":
    main()
