"""Supabase統合（スライド保存・取得）

Issue #24: ブラウザプレビュー + Supabase履歴管理
"""

from supabase import create_client, Client
from typing import Optional, Dict, List
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# シングルトン: プロセス内で1つのクライアントを再利用
_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Supabaseクライアントを返す（環境変数未設定時はNone）

    初回呼び出し時にクライアントを生成し、以降はキャッシュを返す。
    create_client()のHTTPセッション確立コスト（~100-300ms）を初回のみに抑える。

    Returns:
        Supabase Client or None（環境変数未設定時）
    """
    global _client

    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        return None

    try:
        _client = create_client(url, key)
        return _client
    except Exception as e:
        print(f"[supabase] Failed to create client: {e}")
        return None


def save_slide_to_supabase(
    user_id: str,
    title: str,
    topic: str,
    slide_md: str,
    pdf_url: Optional[str] = None
) -> Dict:
    """スライドをSupabase DBに保存（Storageアップロードは別で実施済み）

    Args:
        user_id: ユーザー識別子（emailなど）
        title: スライドタイトル
        topic: スライドのトピック（入力値）
        slide_md: Markdownコンテンツ
        pdf_url: PDFの公開URL（既にStorageにアップロード済み）

    Returns:
        成功時: {"slide_id": str, "pdf_url": str}
        失敗時: {"error": str}
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase not configured"}

    try:
        # DBにメタデータを保存（Storageアップロードは呼び出し元で実施済み）
        data = {
            "user_id": user_id,
            "title": title,
            "topic": topic,
            "slide_md": slide_md,
            "pdf_url": pdf_url  # 既にStorageにアップロード済みのURL
        }

        response = client.table("slides").insert(data).execute()

        if response.data and len(response.data) > 0:
            slide_record = response.data[0]
            return {
                "slide_id": slide_record["id"],
                "pdf_url": pdf_url
            }
        else:
            return {"error": "Failed to insert slide record"}

    except Exception as e:
        return {"error": f"Supabase save failed: {str(e)}"}


def get_slide_by_id(slide_id: str) -> Optional[Dict]:
    """スライドをIDで取得

    Args:
        slide_id: スライドID（UUID）

    Returns:
        スライドデータ or None
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = client.table("slides").select("*").eq("id", slide_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[supabase] Failed to get slide {slide_id}: {e}")
        return None


def get_slides_by_user(user_id: str, limit: int = 20) -> List[Dict]:
    """ユーザーのスライド一覧を取得

    Args:
        user_id: ユーザー識別子
        limit: 取得件数上限

    Returns:
        スライドリスト（作成日時降順）
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        response = (
            client.table("slides")
            .select("id, title, topic, created_at, pdf_url, video_url")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data if response.data else []
    except Exception as e:
        print(f"[supabase] Failed to get slides for {user_id}: {e}")
        return []


def update_slide_video_url(slide_id: str, video_url: str) -> Dict:
    """スライドのvideo_urlを更新（Video Narration Feature）

    Args:
        slide_id: スライドID（UUID）
        video_url: 動画の公開URL（Supabase Storage）

    Returns:
        成功時: {"success": True}
        失敗時: {"error": str}
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase not configured"}

    try:
        response = (
            client.table("slides")
            .update({"video_url": video_url})
            .eq("id", slide_id)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return {"success": True}
        else:
            return {"error": "Failed to update video_url"}

    except Exception as e:
        return {"error": f"Supabase update failed: {str(e)}"}


# ============================================================
# Video Jobs（非同期動画生成ジョブ管理）
# ============================================================

def create_video_job(
    slide_id: str,
    user_id: str,
    slides_json: List[Dict],
    audio_files: List[str],
    title: str
) -> Dict:
    """動画生成ジョブを作成

    Args:
        slide_id: スライドID（UUID）
        user_id: ユーザー識別子
        slides_json: スライドデータ（JSON）
        audio_files: 音声ファイルURLリスト
        title: スライドタイトル

    Returns:
        成功時: {"job_id": str}
        失敗時: {"error": str}
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase not configured"}

    try:
        import json
        data = {
            "slide_id": slide_id,
            "user_id": user_id,
            "status": "pending",
            "input_data": json.dumps({
                "slides_json": slides_json,
                "audio_files": audio_files,
                "title": title
            })
        }

        response = client.table("video_jobs").insert(data).execute()

        if response.data and len(response.data) > 0:
            return {"job_id": response.data[0]["id"]}
        else:
            return {"error": "Failed to create video job"}

    except Exception as e:
        return {"error": f"Supabase insert failed: {str(e)}"}


def get_video_job(job_id: str) -> Optional[Dict]:
    """動画生成ジョブを取得

    Args:
        job_id: ジョブID（UUID）

    Returns:
        ジョブデータ or None
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = client.table("video_jobs").select("*").eq("id", job_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[supabase] Failed to get video job {job_id}: {e}")
        return None


def update_video_job(job_id: str, status: str, video_url: Optional[str] = None, error_message: Optional[str] = None) -> Dict:
    """動画生成ジョブのステータスを更新

    Args:
        job_id: ジョブID（UUID）
        status: ステータス（pending, processing, completed, failed）
        video_url: 動画URL（completed時）
        error_message: エラーメッセージ（failed時）

    Returns:
        成功時: {"success": True}
        失敗時: {"error": str}
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase not configured"}

    try:
        update_data: Dict = {"status": status}
        if video_url:
            update_data["video_url"] = video_url
        if error_message:
            update_data["error_message"] = error_message

        response = (
            client.table("video_jobs")
            .update(update_data)
            .eq("id", job_id)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return {"success": True}
        else:
            return {"error": "Failed to update video job"}

    except Exception as e:
        return {"error": f"Supabase update failed: {str(e)}"}
