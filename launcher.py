import subprocess
import time
import datetime
import os

# 현재 실행 중인 파일의 절대 경로 기준 설정
BASE = os.path.dirname(os.path.abspath(__file__))

# 💡 내 컴퓨터 환경에 맞는 파이썬 실행 파일(인터프리터) 경로 지정
# 가상환경(venv)을 쓰신다면 해당 가상환경 안의 python.exe 경로를 적어주셔야 합니다.
PYTHON_32 = r"./creon_env/Scripts/python.exe"  # 32비트 파이썬 경로
PYTHON_64 = r"./64env/Scripts/python.exe"  # 64비트 파이썬 경로

def run_py_program(python_path, script_path):
    full_script_path = os.path.normpath(os.path.join(BASE, script_path))
    print(f"🔄 실행 중: {python_path} {full_script_path}")
    
    # python.exe [스크립트파일.py] 형태로 실행합니다.
    return subprocess.Popen(
        [python_path, full_script_path],
        cwd=BASE,
        creationflags=subprocess.CREATE_NO_WINDOW  # 검은 창 안 뜨게 설정 보이게 하려면 CREATE_NEW_CONSOLE
    )

print("🚀 [PY 버전] 자동매매 시스템 마스터 시작")

# 1. 32bit 파이썬으로 크레온 데이터 수집 실행
data = run_py_program(PYTHON_32, "creon_data.py")
time.sleep(3)

# 2. 32bit 파이썬으로 주문 시스템 실행
order = run_py_program(PYTHON_32, "creon_order.py")
time.sleep(3)

# 3. 64bit 파이썬으로 AI 추론 실행
ai = run_py_program(PYTHON_64, "creon_ai.py")

print("✅ 장중 시스템 전 프로세스(.py) 실행 완료")

while True:
    now = datetime.datetime.now()

    # 15:40 이후 장후 학습 실행
    if now.hour == 15 and now.minute >= 40:
        print("🌙 장후 학습 시작")
        
        train_script = os.path.normpath(os.path.join(BASE, "train_update.py"))
        # 학습은 끝날 때까지 대기해야 하므로 subprocess.run 사용
        subprocess.run([PYTHON_64, train_script], cwd=BASE)
        
        print("🎉 오늘의 자동매매 및 학습 종료")
        break

    time.sleep(60)