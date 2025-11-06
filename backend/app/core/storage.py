"""Supabase Storage操作ヘルパー

Issue #29: PDFストレージのSupabase移行
"""

from typing import Optional
from app.core.supabase import get_supabase_client


def upload_to_storage(
    bucket: str,
    file_path: str,
    file_data: bytes,
    content_type: str = "application/octet-stream"
) -> Optional[str]:
    """Supabase Storageにファイルをアップロード

    Args:
        bucket: バケット名（uploads or slide-files）
        file_path: ストレージパス（user_id/filename.pdf）
        file_data: ファイルバイナリ
        content_type: MIMEタイプ

    Returns:
        公開URL or 署名付きURL（uploadsバケットの場合は1時間有効）

    Raises:
        Exception: アップロード失敗時
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not configured")

    try:
        # アップロード（既存ファイルは上書き）
        client.storage.from_(bucket).upload(
            path=file_path,
            file=file_data,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        # slide-filesバケットは公開URL
        if bucket == "slide-files":
            return client.storage.from_(bucket).get_public_url(file_path)

        # uploadsバケットは署名付きURL（1時間有効）
        result = client.storage.from_(bucket).create_signed_url(file_path, 3600)
        return result["signedURL"]

    except Exception as e:
        print(f"[storage] Upload failed: {e}")
        raise


def download_from_storage(bucket: str, file_path: str) -> Optional[bytes]:
    """Supabase Storageからファイルをダウンロード

    Args:
        bucket: バケット名
        file_path: ストレージパス

    Returns:
        ファイルバイナリ（失敗時はNone）
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        return client.storage.from_(bucket).download(file_path)
    except Exception as e:
        print(f"[storage] Download failed: {e}")
        return None


def delete_from_storage(bucket: str, file_path: str) -> bool:
    """Supabase Storageからファイルを削除

    Args:
        bucket: バケット名
        file_path: ストレージパス

    Returns:
        成功: True、失敗: False
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        client.storage.from_(bucket).remove([file_path])
        return True
    except Exception as e:
        print(f"[storage] Delete failed: {e}")
        return False
