from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """サービスの稼働状態を確認するエンドポイント。"""
    return {"status": "healthy"}
