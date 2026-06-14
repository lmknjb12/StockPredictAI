# train_update.py

import os
import json
import shutil
from datetime import datetime

import numpy as np

import gymnasium as gym

from gymnasium import spaces

from stable_baselines3 import PPO





# =========================
# 설정
# =========================


MODEL_PATH = "final_ppo_model.zip"

EXPERIENCE_FILE = "experience.json"

BACKUP_DIR = "model_backup"


TRAIN_STEP = 50000



OBS_SIZE = 17






# =========================
# 데이터 로드
# =========================


def load_experience():



    if not os.path.exists(
        EXPERIENCE_FILE
    ):

        print(
            "경험 데이터 없음"
        )

        return []



    with open(
        EXPERIENCE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)







# =========================
# Gym Environment
# =========================


class StockExperienceEnv(
    gym.Env
):


    def __init__(
        self,
        data
    ):


        super().__init__()


        self.data=data


        self.index=0



        self.action_space=spaces.Box(

            low=-1,

            high=1,

            shape=(1,),

            dtype=np.float32

        )



        self.observation_space=spaces.Box(

            low=-np.inf,

            high=np.inf,

            shape=(OBS_SIZE,),

            dtype=np.float32

        )






    def reset(
        self,
        seed=None,
        options=None
    ):


        super().reset(seed=seed)


        self.index=0



        obs=self.make_obs()



        return obs,{}







    def make_obs(self):


        if self.index >= len(self.data):

            return np.zeros(
                OBS_SIZE,
                dtype=np.float32
            )



        state=self.data[
            self.index
        ][
            "state"
        ]



        state=np.array(
            state,
            dtype=np.float32
        )



        if len(state)<OBS_SIZE:


            state=np.pad(

                state,

                (
                    0,
                    OBS_SIZE-len(state)
                )

            )


        elif len(state)>OBS_SIZE:


            state=state[:OBS_SIZE]



        return state






    def step(
        self,
        action
    ):


        item=self.data[
            self.index
        ]



        reward=float(
            item.get(
                "reward",
                0
            )
        )



        self.index+=1



        terminated=(

            self.index
            >=
            len(self.data)

        )



        obs=self.make_obs()



        return (

            obs,

            reward,

            terminated,

            False,

            {}

        )








# =========================
# 백업
# =========================


def backup():


    if not os.path.exists(
        BACKUP_DIR
    ):

        os.makedirs(
            BACKUP_DIR
        )



    name=datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )



    shutil.copy(

        MODEL_PATH,

        f"{BACKUP_DIR}/model_{name}.zip"

    )


    print(
        "모델 백업 완료"
    )








# =========================
# 학습
# =========================


def train():


    data=load_experience()



    if len(data)<5:


        print(
            "데이터 부족",
            len(data)
        )

        return




    print(
        "경험 개수:",
        len(data)
    )



    backup()



    env=StockExperienceEnv(
        data
    )




    if os.path.exists(
        MODEL_PATH
    ):


        print(
            "기존 모델 로드"
        )


        model=PPO.load(
            MODEL_PATH,
            env=env
        )


    else:


        print(
            "새 모델 생성"
        )


        model=PPO(

            "MlpPolicy",

            env,

            verbose=1

        )







    print(
        "PPO 추가 학습 시작"
    )



    model.learn(

        total_timesteps=TRAIN_STEP,

        reset_num_timesteps=False

    )




    model.save(
        MODEL_PATH
    )


    print(
        "학습 완료"
    )









if __name__=="__main__":


    print(
        "🌙 장후 재학습 시작"
    )


    train()


    print(
        "✅ 종료"
    )