import win32com.client
import time

class CreonSession:
    def __init__(self, logger):
        self.logger = logger
        self.cpCybos = None
        self.trade = None
        self.account = None
        self.goods = None
        
    def connect(self):
        try:
            self.cpCybos = win32com.client.Dispatch("CpUtil.CpCybos")
            if self.cpCybos.IsConnect != 1:
                self.logger.error("Creon 연결 실패 (로그인 필요)")
                return False
            
            self.trade = win32com.client.Dispatch("CpTrade.CpTdUtil")
            if self.trade.TradeInit() != 0:
                self.logger.error("주문 초기화 실패")
                return False
            
            self.account = self.trade.AccountNumber[0]
            self.goods = self.trade.GoodsList(self.account, 1)[0]
            
            self.logger.info(f"Creon 연결 성공 (계좌: {self.account})")
            return True
        except Exception as e:
            self.logger.error(f"Creon 연결 오류: {e}")
            return False

    def check_connection(self):
        if self.cpCybos is None:
            return self.connect()
        return self.cpCybos.IsConnect == 1

def get_stock_price(ticker):
    """현재가 및 거래량 조회"""
    obj = win32com.client.Dispatch("DsCbo1.StockMst")
    obj.SetInputValue(0, ticker.upper())
    obj.BlockRequest()
    return {
        "close": float(obj.GetHeaderValue(11)),
        "volume": float(obj.GetHeaderValue(18))
    }

def get_investor_data(ticker):
    """투자자별 수급 데이터 조회"""
    obj = win32com.client.Dispatch("CpSysDib.CpSvrNew7221")
    obj.SetInputValue(0, ticker.upper())
    obj.SetInputValue(1, 1) # 1: 당일 당일
    obj.BlockRequest()
    
    try:
        return {
            "foreigner": float(obj.GetDataValue(0, 0)),
            "institution": float(obj.GetDataValue(1, 0)),
            "individual": float(obj.GetDataValue(2, 0))
        }
    except:
        return {"foreigner": 0.0, "institution": 0.0, "individual": 0.0}

def get_market_index():
    """코스피(KOSPI) 지수 조회"""
    obj = win32com.client.Dispatch("DsCbo1.StockMst")
    obj.SetInputValue(0, "U001") # U001: KOSPI
    obj.BlockRequest()
    return {
        "price": float(obj.GetHeaderValue(11)),
        "change_pct": float(obj.GetHeaderValue(12)) # 전일 대비율
    }

def get_account_balance(account, goods, ticker):
    """계좌 잔고 조회 (예수금 및 특정 종목 보유량)"""
    obj = win32com.client.Dispatch("CpTrade.CpTd6033")
    obj.SetInputValue(0, account)
    obj.SetInputValue(1, goods)
    obj.SetInputValue(2, 50) # 요청 개수
    obj.SetInputValue(3, "1") # 1: 종목별
    obj.BlockRequest()

    cash = float(obj.GetHeaderValue(9)) # 결제기준 잔고 (또는 8: 관리기준 잔고)
    qty = 0
    avg_price = 0.0
    count = obj.GetHeaderValue(7)

    for i in range(count):
        code = str(obj.GetDataValue(12, i)).strip().upper()
        if code == ticker.upper():
            qty = int(obj.GetDataValue(7, i))
            avg_price = float(obj.GetDataValue(17, i))
            break

    return {
        "cash": cash,
        "qty": qty,
        "avg_price": avg_price
    }
