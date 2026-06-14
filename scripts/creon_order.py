import sys
import os
import time
import numpy as np
import win32com.client
from datetime import datetime, time as dt_time

# root 경로를 sys.path에 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from config import (
    TICKER, ACTION_FILE, POSITION_FILE, EXPERIENCE_FILE, 
    ORDER_CHECK_INTERVAL, TRANSACTION_FEE, MARKET_FALL_LIMIT
)
from core.utils.common import setup_logger, atomic_write_json, load_json
from core.utils.creon import CreonSession, get_stock_price, get_account_balance

# 로거 설정
logger = setup_logger("OrderManager")

class OrderExecutor:
    def __init__(self, session):
        self.session = session
        self.order_obj = win32com.client.Dispatch("CpTrade.CpTd0311")

    def market_open(self):
        now = datetime.now().time()
        return dt_time(9, 0) <= now <= dt_time(15, 30)

    def send_order(self, side, qty):
        """
        주문 전송
        side: "1" (매도), "2" (매수)
        """
        if qty <= 0:
            return False

        try:
            self.order_obj.SetInputValue(0, str(side))
            self.order_obj.SetInputValue(1, str(self.session.account))
            self.order_obj.SetInputValue(2, str(self.session.goods))
            self.order_obj.SetInputValue(3, str(TICKER).upper())
            self.order_obj.SetInputValue(4, int(qty))
            self.order_obj.SetInputValue(8, "03") # 시장가

            ret = self.order_obj.BlockRequest()
            msg = self.order_obj.GetDibMsg1()
            logger.info(f"📣 [크레온 주문 응답]: {msg}")
            return ret == 0
        except Exception as e:
            logger.error(f"주문 전송 중 오류: {e}")
            return False

    def is_trading_hour(self):
        from config import TRADING_HOURS
        now_str = datetime.now().strftime("%H:%M")
        for start, end in TRADING_HOURS:
            if start <= now_str <= end:
                return True
        return False

    def check_risk_management(self, current_price, entry_price, qty):
        """손절/익절 체크"""
        from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT
        if qty <= 0 or entry_price <= 0:
            return None
        
        return_pct = (current_price - entry_price) / entry_price
        
        if return_pct <= -STOP_LOSS_PCT:
            return "STOP_LOSS"
        if return_pct >= TAKE_PROFIT_PCT:
            return "TAKE_PROFIT"
        return None

