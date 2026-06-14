import os

# =========================
# 프로젝트 기본 설정
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 종목 설정 (삼성전자)
TICKER = "A005930"

# 강화학습 설정
# 1 (cash) + 1 (price) + 1 (holdings) + 14 (indicators) = 17
OBS_SIZE = 17

# =========================
# 파일 경로 설정 (정리된 폴더 구조 반영)
# =========================
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

MARKET_DATA_FILE = os.path.join(DATA_DIR, "market_data.json")
ACTION_FILE = os.path.join(DATA_DIR, "action.json")
POSITION_FILE = os.path.join(DATA_DIR, "position.json")
EXPERIENCE_FILE = os.path.join(DATA_DIR, "experience.json")
ACCOUNT_FILE = os.path.join(DATA_DIR, "account.json")

MODEL_PATH = os.path.join(MODELS_DIR, "final_ppo_model.zip")
CHECKPOINT_MODEL_PATH = os.path.join(MODELS_DIR, "ppo_model_checkpoint")
INITIAL_MODEL_PATH = os.path.join(MODELS_DIR, "initial_ppo_model")

BACKUP_DIR = os.path.join(MODELS_DIR, "model_backup")

# =========================
# 실행 환경 설정
# =========================
# 사용자 환경에 맞게 수정 필요
PYTHON_32 = os.path.join(BASE_DIR, "creon_env", "Scripts", "python.exe")
PYTHON_64 = os.path.join(BASE_DIR, "64env", "Scripts", "python.exe")

# 실행 간격 (초)
DATA_INTERVAL = 10
AI_INTERVAL = 30
ORDER_CHECK_INTERVAL = 3

# =========================
# 매매 전략 및 리스크 관리
# =========================
STOP_LOSS_PCT = 0.03    # -3% 손절
TAKE_PROFIT_PCT = 0.07  # +7% 익절
MAX_DAILY_LOSS_PCT = 0.05 # 하루 최대 손실 제한

# 매매 제한 시간대
TRADING_HOURS = [
    ("09:00", "11:30"),
    ("14:00", "15:20")
]

# 시장 트렌드 필터
MARKET_FALL_LIMIT = -1.0 

# 수수료 및 슬리피지 설정
TRANSACTION_FEE = 0.002 

# =========================
# 보조지표 설정
# =========================
INDICATORS = [
    "macd", "boll_ub", "boll_lb", "rsi_30", 
    "cci_30", "dx_30", "close_30_sma", "close_60_sma"
]
PYKRX_FEATURES = [
    "foreigner_net_buy_value", "institution_net_buy_value", "individual_net_buy_value",
    "foreigner_trade_volume", "institution_trade_volume", "individual_trade_volume"
]
