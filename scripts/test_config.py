import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import settings, LOG_FILE, DATA_DIR, LOG_DIR
print(f'DATA_DIR: {DATA_DIR}')
print(f'LOG_DIR: {LOG_DIR}')
print(f'LOG_FILE: {LOG_FILE}')
print(f'LOG_FILE exists: {LOG_FILE.exists()}')
print(f'Settings language: {settings.get("language")}')
print('config module imported successfully!')
print(f'LOG_DIR exists: {LOG_DIR.exists()}')
print(f'DATA_DIR exists: {DATA_DIR.exists()}')
