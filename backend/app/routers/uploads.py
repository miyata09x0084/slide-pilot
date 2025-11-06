"""
PDFアップロードルーター

Issue #29: Supabase Storage移行対応
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import uuid
from app.dependencies import get_max_file_size
from app.core.storage import upload_to_storage

router = APIRouter()


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: str = "anonymous",
    max_file_size: int = Depends(get_max_file_size)
):
    """
    PDFファイルをSupabase Storageにアップロードする

    Args:
        file: アップロードされたPDFファイル
        user_id: ユーザー識別子（クエリパラメータ、デフォルト: "anonymous"）

    Returns:
        {
            "status": "success",
            "path": str (Storageパス),
            "url": str (署名付きURL、1時間有効),
            "filename": str (元のファイル名),
            "size": int (ファイルサイズ)
        }
    """
    # ファイル名の検証
    if not file.filename:
        raise HTTPException(status_code=400, detail="ファイル名がありません")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDFファイルのみアップロード可能です")

    # ファイルサイズの検証
    contents = await file.read()
    file_size = len(contents)

    if file_size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"ファイルサイズは50MB以下にしてください（現在: {file_size / 1024 / 1024:.2f}MB）"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="ファイルが空です")

    # 一意なファイル名を生成
    unique_name = f"{uuid.uuid4()}_{file.filename}"

    # Supabase Storageにアップロード
    storage_path = f"{user_id}/{unique_name}"

    try:
        signed_url = upload_to_storage(
            bucket="uploads",
            file_path=storage_path,
            file_data=contents,
            content_type="application/pdf"
        )

        return {
            "status": "success",
            "path": storage_path,      # Storageパス
            "url": signed_url,          # ダウンロード用URL（1時間有効）
            "filename": file.filename,
            "size": file_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルアップロード失敗: {str(e)}")


@router.delete("/uploads/{user_id}/{filename}")
async def delete_upload(user_id: str, filename: str):
    """Supabase Storageからアップロードファイルを削除

    Args:
        user_id: ユーザーID
        filename: ファイル名
    """
    from app.core.storage import delete_from_storage

    storage_path = f"{user_id}/{filename}"

    success = delete_from_storage(bucket="uploads", file_path=storage_path)

    if not success:
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    return {"status": "success", "message": "ファイルを削除しました"}
