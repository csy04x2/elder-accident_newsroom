"""기사·검수·승인 API를 위한 최소 FastAPI 진입점."""
from fastapi import FastAPI

app = FastAPI(title="Elder Accident Newsroom API")


@app.get("/health")
def health() -> dict[str, str]:
    """서버 프로세스 응답만 확인하며 DB/외부 API의 정상 여부는 보장하지 않습니다."""
    return {"status": "ok"}
