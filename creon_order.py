# creon_order.py
import os
import json
import time
from datetime import datetime, time as dt_time
import win32com.client

TICKER = "A005930".strip()
ACTION_FILE = "action.json"
POSITION_FILE = "position.json"
EXPERIENCE_FILE = "experience.json"

CHECK_INTERVAL = 3

print("🤖 Creon 주문 대행 프로세스 시작")

# =====================
# Creon 시스템 연결 및 계좌 초기화
# =====================
cpCybos = win32com.client.Dispatch("CpUtil.CpCybos")
if cpCybos.IsConnect != 1:
    print("❌ 대신증권 크레온 API 연결 실패")
    exit()

trade = win32com.client.Dispatch("CpTrade.CpTdUtil")
trade.TradeInit()

account = str(trade.AccountNumber[0])
goods = str(trade.GoodsList(account, 1)[0])

order = win32com.client.Dispatch("CpTrade.CpTd0311")
print("✅ 크레온 주문 시스템 연결 성공")

def market_open():
    now = datetime.now().time()
    return dt_time(9, 0) <= now <= dt_time(15, 30)

def get_price():
    obj = win32com.client.Dispatch("DsCbo1.StockMst")
    obj.SetInputValue(0, str(TICKER).upper())  # 타입 및 대문자 안전장치
    obj.BlockRequest()
    return float(obj.GetHeaderValue(11))

def get_balance():
    obj = win32com.client.Dispatch("CpTrade.CpTd6033")
    obj.SetInputValue(0, str(account))
    obj.SetInputValue(1, str(goods))
    obj.SetInputValue(2, int(50))
    obj.SetInputValue(3, "1")
    obj.BlockRequest()

    cash = float(obj.GetHeaderValue(9))
    qty = 0
    count = int(obj.GetHeaderValue(7))

    for i in range(count):
        # 크레온 반환 종목코드의 공백 및 대소문자 문제 원천 방지
        code = str(obj.GetDataValue(12, i)).strip().upper()
        if code == str(TICKER).upper():
            qty = int(obj.GetDataValue(7, i))
            break

    return cash, qty

def save_position(data):
    with open(POSITION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_position():
    if not os.path.exists(POSITION_FILE):
        return None
    try:
        with open(POSITION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def save_experience(data):
    arr = []
    if os.path.exists(EXPERIENCE_FILE):
        try:
            with open(EXPERIENCE_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except:
            arr = []
    arr.append(data)
    with open(EXPERIENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(arr, f, indent=2)

def send_order(side, qty):
    if qty <= 0:
        return False

    # 형식이 일치하지 않습니다 에러 방지용 강제 캐스팅
    order.SetInputValue(0, str(side))    # 1: 매도, 2: 매수
    order.SetInputValue(1, str(account)) # 계좌번호
    order.SetInputValue(2, str(goods))   # 상품구분
    order.SetInputValue(3, str(TICKER).upper()) # 종목코드
    order.SetInputValue(4, int(qty))     # 주문수량
    order.SetInputValue(8, "03")         # "03" -> 시장가 주문

    ret = order.BlockRequest()
    print(f"📣 [크레온 메시지]: {order.GetDibMsg1()}")
    return ret == 0

# =====================
# 메인 제어 루프
# =====================
while True:
    try:
        # action.json 파일이 없거나 AI가 쓰는 중일 때 안전하게 대기
        if not os.path.exists(ACTION_FILE):
            time.sleep(CHECK_INTERVAL)
            continue

        action = None
        try:
            with open(ACTION_FILE, "r", encoding="utf-8") as f:
                action = json.load(f)
            os.remove(ACTION_FILE)  # 읽은 직후 삭제하여 중복 주문 방지
        except (FileNotFoundError, json.JSONDecodeError, PermissionError):
            # 파일 제어 권한 충돌 시 한 템포 쉬고 다음 루프에서 처리
            time.sleep(0.5)
            continue

        if not market_open() or action is None:
            continue

        price = get_price()
        cash, qty = get_balance()
        asset = cash + (qty * price)

        if asset <= 0:
            continue

        current_ratio = (qty * price) / asset
        target = action["target_ratio"]
        diff = target - current_ratio

        # 비중 차이에 따른 주문 필요 수량 계산
        order_qty = int(abs(diff) * asset / price)

        # 1. 매수 조건 (비중 확대)
        if diff > 0 and order_qty > 0:
            # 🔥 [개선] 시장가 호가 등락에 따른 예수금 부족 거부 방지 (가용 금액의 95% 수준만 매수)
            max_buyable_qty = int((cash * 0.95) / price)
            final_qty = min(order_qty, max_buyable_qty)

            if final_qty > 0:
                print(f"🛒 [주문執行] 매수 진행 -> 수량: {final_qty}주 (목표비중 맞춤)")
                if send_order("2", final_qty):  # 2: 매수
                    save_position({
                        "state": action["state"],
                        "entry": price,
                        "qty": final_qty
                    })

        # 2. 매도 조건 (비중 축소)
        elif diff < 0 and order_qty > 0:
            # 보유 수량을 초과해서 매도할 수 없도록 제한 안전장치
            final_qty = min(order_qty, qty)

            if final_qty > 0:
                print(f"🔨 [주문執行] 매도 진행 -> 수량: {final_qty}주")
                if send_order("1", final_qty):  # 1: 매도
                    pos = load_position()
                    if pos:
                        reward = (price - pos["entry"]) / pos["entry"]
                        save_experience({
                            "state": pos["state"],
                            "reward": reward,
                            "next_state": action["state"],
                            "done": True
                        })
                        if os.path.exists(POSITION_FILE):
                            os.remove(POSITION_FILE)

    except Exception as e:
        print("🚨 주문 관리 프로세스 오류:", e)

    time.sleep(CHECK_INTERVAL)