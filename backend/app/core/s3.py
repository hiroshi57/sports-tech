"""AWS S3 クライアント・Presigned URL 生成。

テスト時は boto3 の S3 クライアントを unittest.mock でパッチする。
本番では AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY を環境変数で渡す。
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

# ── 許可する MIME タイプ ────────────────────────────────────────────
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
)

# ── ファイルサイズ上限 ─────────────────────────────────────────────
MAX_FILE_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB

# Presigned URL 有効期限（秒）
PRESIGNED_URL_EXPIRES_SEC: int = 3600  # 1 時間


def _get_s3_client() -> Any:
    """boto3 S3 クライアントを返す（DI / モック差し替えの境界）。"""
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
    )


def build_s3_key(athlete_id: uuid.UUID, original_filename: str | None = None) -> str:
    """
    S3 オブジェクトキーを生成する。

    形式: videos/{athlete_id}/{YYYY-MM-DD}/{uuid}.{ext}
    """
    today = date.today().isoformat()
    ext = ""
    if original_filename and "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[-1].lower()
        # 許可する拡張子のみ（セキュリティ）
        if ext not in {".mp4", ".mov", ".avi", ".webm"}:
            ext = ".mp4"
    else:
        ext = ".mp4"

    return f"videos/{athlete_id}/{today}/{uuid.uuid4().hex}{ext}"


def generate_presigned_upload_url(
    s3_key: str,
    content_type: str = "video/mp4",
    expires_in: int = PRESIGNED_URL_EXPIRES_SEC,
) -> str:
    """
    S3 PUT 用 Presigned URL を生成する。

    クライアントはこの URL に直接 PUT リクエストを送ることで、
    サーバーを経由せずに S3 に動画をアップロードできる。

    Args:
        s3_key: S3 オブジェクトキー
        content_type: アップロードする動画の MIME タイプ
        expires_in: URL の有効期限（秒）

    Returns:
        Presigned PUT URL

    Raises:
        ClientError: S3 の設定に問題がある場合
    """
    client = _get_s3_client()
    url: str = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": s3_key,
            "ContentType": content_type,
            # ファイルサイズ上限はポリシーで制御する（Presigned URL では強制できない）
        },
        ExpiresIn=expires_in,
    )
    return url


def generate_presigned_download_url(
    s3_key: str,
    expires_in: int = PRESIGNED_URL_EXPIRES_SEC,
) -> str:
    """
    S3 GET 用 Presigned URL を生成する（動画再生用）。

    Args:
        s3_key: S3 オブジェクトキー
        expires_in: URL の有効期限（秒）

    Returns:
        Presigned GET URL
    """
    client = _get_s3_client()
    url: str = client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expires_in,
    )
    return url


def delete_s3_object(s3_key: str) -> None:
    """
    S3 オブジェクトを削除する（動画削除時に呼ぶ）。

    存在しないキーの削除は無視する（冪等）。
    """
    client = _get_s3_client()
    try:
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        # NoSuchKey はエラーとしない
        if error_code != "NoSuchKey":
            raise


def validate_mime_type(mime_type: str) -> bool:
    """許可された MIME タイプかどうか検証する。"""
    return mime_type in ALLOWED_MIME_TYPES


def validate_file_size(file_size_bytes: int) -> bool:
    """ファイルサイズが上限以内かどうか検証する。"""
    return 0 < file_size_bytes <= MAX_FILE_SIZE_BYTES
