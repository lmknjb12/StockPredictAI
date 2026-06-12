import os
import numpy as np
from stable_baselines3 import PPO
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader
from finrl.meta.preprocessor.preprocessors import FeatureEngineer
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
from finrl.config import INDICATORS

#환경설정
TARGET_TICKER = ["AAPL"]
CHECKPOINT_MODEL_PATH = "ppo_model_checkpoint"
FINAL_MODEL_PATH = "ppo_model"
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
            return PPO.load(candidate, env=env_train)

    raise FileNotFoundError(
        "학습된 모델 파일이 없습니다. 먼저 model.py를 실행해 초기 모델을 생성해주세요."
    )

custom_indicators = INDICATORS + ["foreigner_net", "news_sentiment"]
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

#최근 주가 수집 및 전처리
print("[데이터 준비] 최신 주가 수집")
df_test = YahooDownloader(
    start_date="2026-01-01",
    end_date="2026-06-11",
    ticker_list=TARGET_TICKER,
).fetch_data()

df_test = df_test.sort_values(["date", "tic"]).reset_index(drop=True)
np.random.seed(100)  # 시험 데이터용 가상 변수 생성
df_test["foreigner_net"] = np.random.uniform(-5000, 5000, size=len(df_test))
df_test["news_sentiment"] = np.random.uniform(-1.0, 1.0, size=len(df_test))

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

# 훈련용 환경도 다시 재학습할 때를 위해 대기 세팅
df_train = YahooDownloader(
    start_date="2024-01-01",
    end_date="2026-01-01",
    ticker_list=TARGET_TICKER,
).fetch_data()
print(df_train.columns.tolist())
df_train = df_train.sort_values(["date", "tic"]).reset_index(drop=True)
np.random.seed(42)
df_train["foreigner_net"] = np.random.uniform(-5000, 5000, size=len(df_train))
df_train["news_sentiment"] = np.random.uniform(-1.0, 1.0, size=len(df_train))
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
    print("\n--------------------------------------------------")
    print(f"[시도 회차: {attempt_count}차] AI 성능분석")
    print("--------------------------------------------------")

    account_memory, _ = DRLAgent.DRL_prediction(model=current_model, environment=e_test_gym)

    initial_asset = 10000000
    final_asset = account_memory["account_value"].iloc[-1]
    total_return = ((final_asset - initial_asset) / initial_asset) * 100

    print(f"현재 AI 수익률: {total_return:.2f}%")

    if total_return >= TARGET_RETURN_CUTLINE:
        print(f"[합격] 목표 수익률({TARGET_RETURN_CUTLINE}%)을 달성")
        current_model.save(FINAL_MODEL_PATH)
        current_model.save(CHECKPOINT_MODEL_PATH)
        print(f"최종 모델이 '{FINAL_MODEL_PATH}.zip'으로 저장되었습니다.")
        is_passed = True
    else:
        print(f"[불합격] 성능이 기준치({TARGET_RETURN_CUTLINE}%)에 미달했습니다.")
        additional_steps = 10000 * attempt_count
        print(f"재학습: {additional_steps}번 더 강화학습")
        current_model.learn(total_timesteps=additional_steps, reset_num_timesteps=False)
        current_model.save(CHECKPOINT_MODEL_PATH)
        print(f"재학습 체크포인트가 '{CHECKPOINT_MODEL_PATH}.zip'로 자동 저장되었습니다.")
        attempt_count += 1

print("\n강화학습 완!")