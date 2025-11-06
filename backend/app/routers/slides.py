"""
スライドダウンロード & Supabase統合ルーター

Issue #24: ブラウザプレビュー + Supabase履歴管理
Issue #29: Supabase Storage移行
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from typing import Dict, Any

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
# Supabase Storageダウンロード（Issue #29）
# ──────────────────────────────────────────────────────────────

@router.get("/slides/{user_id}/{filename}")
async def download_slide(user_id: str, filename: str):
    """生成されたスライドをダウンロード（Supabase Storage）

    Args:
        user_id: ユーザーID（anonymousまたはemail）
        filename: ファイル名（例: ai-latest-info_slidev.pdf）

    Returns:
        署名付きURLへのリダイレクト
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage service unavailable")

    storage_path = f"{user_id}/{filename}"

    try:
        # 公開バケットなので直接公開URLを取得
        public_url = client.storage.from_("slide-files").get_public_url(storage_path)

        # 公開URLにリダイレクト
        return RedirectResponse(url=public_url)

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {storage_path}"
        )
