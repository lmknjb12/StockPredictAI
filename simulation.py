import os
from stable_baselines3 import PPO
from finrl.meta.preprocessor.preprocessors import FeatureEngineer
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
from finrl.config import INDICATORS

from data_utils import PYKRX_FEATURES, load_market_data

#환경설정
TARGET_TICKER = ["005930"]
CHECKPOINT_MODEL_PATH = "ppo_model_checkpoint"
FINAL_MODEL_PATH = "final_ppo_model"
INITIAL_MODEL_PATH = "initial_ppo_model"


def load_existing_model(env_train):
    candidate_paths = [
        CHECKPOINT_MODEL_PATH,
        f"{CHECKPOINT_MODEL_PATH}.zip",
        INITIAL_MODEL_PATH,
        f"{INITIAL_MODEL_PATH}.zip",
    ]

    for candidate in candidate_paths:
        if os.path.exists(candidate):
            print(f"저장된 모델을 불러옵니다: {candidate}")
            loaded_model = PPO.load(candidate, env=env_train)
            loaded_model.verbose = 0
            return loaded_model

    raise FileNotFoundError(
        "학습된 모델 파일이 없습니다. 먼저 model.py를 실행해 초기 모델을 생성해주세요."
    )

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
    "tech_indicator_list": custom_indicators,
}

print("[데이터 준비] 최신 주가 및 매매동향 수집")
df_test = load_market_data(
    start_date="2026-01-01",
    end_date="2026-06-11",
    ticker_list=TARGET_TICKER,
)

fe = FeatureEngineer(
    use_technical_indicator=True,
    tech_indicator_list=INDICATORS,
    use_vix=False,
    use_turbulence=False,
    user_defined_feature=False,
)
processed_test = fe.preprocess_data(df_test)

# 가상 환경 빌드
e_test_gym = StockTradingEnv(df=processed_test, **env_kwargs)
env_test, _ = e_test_gym.get_sb_env()

df_train = load_market_data(
    start_date="2024-01-01",
    end_date="2026-01-01",
    ticker_list=TARGET_TICKER,
)
print(df_train.columns.tolist())
processed_train = fe.preprocess_data(df_train)

e_train_gym = StockTradingEnv(df=processed_train, **env_kwargs)
env_train, _ = e_train_gym.get_sb_env()

# 강화학습
TARGET_RETURN_CUTLINE = 5.0
is_passed = False
attempt_count = 1

print("\n저장된 모델을 확인한 뒤 이어서 학습합니다...")
current_model = load_existing_model(env_train)

while not is_passed:
    print(f"학습 횟수: {attempt_count}차")

    account_memory, _ = DRLAgent.DRL_prediction(model=current_model, environment=e_test_gym)

    initial_asset = 10000000
    final_asset = account_memory["account_value"].iloc[-1]
    total_return = ((final_asset - initial_asset) / initial_asset) * 100

    if total_return >= TARGET_RETURN_CUTLINE:
        current_model.save(FINAL_MODEL_PATH)
        current_model.save(CHECKPOINT_MODEL_PATH)
        print(f"최종 모델이 '{FINAL_MODEL_PATH}.zip'으로 저장되었습니다.")
        is_passed = True
    else:
        additional_steps = 10000 * attempt_count
        current_model.learn(total_timesteps=additional_steps, reset_num_timesteps=False, progress_bar=False)
        current_model.save(CHECKPOINT_MODEL_PATH)
        attempt_count += 1

print("\n강화학습 완!")