model.py를 실행하면 삼성전자 주가데이터를 학습한 initial, checkpoint 모델을 만듭니다
simulation.py는 가상 주식환경을 만들어 원하는 수익률이 나올때까지 학습하며 종종 checkpoint에 저장하고
완성이 되면 final ppo 모델로 만듬.

launcher.py는
creon_ai, creon_data, creon_order, train_update 파일들을 실행하며
몇가지 파일들은 크레온 계좌번호를 요구합니다. 이 4가지로 모의주식을 하며 creon plus 계정이 필요하고
컴퓨터로 상시 켜놔야 작동합니다. 4개로 나눈 이유는 creon이 32bit환경을 요구하고 ppo는 64bit환경을 요구해서
나누게 됨.

creon_ai:뇌 역할 ppo모델을 사용해 매매를 결정함 이는 action.json을 사용해 creon_order 파일에 명령을 내림.

creon_data: krx api, creon api를 활용해 현재 주가정보 매매동향 정보들을 수집한뒤 market_data.json으로 creon_ai 에서 처리 할 수 있게 데이터를 제공함.

creon_order: action.json을 기반으로 매매를 하며 추후 장이후 AI의 학습을 위한 데이터들을 experience.json으로 저장함

launcher.py를 실행해 구동가능. 