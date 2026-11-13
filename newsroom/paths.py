"""기존 분석 저장소 데이터 경로 설정."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def processed_data_dir() -> Path:
    """명시한 DATA_DIR 또는 같은 project 폴더의 elder_accident를 사용."""
    configured = os.getenv("DATA_DIR")
    if configured:
        location = Path(configured).expanduser()
        return location if location.is_absolute() else ROOT_DIR / location
    sibling = ROOT_DIR.parent / "elder_accident" / "data" / "processed"
    return sibling if sibling.exists() else ROOT_DIR / "data" / "processed"
