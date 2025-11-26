# スライド画像生成の安定化設計

> 作成日: 2025-11-26
> ステータス: 承認済み

## 背景と問題

### 現状の問題
- **Slidev `export --format png`** で白紙画像が生成される不安定さ
- 現在のDockerfileにSlidevが含まれていない（2025-11-03に削除済み）
- Cloud Run本番環境で動画生成が失敗している状態

### 要件
- Cloud Run環境で動作すること
- LangGraphノードから同期呼び出し可能（asyncブロッキング問題回避）
- 安定した画像出力
- 高速なレンダリング（目標: <2秒/スライド）

---

## 技術選定

### 選定結果: HTML/CSS テンプレート + Playwright

| 要件 | 対応状況 |
|------|----------|
| Cloud Run対応 | ✅ Chromium対応Dockerイメージで実現 |
| LangGraph互換 | ✅ `sync_playwright()` 同期API使用 |
| 安定性 | ✅ 静的HTMLでビルドエラーなし |
| デバッグ容易性 | ✅ HTMLをブラウザで直接確認可能 |
| デザイン品質 | ✅ CSS自由度高い |

### 却下した選択肢

| 選択肢 | 却下理由 |
|--------|----------|
| Slidev継続 | 白紙出力が不安定、ビルドプロセス複雑 |
| Marp CLI | Slidevマークダウンと互換性なし |
| PIL/Pillow直接描画 | デザイン品質が低い、レイアウト実装が複雑 |
| 外部API (htmlcsstoimage.com) | ネットワーク依存、コスト、プライバシー |

---

## アーキテクチャ

### 処理フロー

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LLM出力        │     │  HTMLテンプレート │     │  Playwright     │
│  (構造化JSON)   │ ──▶ │  エンジン        │ ──▶ │  スクリーンショット │
│                 │     │                  │     │                 │
│ {               │     │ <html>           │     │ ┌─────────────┐ │
│   type: title   │     │   <style>...</style>│   │ │ PNG 1920x1080│ │
│   title: ...    │     │   <body>...</body>│    │ └─────────────┘ │
│   bullets: []   │     │ </html>          │     │                 │
│ }               │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### コンポーネント構成

```
backend/app/
├── core/
│   └── slide_renderer.py    # 新規: HTMLテンプレート + Playwright
├── prompts/
│   └── slide_prompts.py     # 変更: JSON出力形式に更新
└── agents/
    └── slide_workflow.py    # 変更: render_videoノードを新レンダラーに置換
```

---

## 実装詳細

### 1. SlideRenderer クラス

```python
# backend/app/core/slide_renderer.py
from playwright.sync_api import sync_playwright
from pathlib import Path
from typing import List, Dict

class SlideRenderer:
    """HTML/CSS + Playwright ベースのスライドレンダラー"""

    VIEWPORT = {'width': 1920, 'height': 1080}

    def __init__(self):
        self.templates = {
            'title': self._title_template,
            'content': self._content_template,
            'conversation': self._conversation_template,
        }

    def render_all(self, slides: List[Dict], output_dir: Path) -> List[Path]:
        """全スライドをPNG画像としてレンダリング"""
        output_dir.mkdir(parents=True, exist_ok=True)
        png_paths = []

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport=self.VIEWPORT)

            for i, slide in enumerate(slides):
                html = self._generate_html(slide)
                page.set_content(html)
                page.wait_for_load_state('networkidle')

                png_path = output_dir / f"{i+1}.png"
                page.screenshot(path=str(png_path))
                png_paths.append(png_path)

            browser.close()

        return png_paths

    def _generate_html(self, slide: Dict) -> str:
        """スライドデータからHTMLを生成"""
        slide_type = slide.get('type', 'content')
        template_fn = self.templates.get(slide_type, self._content_template)
        return template_fn(slide)
```

### 2. LLM出力形式（JSON）

```json
{
  "slides": [
    {
      "type": "title",
      "title": "AIの最新動向",
      "subtitle": "2024年11月版"
    },
    {
      "type": "content",
      "heading": "OpenAIの発表",
      "bullets": [
        "GPT-5の開発状況が明らかに",
        "Soraが一般公開開始",
        "APIの料金改定"
      ]
    },
    {
      "type": "conversation",
      "heading": "ポイント解説",
      "teacher": "今回の発表で最も重要なのは、GPT-5の能力向上です。",
      "student": "具体的にどんな点が改善されたんですか？"
    }
  ]
}
```

### 3. render_video ノード更新

```python
# backend/app/agents/slide_workflow.py (変更部分)

def render_video(state: State) -> Dict:
    """PNG画像 + 音声 → MP4動画生成"""
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    from app.core.slide_renderer import SlideRenderer

    # ... 前処理は既存コードと同じ ...

    # 変更点: Slidev → SlideRenderer
    renderer = SlideRenderer()
    slides_json = state.get("slides_json", [])

    png_dir = temp_dir / "slides_png"
    png_paths = renderer.render_all(slides_json, png_dir)

    if not png_paths:
        return {
            "error": "No PNG files generated",
            "log": _log(state, "[video] ERROR: SlideRenderer produced no images")
        }

    # ... 以降は既存のMoviePy処理と同じ ...
```

---

## Dockerfile変更

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Chromium依存パッケージ + 日本語フォント
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザインストール
RUN playwright install chromium

# アプリケーションコード
COPY ./app /app/app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 実装ステップ

### Phase 1: 基盤整備
1. `backend/requirements.txt` に `playwright>=1.49.0` 追加
2. `backend/Dockerfile` をChromium対応に更新
3. ローカルでPlaywright動作確認

### Phase 2: SlideRenderer実装
1. `backend/app/core/slide_renderer.py` 新規作成
2. HTMLテンプレート（title, content, conversation）実装
3. 単体テスト作成

### Phase 3: プロンプト変更
1. `backend/app/prompts/slide_prompts.py` 更新
2. LLM出力をSlidevマークダウン → 構造化JSONに変更
3. 出力形式の検証

### Phase 4: ワークフロー統合
1. `backend/app/agents/slide_workflow.py` の `render_video` ノード更新
2. State型に `slides_json` フィールド追加
3. エンドツーエンドテスト

### Phase 5: デプロイ
1. Cloud Runへデプロイ
2. コールドスタート時間計測
3. 本番動作確認

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| コンテナサイズ増加 (500MB → 1.2GB) | 許容範囲内、Cloud Runスペックで対応可能 |
| コールドスタート増加 | `min-instances=1` 設定で軽減 |
| Google Fontsネットワーク依存 | フォントプリロード、フォールバックフォント設定 |
| Playwright初期化時間 | ブラウザ起動を1回に集約（render_all内） |

---

## 期待される改善

| 指標 | 現状 (Slidev) | 改善後 |
|------|--------------|--------|
| 安定性 | ❌ 白紙出力発生 | ✅ 安定 |
| デバッグ | 難しい | 簡単（HTML直接確認） |
| 速度 | 2-10秒/スライド | 1-2秒/スライド |
| 依存関係 | Slidev + Playwright | Playwright のみ |
