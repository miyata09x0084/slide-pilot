"""
Cloud Tasks クライアント

動画生成ジョブを Cloud Run Job にオフロードするためのタスク投入機能。
"""

import os
import json
from typing import Optional
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import datetime


# 環境変数から設定を取得
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "slide-pilot-474305")
GCP_LOCATION = os.getenv("GCP_LOCATION", "asia-northeast1")
CLOUD_TASKS_QUEUE = os.getenv("CLOUD_TASKS_QUEUE", "video-generation-queue")
VIDEO_JOB_URL = os.getenv("VIDEO_JOB_URL")  # Cloud Run Job のトリガーURL


def create_video_generation_task(
    slide_id: str,
    user_id: str,
    slide_md: str,
    title: str,
    delay_seconds: int = 0
) -> Optional[str]:
    """
    動画生成タスクを Cloud Tasks に投入

    Args:
        slide_id: スライドID（Supabase）
        user_id: ユーザーID
        slide_md: スライドのMarkdown内容
        title: スライドタイトル
        delay_seconds: 遅延秒数（デフォルト: 0）

    Returns:
        タスク名（成功時）、None（失敗時またはローカル環境）
    """
    # ローカル開発環境ではスキップ
    if os.getenv("LANGGRAPH_DEPLOYMENT_ID", "local") == "local":
        print("[cloud_tasks] Skipping task creation in local environment")
        return None

    # VIDEO_JOB_URL が未設定の場合はスキップ
    if not VIDEO_JOB_URL:
        print("[cloud_tasks] VIDEO_JOB_URL not set, skipping task creation")
        return None

    try:
        client = tasks_v2.CloudTasksClient()

        # キューのフルパス
        parent = client.queue_path(GCP_PROJECT_ID, GCP_LOCATION, CLOUD_TASKS_QUEUE)

        # タスクペイロード
        payload = {
            "slide_id": slide_id,
            "user_id": user_id,
            "slide_md": slide_md,
            "title": title
        }

        # HTTP リクエストタスク
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": VIDEO_JOB_URL,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode()
            }
        }

        # 遅延実行の設定
        if delay_seconds > 0:
            d = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(d)
            task["schedule_time"] = timestamp

        # タスク作成
        response = client.create_task(parent=parent, task=task)
        print(f"[cloud_tasks] Created task: {response.name}")
        return response.name

    except Exception as e:
        print(f"[cloud_tasks] Failed to create task: {str(e)}")
        return None
