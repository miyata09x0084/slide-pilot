"""
FastAPIメインアプリケーション

PDFアップロード、スライドダウンロード、ヘルスチェック、LangGraphプロキシのAPIを提供
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 設定とルーターのインポート
from app.config import settings
from app.routers import health, uploads, slides, agent, auth, feedback, video

# FastAPIアプリケーション作成
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録（/api プレフィックス付き）
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])
app.include_router(slides.router, prefix="/api", tags=["slides"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(video.router, prefix="/api/video", tags=["video"])


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Multimodal Lab API",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    print(f"🧪 Starting {settings.API_TITLE} on http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API docs available at http://{settings.HOST}:{settings.PORT}/docs")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
