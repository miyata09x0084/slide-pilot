"""
スライドダウンロード & Supabase統合ルーター

Issue #24: ブラウザプレビュー + Supabase履歴管理
Issue #29: Supabase Storage移行
Issue: Supabase Auth統合
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from typing import Dict, Any

from app.core.supabase import get_supabase_client, get_slides_by_user, get_slide_by_id
from app.auth.middleware import verify_token

router = APIRouter()

# サンプルスライド用の固定ユーザーID
SAMPLE_USER_ID = "00000000-0000-0000-0000-000000000000"


# ──────────────────────────────────────────────────────────────
# サンプルスライド（認証不要）
# ──────────────────────────────────────────────────────────────

@router.get("/samples")
async def get_samples() -> Dict[str, Any]:
    """サンプルスライド一覧を取得（認証不要）

    user_id = 00000000-0000-0000-0000-000000000000 のスライドを動的に取得
    RLSポリシーで全員アクセス可能に設定済み

    Returns:
        {"samples": [...]}
    """
    client = get_supabase_client()
    if not client:
        return {"samples": []}

    response = (
        client.table("slides")
        .select("id, title, topic, created_at, pdf_url, video_url")
        .eq("user_id", SAMPLE_USER_ID)
        .order("created_at", desc=True)
        .execute()
    )

    return {"samples": response.data}


# ──────────────────────────────────────────────────────────────
# Supabase統合エンドポイント（Issue #24）
# ──────────────────────────────────────────────────────────────

@router.get("/slides")
async def list_slides(
    authenticated_user_id: str = Depends(verify_token),
    limit: int = 20
) -> Dict[str, Any]:
    """認証ユーザーのスライド一覧を取得

    認証: 必須（JWT）
    RLS: Supabase が自動的に user_id でフィルタ

    Args:
        authenticated_user_id: JWT検証で取得したユーザーID
        limit: 取得件数上限

    Returns:
        {"slides": [...], "message": str}
    """
    client = get_supabase_client()
    if not client:
        return {"slides": [], "message": "Supabase未設定"}

    slides = get_slides_by_user(authenticated_user_id, limit)
    return {"slides": slides, "message": f"{len(slides)}件のスライドを取得しました"}


@router.get("/slides/{slide_id}/markdown")
async def get_slide_markdown(
    slide_id: str,
    authenticated_user_id: str = Depends(verify_token)
) -> Dict[str, Any]:
    """スライドのMarkdownを取得（認証必須、RLSで保護）

    認証: 必須（JWT）
    RLS: Supabaseが自動的にuser_idでフィルタ
    例外: サンプルスライド（user_id = 00000000-...）は全員アクセス可能

    Args:
        slide_id: スライドID（UUID）
        authenticated_user_id: JWT検証で取得したユーザーID

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

    # サンプルスライド（user_id = 00000000-...）は全員アクセス可能
    is_sample = slide.get("user_id") == SAMPLE_USER_ID

    # RLS + 念のためユーザーID照合（サンプルスライドは除外）
    if not is_sample and slide.get("user_id") != authenticated_user_id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    return {
        "slide_id": slide["id"],
        "title": slide["title"],
        "markdown": slide["slide_md"],
        "created_at": slide["created_at"],
        "pdf_url": slide.get("pdf_url"),
        "video_url": slide.get("video_url")  # Video Narration Feature
    }


# ──────────────────────────────────────────────────────────────
# Supabase Storageダウンロード（Issue #29）
# ──────────────────────────────────────────────────────────────

@router.get("/slides/{user_id}/{filename}")
async def download_slide(
    user_id: str,
    filename: str,
    authenticated_user_id: str = Depends(verify_token)
):
    """スライドダウンロード（認証必須、user_id照合）

    認証: 必須（JWT）
    セキュリティ: URLのuser_idとJWTのuser_idを照合

    Args:
        user_id: URLパラメータのユーザーID
        filename: ファイル名（例: ai-latest-info_slidev.pdf）
        authenticated_user_id: JWT検証で取得したユーザーID

    Returns:
        署名付きURLへのリダイレクト

    Raises:
        HTTPException: user_id不一致時403エラー
    """
    # JWTから取得したuser_idとパスのuser_idを照合（セキュリティ Critical）
    if user_id != authenticated_user_id:
        raise HTTPException(
            status_code=403,
            detail="他のユーザーのファイルにはアクセスできません"
        )

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
