"""
フィードバックAPI

スライドに対するユーザーフィードバック（評価・コメント）を収集
JSONファイルベースで実装（データベース不要）
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_feedback_dir
from app.auth.middleware import verify_token

router = APIRouter()


class FeedbackRequest(BaseModel):
    """フィードバックリクエスト"""
    slide_id: str = Field(..., description="スライドID")
    rating: int = Field(..., ge=1, le=5, description="評価（1-5）")
    comment: Optional[str] = Field(None, description="コメント（任意）")


class FeedbackResponse(BaseModel):
    """フィードバックレスポンス"""
    success: bool
    message: str
    feedback_id: str


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user_id: str = Depends(verify_token),
    feedback_dir: Path = Depends(get_feedback_dir)
):
    """
    フィードバックを送信

    - **slide_id**: 対象スライドのID
    - **rating**: 1-5の評価
    - **comment**: 自由記述コメント（任意）
    """
    try:
        # タイムスタンプ生成（ISO 8601形式、UTC）
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        # フィードバックデータ
        feedback_data = {
            "slide_id": request.slide_id,
            "user_id": user_id,
            "rating": request.rating,
            "comment": request.comment,
            "created_at": now.isoformat()
        }

        # ファイル名: {slide_id}_{timestamp}.json
        feedback_id = f"{request.slide_id}_{timestamp}"
        file_path = feedback_dir / f"{feedback_id}.json"

        # JSONファイルとして保存
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        return FeedbackResponse(
            success=True,
            message="フィードバックを送信しました",
            feedback_id=feedback_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"フィードバック保存エラー: {str(e)}")


@router.get("/feedback/{slide_id}")
async def get_feedback(
    slide_id: str,
    user_id: str = Depends(verify_token),
    feedback_dir: Path = Depends(get_feedback_dir)
):
    """
    スライドのフィードバック一覧を取得（管理者用）

    - **slide_id**: 対象スライドのID
    """
    try:
        # スライドIDで始まるフィードバックファイルを検索
        feedback_files = sorted(feedback_dir.glob(f"{slide_id}_*.json"), reverse=True)

        feedbacks = []
        for file_path in feedback_files:
            with open(file_path, "r", encoding="utf-8") as f:
                feedback = json.load(f)
                feedbacks.append(feedback)

        return {
            "slide_id": slide_id,
            "count": len(feedbacks),
            "feedbacks": feedbacks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"フィードバック取得エラー: {str(e)}")
