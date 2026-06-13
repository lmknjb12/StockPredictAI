# creon_ai.py
import os
import json
import time
import numpy as np
from datetime import datetime, time as dt_time
from stable_baselines3 import PPO

MODEL_PATH = "final_ppo_model.zip"
MARKET_FILE = "market_data.json"
ACTION_FILE = "action.json"
INTERVAL = 30

# PPO 환경 상태 크기 고정
OBS_SIZE = 17

def market_open():
    now = datetime.now()
    if now.weekday() >= 5:  # 주말 제외
        return False
    t = now.time()
    return dt_time(9, 0) <= t <= dt_time(15, 30)

def load_market():
    # 데이터 수집 프로세스가 파일을 쓰는 도중 읽어서 터지는 것을 방지 (예외 처리 루프)
    for _ in range(5):
        try:
            if os.path.exists(MARKET_FILE):
                with open(MARKET_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.5)
    return None

def make_observation(data):
    if data is None:
        return np.zeros((1, OBS_SIZE), dtype=np.float32)

    obs = []
    # 1~2. 가격 및 거래량
    obs.append(data["close"])
    obs.append(data["volume"])

    # 3~7. 기술지표 (5개 고정)
    for x in data["indicators"]:
        obs.append(x)

    # 8~13. 수급 데이터 (순서 고정: 외, 기, 개 순매수 및 거래량 대치용)
    obs.append(data["foreigner"])     # 외국인 순매수 관련
    obs.append(data["institution"])   # 기관 순매수 관련
    obs.append(data["individual"])    # 개인 순매수 관련
    obs.append(0.0)                   # 데이터 정렬용 패딩 (외국인 거래량 대치)
    obs.append(0.0)                   # 데이터 정렬용 패딩 (기관 거래량 대치)
    obs.append(0.0)                   # 데이터 정렬용 패딩 (개인 거래량 대치)

    # 14~15. 계좌 상태
    obs.append(data["cash"])
    obs.append(data["stock_value"])

    obs = np.array(obs, dtype=np.float32)
    obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)

    # PPO 입력 크기(17) 최종 맞춤 및 형변환
    if len(obs) < OBS_SIZE:
        obs = np.pad(obs, (0, OBS_SIZE - len(obs)))
    elif len(obs) > OBS_SIZE:
        obs = obs[:OBS_SIZE]

    return obs.reshape(1, -1)

print("🧠 AI 엔진 시작")
if os.path.exists(MODEL_PATH):
    model = PPO.load(MODEL_PATH)
    print("✅ PPO AI 모델 로드 완료")
else:
    print(f"⚠️ 모델 파일({MODEL_PATH})을 찾을 수 없습니다. 임시 무작위 추론 모드로 작동합니다.")
    model = None

while True:
    try:
        if not market_open():
            print("⏰ 장 운영시간이 아닙니다. (대기 중...)")
            time.sleep(60)
            continue

        market = load_market()
        if market is None:
            print("⏳ market_data.json 생성을 기다리는 중...")
            time.sleep(3)
            continue

        obs = make_observation(market)

        if model is not None:
            action, _ = model.predict(obs, deterministic=True)
            value = float(np.array(action).flatten()[0])
        else:
            value = float(np.random.uniform(-1, 1))  # 모델 없을 시 샘플링

        # Continuous action: -1 ~ 1 매핑
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

        # 원자적(Atomic) 파일 쓰기: 임시 파일에 쓰고 이름을 바꾸어 Order 측과의 충돌 원천 차단
        tmp_action_file = ACTION_FILE + ".tmp"
        with open(tmp_action_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        os.replace(tmp_action_file, ACTION_FILE)

        print(f"🧠 [AI 분석] 판단: {cmd} | 목표 비중: {result['target_ratio']:.2%}")

    except Exception as e:
        print("🚨 AI 프로세스 오류:", e)

    time.sleep(INTERVAL)