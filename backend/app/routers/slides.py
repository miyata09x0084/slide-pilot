"""
スライドダウンロード & Supabase統合ルーター

Issue #24: ブラウザプレビュー + Supabase履歴管理
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, Any

from app.dependencies import get_slides_dir
from app.core.supabase import get_supabase_client, get_slides_by_user, get_slide_by_id

router = APIRouter()


# ──────────────────────────────────────────────────────────────
# Supabase統合エンドポイント（Issue #24）
# ──────────────────────────────────────────────────────────────

@router.get("/slides")
async def list_slides(user_id: str = "anonymous", limit: int = 20) -> Dict[str, Any]:
    """ユーザーのスライド一覧を取得（Supabase）

    Args:
        user_id: ユーザー識別子（デフォルト: "anonymous"）
        limit: 取得件数上限（デフォルト: 20）

    Returns:
        {"slides": [...], "message": str}
    """
    client = get_supabase_client()
    if not client:
        return {"slides": [], "message": "Supabase未設定"}

    slides = get_slides_by_user(user_id, limit)
    return {"slides": slides, "message": f"{len(slides)}件のスライドを取得しました"}


@router.get("/slides/{slide_id}/markdown")
async def get_slide_markdown(slide_id: str) -> Dict[str, Any]:
    """スライドのMarkdownを取得（Supabaseからプレビュー用）

    Args:
        slide_id: スライドID（UUID）

    Returns:
        {
            "slide_id": str,
            "title": str,
            "markdown": str,
            "created_at": str,
            "pdf_url": str | None
        }
    """
    slide = get_slide_by_id(slide_id)
    if not slide:
        raise HTTPException(status_code=404, detail="スライドが見つかりません")

    return {
        "slide_id": slide["id"],
        "title": slide["title"],
        "markdown": slide["slide_md"],
        "created_at": slide["created_at"],
        "pdf_url": slide.get("pdf_url")
    }


# ──────────────────────────────────────────────────────────────
# ローカルファイルダウンロード（既存機能）
# ──────────────────────────────────────────────────────────────

@router.get("/slides/{filename}")
async def download_slide(filename: str, slides_dir: Path = Depends(get_slides_dir)):
    """生成されたスライドをダウンロード（ローカルファイル）"""
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
