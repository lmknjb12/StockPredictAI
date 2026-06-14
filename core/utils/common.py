import os
import json
import logging
from datetime import datetime

def setup_logger(name, log_file=None, level=logging.INFO):
    """표준 로거 설정"""
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

def atomic_write_json(file_path, data):
    """임시 파일을 사용하여 원자적으로 JSON 저장"""
    tmp_file = f"{file_path}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp_file, file_path)
        return True
    except Exception as e:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        return False

def load_json(file_path, default=None):
    """JSON 파일 안전하게 로드"""
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, PermissionError):
        return default
