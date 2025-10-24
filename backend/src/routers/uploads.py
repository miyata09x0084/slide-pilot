"""
PDFアップロードルーター
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid
from dependencies import get_upload_dir, get_max_file_size

router = APIRouter()


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    upload_dir: Path = Depends(get_upload_dir),
    max_file_size: int = Depends(get_max_file_size)
):
    """
    PDFファイルをアップロードする

    Args:
        file: アップロードされたPDFファイル

    Returns:
        {
            "status": "success",
            "path": str (保存されたファイルパス),
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
            detail=f"ファイルサイズは100MB以下にしてください（現在: {file_size / 1024 / 1024:.2f}MB）"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="ファイルが空です")

    # 一意なファイル名を生成
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / unique_name

    # ファイルを保存
    try:
        with file_path.open("wb") as f:
            f.write(contents)

        return {
            "status": "success",
            "path": str(file_path),
            "filename": file.filename,
            "size": file_size
        }

    except Exception as e:
        # エラー時は作成されたファイルを削除
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"ファイル保存エラー: {str(e)}")


@router.delete("/uploads/{filename}")
async def delete_upload(filename: str, upload_dir: Path = Depends(get_upload_dir)):
    """アップロードされたファイルを削除"""
    file_path = upload_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    try:
        file_path.unlink()
        return {"status": "success", "message": "ファイルを削除しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル削除エラー: {str(e)}")
