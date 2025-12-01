"""
Cloud Run Jobs API Helper

本番環境でCloud Run Jobをトリガーするためのヘルパーモジュール。
gcloud CLIの代わりにGoogle Cloud Run Jobs APIを使用する。
"""

import os
from google.cloud import run_v2
from google.api_core import exceptions as google_exceptions


def trigger_video_job(job_id: str) -> bool:
    """
    Cloud Run Jobをトリガーして動画レンダリングを開始

    Args:
        job_id: video_jobsテーブルのジョブID（環境変数JOB_IDとして渡される）

    Returns:
        bool: トリガー成功時True、失敗時False

    Environment Variables:
        GCP_PROJECT_ID: GCPプロジェクトID（デフォルト: slide-pilot-474305）
        GCP_REGION: Cloud Runリージョン（デフォルト: asia-northeast1）
        VIDEO_JOB_NAME: Cloud Run Job名（デフォルト: slidepilot-video-job）

    Notes:
        - Application Default Credentials (ADC) を使用
        - Cloud Runサービスアカウントに `roles/run.developer` 権限が必要
        - ジョブ実行は非同期（この関数は即座にreturn）
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "slide-pilot-474305")
    region = os.environ.get("GCP_REGION", "asia-northeast1")
    job_name = os.environ.get("VIDEO_JOB_NAME", "slidepilot-video-job")

    job_resource_name = f"projects/{project_id}/locations/{region}/jobs/{job_name}"

    try:
        client = run_v2.JobsClient()

        # 環境変数オーバーライド（JOB_IDを渡す）
        # Note: dictionary形式でoverides_specを定義（RunJobRequestが受け入れる形式）
        override_spec = {
            'container_overrides': [{
                'env': [{'name': 'JOB_ID', 'value': job_id}]
            }]
        }

        request = run_v2.RunJobRequest(
            name=job_resource_name,
            overrides=override_spec
        )

        operation = client.run_job(request=request)
        print(f"[cloud_run] Triggered job execution for job_id: {job_id}")
        return True

    except google_exceptions.NotFound:
        print(f"[cloud_run] ERROR: Job '{job_name}' not found in {region}")
        print(f"[cloud_run] Resource name: {job_resource_name}")
        return False

    except google_exceptions.PermissionDenied as e:
        print(f"[cloud_run] ERROR: Permission denied. Service account needs 'roles/run.developer'")
        print(f"[cloud_run] Details: {e}")
        return False

    except Exception as e:
        print(f"[cloud_run] ERROR: Failed to trigger job: {type(e).__name__}: {e}")
        return False
