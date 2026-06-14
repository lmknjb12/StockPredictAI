import sys
import os
import time
import numpy as np
from datetime import datetime, time as dt_time
from stable_baselines3 import PPO

# root 경로를 sys.path에 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from config import MODEL_PATH, MARKET_DATA_FILE, ACTION_FILE, AI_INTERVAL, OBS_SIZE
from core.utils.common import setup_logger, atomic_write_json, load_json

# 로거 설정
logger = setup_logger("AI_Engine")

def market_open():
    now = datetime.now()
    if now.weekday() >= 5:  # 주말 제외
        return False
    t = now.time()
    # 한국 거래소 시간: 09:00 ~ 15:30
    return dt_time(9, 0) <= t <= dt_time(15, 30)

def make_observation(data):
    """
    FinRL StockTradingEnv 상태 벡터 구성 (17차원)
    Order: [cash, close, qty, indicators(14)]
    """
    if data is None:
        return np.zeros((1, OBS_SIZE), dtype=np.float32)

    obs = []
    # 1. 계좌 예수금
    obs.append(data["cash"])
    
    # 2. 현재가 (종목별)
    obs.append(data["close"])
    
    # 3. 보유 수량 (종목별)
    obs.append(data["qty"])
    
    # 4. 보조지표 (14개)
    indicators = data.get("indicators", [])
    for val in indicators:
        obs.append(val)
        
    # 차원 맞춤 및 패딩/자르기
    obs = np.array(obs, dtype=np.float32)
    if len(obs) < OBS_SIZE:
        obs = np.pad(obs, (0, OBS_SIZE - len(obs)))
    elif len(obs) > OBS_SIZE:
        obs = obs[:OBS_SIZE]
        
    return obs.reshape(1, -1)

def main():
    logger.info("🧠 AI 엔진 시작")
    
    if os.path.exists(MODEL_PATH):
        try:
            model = PPO.load(MODEL_PATH)
            logger.info(f"✅ PPO AI 모델 로드 완료 ({MODEL_PATH})")
        except Exception as e:
            logger.error(f"모델 로드 중 오류: {e}")
            model = None
    else:
        logger.warning(f"⚠️ 모델 파일({MODEL_PATH})을 찾을 수 없습니다. 무작위 추론 모드.")
        model = None

    last_cmd = None
    while True:
        try:
            if not market_open():
                if last_cmd != "OFF_HOURS":
                    logger.info("⏰ 장 운영시간 종료 (대기 모드)")
                    last_cmd = "OFF_HOURS"
                time.sleep(60)
                continue

            market = load_json(MARKET_DATA_FILE)
            if market is None:
                time.sleep(3)
                continue

            obs = make_observation(market)

            if model is not None:
                action, _ = model.predict(obs, deterministic=True)
                value = float(action[0])
            else:
                value = float(np.random.uniform(-1, 1))

            # Action Mapping
            if value > 0.3:
                cmd = "BUY"
            elif value < -0.3:
                cmd = "SELL"
            else:
                cmd = "HOLD"

            result = {
                "time": str(datetime.now()),
                "action": cmd,
                "target_ratio": float(max(0.0, min(1.0, (value + 1) / 2))),
                "state": obs.flatten().tolist()
            }

            if atomic_write_json(ACTION_FILE, result):
                if cmd != last_cmd:
                    logger.info(f"🧠 [AI 판단 변경] {last_cmd} -> {cmd} | 목표 비중: {result['target_ratio']:.2%}")
                    last_cmd = cmd
            else:
                logger.error("AI 판단 저장 실패")

        except Exception as e:
            logger.error(f"AI 추론 중 오류: {e}")
            time.sleep(3)

        time.sleep(AI_INTERVAL)

if __name__ == "__main__":
    main()
