"""データベース接続・セッション管理。

engine と SessionLocal は起動時に一度だけ生成する。
FastAPI の DI で get_db() を使い、リクエストごとにセッションを払い出す。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite（テスト用）の場合は connect_args を追加
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: DB セッションを提供し、リクエスト完了後にクローズする。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
