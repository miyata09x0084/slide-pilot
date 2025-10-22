"""
PDFアップロードAPI (Issue #17)
FastAPIを使用してPDFファイルをアップロードするエンドポイントを提供
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uuid
import shutil

app = FastAPI()

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# アップロードディレクトリの設定
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ファイルサイズ制限（100MB）
MAX_FILE_SIZE = 100 * 1024 * 1024


@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
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

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"ファイルサイズは100MB以下にしてください（現在: {file_size / 1024 / 1024:.2f}MB）"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="ファイルが空です")

    # 一意なファイル名を生成
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / unique_name

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


@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "ok",
        "upload_dir": str(UPLOAD_DIR),
        "upload_dir_exists": UPLOAD_DIR.exists()
    }


@app.delete("/api/uploads/{filename}")
async def delete_upload(filename: str):
    """アップロードされたファイルを削除"""
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    try:
        file_path.unlink()
        return {"status": "success", "message": "ファイルを削除しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル削除エラー: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PDF Upload API server on http://localhost:8001")
    print(f"📁 Upload directory: {UPLOAD_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8001)
