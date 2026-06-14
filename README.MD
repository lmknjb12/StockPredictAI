[PPO 기반 AI 주식 자동매매 시스템]
본 시스템은 32비트 대신증권 크레온 API와 64비트 PPO 강화학습 모델을 연동하여 실시간으로 모의주식 매매를 수행하는 멀티 프로세스 시스템입니다.

1. 시스템 구동 흐름도 
32비트 환경과 64비트 환경이 JSON 파일 교환을 통해 데이터를 주고받으며 유기적으로 작동합니다.

1. 핵심 파일별 기능 및 역할
[준비 및 학습 단계]
model.py

삼성전자의 과거 주가 데이터를 분석하여 강화학습의 기초가 되는 초기 모델을 생성합니다.

simulation.py

가상 매매 환경을 구축하여 사용자가 설정한 목표 수익률을 달성할 때까지 에이전트를 반복 학습시킵니다. 완료 시 최종 실전용 모델(final_ppo_model)을 출력합니다.

[실전 매매 단계 (상시 가동)]
launcher.py (마스터 스크립트)

전체 시스템의 메인 컨트롤러입니다. 실행 시 아래 4개의 서브 프로세스를 각각 독립된 콘솔 창으로 동시에 켜고 제어합니다.

creon_data.py (32bit) - [눈]

KRX 및 크레온 API를 통해 현재 주가와 매매 동향(수급)을 수집하고 market_data.json으로 저장합니다.

creon_ai.py (64bit) - [뇌]

PPO 모델을 로드하여 30초마다 시장을 분석한 뒤, 매매 판단을 내리고 action.json으로 명령을 하달합니다.

creon_order.py (32bit) - [손]

action.json을 읽어 즉시 시장가 주문을 실행합니다. 또한 장 마감 후 학습을 위해 매매 결과를 experience.json에 기록합니다.

train_update.py (64bit) - [진화]

장 마감 후 experience.json에 누적된 당일 매매 데이터를 바탕으로 AI 모델을 재학습(업데이트)합니다.

3. 운영자 체크리스트 (필수 요구사항)
계정 설정: 프로그램 구동 전, 각 서브 파일에 크레온 계좌번호가 정확히 입력되어 있어야 합니다.

로그인 세션: 대신증권 크레온 Plus가 관리자 권한으로 로그인되어 있어야 합니다.

인프라 환경: 모의투자가 실시간으로 진행되므로, 장 운영시간(09:00 ~ 15:30) 동안 컴퓨터와 인터넷이 상시 켜져 있어야 합니다.

[User Manual] PPO-Based AI Automated Stock Trading System
This framework is a multi-process automated trading system designed to connect the 32-bit Daishin Creon API with a 64-bit PPO reinforcement learning model for live simulated trading.

1. Core Component Functions
[Training Phase]
model.py: Generates the initial baseline model using historical price data of Samsung Electronics.

simulation.py: Trains the agent inside a virtual environment until it achieves the target return, outputting the production-ready final_ppo_model.

[Execution Phase (Controlled by launcher.py)]
launcher.py (Master): The main controller that simultaneously fires up and manages the following 4 sub-processes in separate console windows.

creon_data.py (32-bit): Collects live stock prices and investor supply/demand trends via KRX and Creon APIs, saving them into market_data.json.

creon_ai.py (64-bit): Runs the PPO model every 30 seconds to evaluate the market and writes trading commands into action.json.

creon_order.py (32-bit): Executes real-time market orders based on action.json and logs trading results into experience.json.

train_update.py (64-bit): Fine-tunes and updates the PPO model after market close using the data stored in experience.json.

2. Operational Requirements
Account Info: Valid Creon account numbers must be configured within the scripts prior to launch.

API Session: The Daishin Creon Plus handler must be active and running with Administrator privileges.

Uptime: The system requires 24/7 continuous PC operation and stable network connectivity during market hours (09:00 - 15:30) to execute trades seamlessly.