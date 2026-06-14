import subprocess
import time
import datetime
import os
import shutil
from config import BASE_DIR, PYTHON_32, PYTHON_64

def compress_logs():
    """logs 폴더의 내용을 날짜와 시간 이름으로 압축 (원본 유지)"""
    logs_dir = os.path.join(BASE_DIR, "logs")
    archive_dir = os.path.join(BASE_DIR, "log_zip")
    
    if not os.path.exists(logs_dir) or not os.listdir(logs_dir):
        return

    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    # 압축 파일 이름 설정
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"logs_archive_{timestamp}"
    archive_path = os.path.join(archive_dir, archive_name)

    try:
        print(f"📦 로그 백업 중: {archive_dir}/{archive_name}.zip")
        shutil.make_archive(archive_path, 'zip', logs_dir)
        print(f"✅ 로그 백업 완료")
        
    except Exception as e:
        print(f"❌ 로그 압축 중 오류 발생: {e}")

def clear_existing_logs():
    """프로그램 시작 시 기존 로그 파일 내용 초기화"""
    logs_dir = os.path.join(BASE_DIR, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        return

    print("🧹 기존 로그 파일 초기화 중...")
    # 관리할 로그 파일 목록
    log_files = ["creon_data.log", "creon_ai.log", "creon_order.log", "trainer.log"]
    
    for filename in log_files:
        file_path = os.path.join(logs_dir, filename)
        try:
            # 파일이 없으면 생성, 있으면 내용 비우기
            with open(file_path, "w", encoding="utf-8") as f:
                f.truncate(0)
        except Exception as e:
            print(f"⚠️ {filename} 초기화 실패: {e}")

def run_py_program(python_path, script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    print(f"🔄 실행 중 (백그라운드): {python_path} {script_name}")

    # CREATE_NO_WINDOW를 사용하여 보조 콘솔 창이 뜨지 않게 설정
    return subprocess.Popen(
        [python_path, script_path],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW
    )


def main():
    print("🚀 [StockPredictAI] 자동매매 시스템 마스터 시작")
    
    # 시작 시 기존 로그 비우기
    clear_existing_logs()

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
                
                # 프로세스 종료
                data_proc.terminate()
                order_proc.terminate()
                ai_proc.terminate()
                
                # 종료 전 로그 압축 (원본 유지)
                compress_logs()
                break

            time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping systems...")
        data_proc.terminate()
        order_proc.terminate()
        ai_proc.terminate()
        
        # 종료 전 로그 압축 (원본 유지)
        compress_logs()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        input("\n종료하려면 엔터 키를 누르세요...")
