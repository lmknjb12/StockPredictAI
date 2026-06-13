import json
import time
from datetime import datetime
import win32com.client

# =========================
# 설정
# =========================
TICKER = "A005930".strip()  # 공백 제거로 안전성 확보
OUTPUT = "market_data.json"
INTERVAL = 10

print("📡 Creon 데이터 수집 시작")

# =========================
# Creon 연결 확인
# =========================
cpCybos = win32com.client.Dispatch("CpUtil.CpCybos")

if cpCybos.IsConnect != 1:
    print("❌ Creon 연결 실패 (프로그램이 꺼져있거나 로그인 세션 확인 필요)")
    exit()

print("✅ Creon 연결 성공")

# =========================
# 계좌 초기화
# =========================
trade = win32com.client.Dispatch("CpTrade.CpTdUtil")
trade.TradeInit()

account = trade.AccountNumber[0]
goods = trade.GoodsList(account, 1)[0]

# =========================
# 현재가 조회 기능
# =========================
def get_price():
    obj = win32com.client.Dispatch("DsCbo1.StockMst")
    
    # 확실하게 문자열 타입으로 전달
    obj.SetInputValue(0, str(TICKER).upper())
    obj.BlockRequest()

    return {
        "close": float(obj.GetHeaderValue(11)),
        "volume": float(obj.GetHeaderValue(18))
    }

# =========================
# 투자자 수급 조회 기능 (🔥 에러 해결 포인트)
# =========================
def get_investor():
    obj = win32com.client.Dispatch("CpSysDib.CpSvrNew7221")

    # [핵심] Type:0 에러 방지를 위해 명시적으로 str()과 upper() 적용
    obj.SetInputValue(0, str(TICKER).upper())
    
    # [핵심] Type:1 에러 방지를 위해 아스키 코드가 아닌 순수 정수(int) 1 적용
    obj.SetInputValue(1, int(1))

    obj.BlockRequest()

    foreigner = 0
    institution = 0
    individual = 0

    try:
        foreigner = float(obj.GetDataValue(0, 0))
        institution = float(obj.GetDataValue(1, 0))
        individual = float(obj.GetDataValue(2, 0))
    except Exception as e:
        # 혹시 모를 데이터 파싱 에러 방지용 안전장치
        pass

    return {
        "foreigner": foreigner,
        "institution": institution,
        "individual": individual
    }

# =========================
# 계좌 보유 잔고 조회 기능
# =========================
def get_account():
    obj = win32com.client.Dispatch("CpTrade.CpTd6033")
    
    obj.SetInputValue(0, str(account))
    obj.SetInputValue(1, str(goods))
    obj.SetInputValue(2, int(50))
    obj.SetInputValue(3, "1")
    obj.BlockRequest()

    cash = float(obj.GetHeaderValue(9))
    qty = 0
    count = obj.GetHeaderValue(7)

    for i in range(count):
        code = str(obj.GetDataValue(12, i)).strip().upper()
        if code == str(TICKER).upper():
            qty = int(obj.GetDataValue(7, i))
            break

    return {
        "cash": cash,
        "qty": qty
    }

# =========================
# 기술지표 생성 기능 (기본값 제공)
# =========================
def get_indicators(price):
    # 나중에 이 부분에 pandas, ta-lib 등을 활용해 RSI, MACD 등을 추가하실 수 있습니다.
    return [
        float(price / 100000),
        0.5,
        0.5,
        0.5,
        0.5
    ]

# =========================
# 종합 데이터 가공 및 파일 저장
# =========================
def save_market():
    price = get_price()
    investor = get_investor()
    account = get_account()

    data = {
        "time": str(datetime.now()),
        "close": price["close"],
        "volume": price["volume"],
        "foreigner": investor["foreigner"],
        "institution": investor["institution"],
        "individual": investor["individual"],
        "cash": account["cash"],
        "stock_value": float(account["qty"] * price["close"]),
        "holding": int(account["qty"]),
        "indicators": get_indicators(price["close"])
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"📊 [데이터 수집] {data['time'].split('.')[0]} | 현재가: {int(price['close']):,}원 | 외국인 수급: {int(investor['foreigner']):,}")

# =========================
# 메인 루프 실행
# =========================
while True:
    try:
        save_market()
    except Exception as e:
        print("🚨 데이터 가공/저장 오류:", e)

    time.sleep(INTERVAL)