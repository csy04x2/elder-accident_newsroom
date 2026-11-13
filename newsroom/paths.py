"""기존 elder_accident 가공 데이터 경로 설정. 파일 수집·복제는 하지 않습니다."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def processed_data_dir() -> Path:
    """DATA_DIR가 없으면 저장소 내부 data/processed를 가리킵니다."""
    configured = os.getenv("DATA_DIR", "data/processed")
    path = Path(configured).expanduser()
    return path if path.is_absolute() else ROOT_DIR / path
