"""
サンプルスライドAPIルーター

新規ユーザーに使用イメージを提供するため、
事前に生成されたサンプルスライド一覧を返すエンドポイント。
"""
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

# サンプルスライドのメタデータ（静的定義）
SAMPLE_SLIDES: List[Dict] = [
    {
        "id": "sample-multilingual-ocr",
        "title": "多言語AIで文書解析",
        "pdf_path": "/samples/multilingual-ai-document-analysis_slidev.pdf",
        "md_path": "/samples/multilingual-ai-document-analysis_slidev.md",
        "created_at": "2025-01-15T00:00:00Z",
        "is_sample": True,
    },
    {
        "id": "sample-spatial-learning",
        "title": "2Dと3Dで学ぶ空間理解",
        "pdf_path": "/samples/learning-spatial-understanding-2d-3d_slidev.pdf",
        "md_path": "/samples/learning-spatial-understanding-2d-3d_slidev.md",
        "created_at": "2025-01-15T00:00:00Z",
        "is_sample": True,
    },
]


@router.get("/samples")
async def get_samples():
    """
    サンプルスライド一覧を取得

    Returns:
        サンプルスライドのメタデータリスト
        - id: サンプル識別子
        - title: スライドタイトル
        - pdf_path: PDF相対パス
        - md_path: Markdown相対パス
        - created_at: 作成日時（固定値）
        - is_sample: サンプルフラグ（常にTrue）
    """
    return {"samples": SAMPLE_SLIDES}
