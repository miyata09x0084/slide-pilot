"""
スライドダウンロードルーター
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from dependencies import get_slides_dir

router = APIRouter()


@router.get("/slides/{filename}")
async def download_slide(filename: str, slides_dir: Path = Depends(get_slides_dir)):
    """生成されたスライドをダウンロード"""
    file_path = slides_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="スライドが見つかりません")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
