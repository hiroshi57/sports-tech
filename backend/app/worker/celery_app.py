"""Celery アプリケーション設定。

起動方法:
    celery -A app.worker.celery_app worker --loglevel=info

broker / result backend はどちらも Redis を使用する。
テストでは CELERY_TASK_ALWAYS_EAGER=true で同期実行できる。
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sports_tech",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    # 分析ジョブは 1 動画 = 1 タスク。長時間ジョブなので prefetch を絞る
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # 動画分析のタイムアウト（ハード 15 分 / ソフト 12 分）
    task_time_limit=15 * 60,
    task_soft_time_limit=12 * 60,
    # テスト用: 同期実行モード
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=False,
)