def main():
    logger.info("🤖 Creon 주문 대행 프로세스 시작")
    
    session = CreonSession(logger)
    if not session.connect():
        return

    executor = OrderExecutor(session)

    while True:
        try:
            if not session.check_connection():
                logger.warning("Creon 연결 끊김, 재연결 시도...")
                if not session.connect():
                    time.sleep(10)
                    continue

            # 0. 리스크 관리 체크 (AI 판단보다 우선함)
            price_info = get_stock_price(TICKER)
            price = price_info["close"]
            pos = load_json(POSITION_FILE)
            
            if pos:
                risk_signal = executor.check_risk_management(price, pos["entry_price"], pos["qty"])
                if risk_signal:
                    return_pct = (price - pos["entry_price"]) / pos["entry_price"]
                    logger.warning(f"🚨 [위험관리] {risk_signal} | 수량: {pos['qty']} | 수익률: {return_pct:.2%}")
                    
                    if executor.send_order("1", pos["qty"]):
                        # 매도 기록 저장
                        reward = np.log(price / pos["entry_price"]) - TRANSACTION_FEE
                        exp = {
                            "state": pos["state"],
                            "action": risk_signal,
                            "reward": reward,
                            "entry_price": pos["entry_price"],
                            "exit_price": price,
                            "next_state": pos["state"], # 강제종료이므로 상태 전이 무시
                            "time": str(datetime.now())
                        }
                        exps = load_json(EXPERIENCE_FILE, default=[])
                        exps.append(exp)
                        atomic_write_json(EXPERIENCE_FILE, exps)
                        os.remove(POSITION_FILE)
                        continue

            # 1. 매매 시간 필터
            if not executor.is_trading_hour():
                time.sleep(10)
                continue

            # 2. 시장 트렌드 필터 (코스피 급락 시 매수 금지)
            market_data = load_json(MARKET_DATA_FILE)
            if market_data and market_data.get("market_change_pct", 0) <= MARKET_FALL_LIMIT:
                logger.warning(f"📉 시장 급락 감지 ({market_data['market_change_pct']:.2%}) - 매수 제한 모드")
                # 매수 신호가 오더라도 무시하도록 설정 (아래 action 처리 시 check)
                market_is_bad = True
            else:
                market_is_bad = False

            # 3. action.json 확인
            action_data = load_json(ACTION_FILE)
            if action_data is None:
                time.sleep(ORDER_CHECK_INTERVAL)
                continue

            # 파일 읽은 후 즉시 삭제 (중복 처리 방지)
            if os.path.exists(ACTION_FILE):
                os.remove(ACTION_FILE)

            if not executor.market_open():
                logger.info("장 운영시간이 아닙니다. 주문을 건너뜁니다.")
                continue

            # 현재 상태 조회
            price_info = get_stock_price(TICKER)
            price = price_info["close"]
            account_info = get_account_balance(session.account, session.goods, TICKER)
            cash = account_info["cash"]
            qty = account_info["qty"]
            
            total_asset = cash + (qty * price)
            if total_asset <= 0:
                continue

            current_ratio = (qty * price) / total_asset
            target_ratio = action_data["target_ratio"]
            diff_ratio = target_ratio - current_ratio
            
            # 주문 수량 계산
            order_qty = int(abs(diff_ratio) * total_asset / price)

            # 1. 매수 (비중 확대)
            if diff_ratio > 0.05 and order_qty > 0: # 5% 이상 차이날 때만 실행
                if market_is_bad:
                    logger.warning("🚫 시장 상태 불량으로 매수를 차단합니다.")
                    continue
                
                # 가용 현금의 95% 수준만 매수 (안전장치)
                max_buyable = int((cash * 0.95) / price)
                final_qty = min(order_qty, max_buyable)

                if final_qty > 0:
                    logger.info(f"🛒 [매수] 수량: {final_qty}주 (목표비중: {target_ratio:.2%})")
                    if executor.send_order("2", final_qty):
                        atomic_write_json(POSITION_FILE, {
                            "state": action_data["state"],
                            "entry_price": price,
                            "qty": final_qty,
                            "time": str(datetime.now())
                        })

            # 2. 매도 (비중 축소)
            elif diff_ratio < -0.05 and order_qty > 0:
                final_qty = min(order_qty, qty)

                if final_qty > 0:
                    logger.info(f"🔨 [매도] 수량: {final_qty}주 (목표비중: {target_ratio:.2%})")
                    if executor.send_order("1", final_qty):
                        # 경험 데이터 저장 (학습용)
                        pos = load_json(POSITION_FILE)
                        if pos:
                            reward = np.log(price / pos["entry_price"]) - 0.003 # 거래세 등 반영
                            exp = {
                                "state": pos["state"],
                                "action": action_data["action"],
                                "reward": reward,
                                "entry_price": pos["entry_price"],
                                "exit_price": price,
                                "next_state": action_data["state"],
                                "time": str(datetime.now())
                            }
                            
                            # 기존 경험 데이터에 추가
                            exps = load_json(EXPERIENCE_FILE, default=[])
                            exps.append(exp)
                            atomic_write_json(EXPERIENCE_FILE, exps)
                            
                            if os.path.exists(POSITION_FILE):
                                os.remove(POSITION_FILE)

        except Exception as e:
            logger.error(f"주문 관리 루프 오류: {e}")

        time.sleep(ORDER_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
