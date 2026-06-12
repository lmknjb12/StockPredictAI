from finrl.meta.preprocessor.preprocessors import FeatureEngineer
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
from finrl.config import INDICATORS

from data_utils import PYKRX_FEATURES, load_market_data

# 모델 저장 경로
INITIAL_MODEL_PATH = "initial_ppo_model"
CHECKPOINT_MODEL_PATH = "ppo_model_checkpoint"

# 종목 및 지표 정의
TARGET_TICKER = ["005930"]
custom_indicators = INDICATORS + PYKRX_FEATURES
stock_dimension = len(TARGET_TICKER)
state_space = 1 + 2 * stock_dimension + len(custom_indicators) * stock_dimension

env_kwargs = {
    "stock_dim": stock_dimension,
    "hmax": 100,
    "initial_amount": 10000000, 
    "num_stock_shares": [0] * stock_dimension,
    "buy_cost_pct": [0.0015] * stock_dimension,
    "sell_cost_pct": [0.0015] * stock_dimension,
    "reward_scaling": 1e-4,
    "state_space": state_space,
    "action_space": stock_dimension,
    "tech_indicator_list": custom_indicators
}

print("과거 주가 및 매매동향 데이터 수집")
df_train = load_market_data(
    start_date="2024-01-01",
    end_date="2026-01-01",
    ticker_list=TARGET_TICKER,
)
print(df_train.columns.tolist())

# 보조지표 가공
fe = FeatureEngineer(
    use_technical_indicator=True, tech_indicator_list=INDICATORS,
    use_vix=False, use_turbulence=False, user_defined_feature=False
)
processed_train = fe.preprocess_data(df_train)

# 2. FinRL 강화학습 환경 구축
e_train_gym = StockTradingEnv(df=processed_train, **env_kwargs)
env_train, _ = e_train_gym.get_sb_env()

# 3. 최초 모델 생성 및 훈련
print("강화학습")
agent = DRLAgent(env=env_train)
model_ppo = agent.get_model("ppo")
trained_ppo = agent.train_model(
    model=model_ppo,
    tb_log_name="ppo",
    total_timesteps=30000
)

# 최초 가중치 파일 저장
trained_ppo.save(INITIAL_MODEL_PATH)
trained_ppo.save(CHECKPOINT_MODEL_PATH)
print(f"모델 생성 완료: {INITIAL_MODEL_PATH}.zip, {CHECKPOINT_MODEL_PATH}.zip")
