import sys
import os
import shutil
from datetime import datetime
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO

# root 경로를 sys.path에 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from config import MODEL_PATH, EXPERIENCE_FILE, BACKUP_DIR, OBS_SIZE
from core.utils.common import setup_logger, load_json

# 로거 설정
logger = setup_logger("Trainer")

class StockExperienceEnv(gym.Env):
    """경험 데이터를 기반으로 한 간이 학습 환경"""
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.index = 0

        self.action_space = spaces.Box(low=-1, high=1, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(OBS_SIZE,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.index = 0
        return self.make_obs(), {}

    def make_obs(self):
        if self.index >= len(self.data):
            return np.zeros(OBS_SIZE, dtype=np.float32)

        state = self.data[self.index]["state"]
        state = np.array(state, dtype=np.float32)

        # 차원 맞춤 (OBS_SIZE=17)
        if len(state) < OBS_SIZE:
            state = np.pad(state, (0, OBS_SIZE - len(state)))
        elif len(state) > OBS_SIZE:
            state = state[:OBS_SIZE]

        return state

    def step(self, action):
        item = self.data[self.index]
        reward = item.get("reward", 0)

        # 다음 상태를 현재 아이템의 next_state에서 가져옴 (데이터 간 공백 대응)
        next_state = np.array(item.get("next_state", np.zeros(OBS_SIZE)), dtype=np.float32)
        if len(next_state) < OBS_SIZE:
            next_state = np.pad(next_state, (0, OBS_SIZE - len(next_state)))
        elif len(next_state) > OBS_SIZE:
            next_state = next_state[:OBS_SIZE]

        self.index += 1
        terminated = (self.index >= len(self.data))
        
        return next_state, reward, terminated, False, {}

def backup_model():
    if not os.path.exists(MODEL_PATH):
        return
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(MODEL_PATH, os.path.join(BACKUP_DIR, f"model_{timestamp}.zip"))
    logger.info("모델 백업 완료")

def train():
    data = load_json(EXPERIENCE_FILE)
    if not data or len(data) < 10:
        logger.info(f"📊 [학습 데이터 부족] 현재: {len(data) if data else 0} / 최소: 10")
        return

    # 평균 보상 및 데이터 상태 로그 (디버깅용)
    rewards = [d.get("reward", 0) for d in data]
    avg_reward = sum(rewards) / len(data)
    logger.info(f"📈 [데이터 점검] 수량: {len(data)}개 | 평균 수익률(로그): {avg_reward:.4f} | 위치: {EXPERIENCE_FILE}")

    backup_model()

    env = StockExperienceEnv(data)

    if os.path.exists(MODEL_PATH):
        logger.info("기존 모델 로드 후 추가 학습")
        model = PPO.load(MODEL_PATH, env=env)
    else:
        logger.info("새 모델 생성")
        model = PPO("MlpPolicy", env, verbose=1)

    # 학습 (데이터 양에 따라 스텝 조정 가능)
    steps = len(data) * 100 
    model.learn(total_timesteps=steps, reset_num_timesteps=False)
    
    model.save(MODEL_PATH)
    logger.info("학습 완료 및 모델 저장")

if __name__ == "__main__":
    logger.info("🌙 장후 재학습 시작")
    train()
    logger.info("✅ 종료")
