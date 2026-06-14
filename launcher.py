import subprocess
import time
import datetime
import os
from config import BASE_DIR, PYTHON_32, PYTHON_64

def run_py_program(python_path, script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    print(f"🔄 실행 중: {python_path} {script_path}")
    
    return subprocess.Popen(
        [python_path, script_path],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

def main():
    print("🚀 [StockPredictAI] 자동매매 시스템 마스터 시작")

    # 1. 32bit 파이썬으로 크레온 데이터 수집 실행
    data_proc = run_py_program(PYTHON_32, "scripts/creon_data.py")
    time.sleep(3)

    # 2. 32bit 파이썬으로 주문 시스템 실행
    order_proc = run_py_program(PYTHON_32, "scripts/creon_order.py")
    time.sleep(3)

    # 3. 64bit 파이썬으로 AI 추론 실행
    ai_proc = run_py_program(PYTHON_64, "scripts/creon_ai.py")
    time.sleep(3)

    print("✅ 장중 시스템 모든 프로세스 실행 완료")

    try:
        while True:
            now = datetime.datetime.now()

            # 15:40 이후 장후 학습 실행
            if now.hour == 15 and now.minute >= 40:
                print("🌙 장 마감 후 재학습 세션 시작")
                
                # 학습 프로세스는 완료될 때까지 대기
                train_script = os.path.join(BASE_DIR, "scripts/train_update.py")
                subprocess.run([PYTHON_64, train_script], cwd=BASE_DIR)
                
                print("🎉 오늘의 자동매매 및 학습 일정이 종료되었습니다.")
                
                # 프로세스 종료 시도 (선택 사항)
                data_proc.terminate()
                order_proc.terminate()
                ai_proc.terminate()
                break

            time.sleep(60)
    except KeyboardInterrupt:
        print("Stopping systems...")
        data_proc.terminate()
        order_proc.terminate()
        ai_proc.terminate()

if __name__ == "__main__":
    main()
