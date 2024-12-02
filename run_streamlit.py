import os
import subprocess
import sys

def ensure_streamlit_installed():
    """
    Streamlit이 설치되어 있지 않으면 pip를 사용하여 설치합니다.
    """
    try:
        import streamlit  # Streamlit 모듈 테스트
    except ImportError:
        print("Streamlit is not installed. Installing Streamlit...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("Streamlit installed successfully.")

def get_resource_path(relative_path):
    """
    PyInstaller에서 실행 파일 내부 리소스 경로를 계산합니다.
    """
    if hasattr(sys, '_MEIPASS'):  # PyInstaller 실행 환경
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

def run_streamlit():
    # Streamlit 설치 확인
    ensure_streamlit_installed()

    # front/main.py 경로 계산
    app_path = get_resource_path("front/main.py")

    # Streamlit 실행 명령어
    command = [sys.executable, "-m", "streamlit", "run", app_path]
    subprocess.run(command)

if __name__ == "__main__":
    run_streamlit()