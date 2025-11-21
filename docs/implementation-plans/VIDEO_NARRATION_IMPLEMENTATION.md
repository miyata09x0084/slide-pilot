# スライド動画化機能 実装計画書

**作成日**: 2025-11-21
**目的**: 静的スライド（PDF）を音声付き動画（MP4）に変換し、マルチモーダルな学習体験を提供
**ブランチ**: `feature/video-narration` (実装時に作成)

---

## 🎯 実装方針

### 基本原則
- **各ステップで必ず動作確認**してから次に進む（1ステップ=10-30分）
- **既存のPDF生成機能は維持**（後方互換性重視）
- **段階的リリース**: フラグ制御で動画生成ON/OFF可能

### 技術選定

| 用途 | 採用技術 | 理由 |
|-----|---------|------|
| **音声生成** | OpenAI TTS API (tts-1-hd) | ✅ 既存OpenAI契約で追加コスト最小（1動画4円）<br>✅ 最高品質の日本語音声（shimmer/alloy）<br>✅ 高速（1スライド1-2秒） |
| **動画生成** | MoviePy | ✅ Pythonネイティブ統合<br>✅ FFmpeg不要<br>✅ 画像+音声合成が簡単 |
| **画像生成** | Slidev PNG export | ✅ 既存Slidev環境を活用<br>✅ デザイン一貫性 |

### アーキテクチャ

```
既存フロー（保持）:
collect_info → ... → save_and_render_slidev (PDF保存) → END

新規フロー（追加）:
save_and_render_slidev → [VIDEO_ENABLED?]
                              ↓ YES
                         generate_narration → render_video → END
                              ↓
                         OpenAI TTS API (音声生成)
                              ↓
                         MoviePy (動画合成)
                              ↓
                         Supabase Storage (動画保存)
```

### コスト試算

**想定**: 5スライド × 200文字/スライド = 1,000文字

| モデル | 価格 | 1動画コスト |
|-------|------|-----------|
| tts-1 (標準) | $15/100万文字 | **$0.015** (約2円) |
| tts-1-hd (高品質) | $30/100万文字 | **$0.030** (約4円) |

→ **推奨**: tts-1-hd（高品質）で1動画4円、100動画でも400円

---

## 📋 Phase 1: 環境準備（30分）

### なぜ最初にやるか
- ✅ 依存関係エラーを早期発見
- ✅ OpenAI TTS/MoviePyの動作を単体確認
- ✅ 実装前に技術的リスクを排除

---

### Step 1.1: 依存関係インストール（10分）

**ファイル**: `backend/requirements.txt`

**追加内容**:
```bash
# ---動画生成（Video Narration Feature）---
moviepy>=1.0.3         # 動画生成（画像+音声合成）
pillow>=10.0.0         # 画像処理
```

**作業コマンド**:
```bash
cd backend
echo "" >> requirements.txt
echo "# ---動画生成（Video Narration Feature）---" >> requirements.txt
echo "moviepy>=1.0.3         # 動画生成（画像+音声合成）" >> requirements.txt
echo "pillow>=10.0.0         # 画像処理" >> requirements.txt

pip install -r requirements.txt
```

**成功基準**:
- ✅ `pip install`がエラーなく完了
- ✅ `moviepy`がインポート可能

**確認方法**:
```bash
python3 -c "import moviepy; print('MoviePy version:', moviepy.__version__)"
python3 -c "from PIL import Image; print('Pillow version:', Image.__version__)"
```

**期待出力**:
```
MoviePy version: 1.0.3
Pillow version: 10.x.x
```

**コミット**: `build: MoviePy/Pillow依存関係追加`

---

### Step 1.2: OpenAI TTS動作確認（10分）

**目的**: OpenAI APIキーが正しく設定され、TTS APIが動作することを確認

**テストスクリプト**: `backend/test_openai_tts.py`（一時ファイル）

```python
"""OpenAI TTS API動作確認スクリプト"""
from openai import OpenAI
import os
from pathlib import Path

# 環境変数からAPIキー取得
client = OpenAI()  # OPENAI_API_KEYから自動読み込み

# テスト音声生成
response = client.audio.speech.create(
    model="tts-1-hd",
    voice="shimmer",
    input="こんにちは。これはOpenAI TTSのテストです。自然な日本語音声が生成できています。"
)

# 音声ファイル保存
output_path = Path("test_tts_output.mp3")
response.stream_to_file(str(output_path))

print(f"✅ 音声ファイル生成成功: {output_path}")
print(f"ファイルサイズ: {output_path.stat().st_size / 1024:.2f} KB")
```

**実行コマンド**:
```bash
cd backend
python3 test_openai_tts.py
```

**成功基準**:
- ✅ `test_tts_output.mp3`が生成される
- ✅ ファイルサイズが10KB以上
- ✅ 音声ファイルが再生可能

**確認方法**:
```bash
# macOS
open test_tts_output.mp3

# Linux
mpg123 test_tts_output.mp3
```

**クリーンアップ**:
```bash
rm test_openai_tts.py test_tts_output.mp3
```

**エラー時の対処**:
- `openai.AuthenticationError` → `.env`の`OPENAI_API_KEY`を確認
- `ModuleNotFoundError: No module named 'openai'` → `pip install openai`

---

### Step 1.3: MoviePy動作確認（10分）

**目的**: MoviePyで画像+音声→動画生成が動作することを確認

**テストスクリプト**: `backend/test_moviepy.py`（一時ファイル）

```python
"""MoviePy動作確認スクリプト"""
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import tempfile

# 1. テスト画像生成（2枚）
temp_dir = Path(tempfile.mkdtemp())

for i in range(2):
    img = Image.new('RGB', (1920, 1080), color=(100 + i*50, 150, 200))
    draw = ImageDraw.Draw(img)

    # テキスト描画（フォントなしでシンプルに）
    text = f"スライド {i+1}"
    draw.text((960, 540), text, fill=(255, 255, 255))

    img.save(temp_dir / f"slide_{i}.png")

print(f"✅ テスト画像生成: {temp_dir}")

# 2. テスト音声生成（OpenAI TTS使用）
from openai import OpenAI
client = OpenAI()

audio_files = []
for i in range(2):
    response = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=f"これは{i+1}枚目のスライドです。"
    )
    audio_path = temp_dir / f"audio_{i}.mp3"
    response.stream_to_file(str(audio_path))
    audio_files.append(str(audio_path))

print(f"✅ テスト音声生成: {len(audio_files)}ファイル")

# 3. MoviePyで動画生成
clips = []
for i in range(2):
    img_clip = ImageClip(str(temp_dir / f"slide_{i}.png"))
    audio_clip = AudioFileClip(audio_files[i])

    # 音声の長さに合わせて画像を表示
    video_clip = img_clip.set_duration(audio_clip.duration).set_audio(audio_clip)
    clips.append(video_clip)

# 結合
final_video = concatenate_videoclips(clips, method="compose")
output_path = temp_dir / "test_video.mp4"
final_video.write_videofile(
    str(output_path),
    fps=24,
    codec="libx264",
    audio_codec="aac",
    verbose=False,
    logger=None
)

print(f"✅ 動画生成成功: {output_path}")
print(f"ファイルサイズ: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
print(f"動画時間: {final_video.duration:.1f}秒")
```

**実行コマンド**:
```bash
cd backend
python3 test_moviepy.py
```

**成功基準**:
- ✅ `test_video.mp4`が生成される
- ✅ 動画時間が5秒前後
- ✅ 動画が再生可能（映像+音声）

**確認方法**:
```bash
# macOS
open /tmp/*/test_video.mp4

# Linux
vlc /tmp/*/test_video.mp4
```

**クリーンアップ**:
```bash
rm test_moviepy.py
rm -rf /tmp/tmp*  # 一時ファイル削除
```

**エラー時の対処**:
- `ImageMagick is not installed` → `brew install imagemagick` (macOS) / `apt install imagemagick` (Linux)
- `ffmpeg not found` → `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux)

---

## 📋 Phase 2: ナレーション生成ノード実装（2時間）

### なぜこのフェーズか
- ✅ 動画生成の最も重要な部分（音声品質が成否を決める）
- ✅ 単体テストが可能（PNG画像不要）
- ✅ LangGraphフロー統合前に動作確認

---

### Step 2.1: ナレーション台本生成プロンプト作成（30分）

**ファイル**: `backend/app/prompts/narration_prompts.py`（新規作成）

```python
"""ナレーション台本生成プロンプト"""

# システムプロンプト
NARRATION_SYSTEM = """あなたはプレゼンテーションのナレーション原稿を作成する専門家です。

# 役割
スライドの内容を、聞き手に分かりやすく伝える自然な日本語ナレーション原稿を作成してください。

# 制約条件
- 読み上げ時間: 15-25秒（150-250文字）
- 口語体で自然な話し言葉
- 専門用語には簡単な補足説明を追加
- 箇条書きは文章に変換
- 絵文字・記号は読み上げしない
"""

# ユーザープロンプト
NARRATION_USER = """以下のスライド内容から、ナレーション原稿を作成してください。

## スライド内容
{slide_content}

## 出力形式
ナレーション原稿のみを出力してください（説明文不要）。

例:
「このスライドでは、LangGraphを使ったAIエージェントの構築方法を紹介します。LangGraphは、複数のAI処理を連携させるためのフレームワークです。」
"""


def get_narration_prompt(slide_content: str) -> list:
    """ナレーション台本生成プロンプト取得

    Args:
        slide_content: スライドのMarkdown内容（500文字まで）

    Returns:
        LangChain形式のプロンプト
    """
    return [
        ("system", NARRATION_SYSTEM),
        ("user", NARRATION_USER.format(slide_content=slide_content[:500]))
    ]
```

**成功基準**:
- ✅ ファイルが作成される
- ✅ Pythonのインポートエラーなし

**確認方法**:
```bash
python3 -c "from app.prompts.narration_prompts import get_narration_prompt; print('✅ Import OK')"
```

**コミット**: `feat(prompts): ナレーション台本生成プロンプト追加`

---

### Step 2.2: ナレーション生成ノード実装（1時間）

**ファイル**: `backend/app/agents/slide_workflow.py`

**追加位置**: `save_and_render_slidev`関数の後（行832付近）

```python
# -------------------
# Node G: ナレーション生成（OpenAI TTS）
# -------------------
@traceable(run_name="g_generate_narration")
def generate_narration(state: State) -> Dict:
    """各スライドのナレーション音声を生成（OpenAI TTS）"""
    from openai import OpenAI
    from app.prompts.narration_prompts import get_narration_prompt

    if state.get("error"):
        return {}

    slide_md = state.get("slide_md", "")
    title = state.get("title", "AIスライド")

    # Slidevのスライド区切り（---）で分割
    slides = slide_md.split("\n---\n")

    # frontmatter（最初のYAML部分）をスキップ
    slide_contents = []
    for slide in slides[1:]:  # slides[0]はfrontmatter
        # 空白・コメント行を除去
        content = "\n".join([
            line for line in slide.split("\n")
            if line.strip() and not line.strip().startswith("<!--")
        ])
        if content.strip():
            slide_contents.append(content)

    if not slide_contents:
        return {
            "error": "No slide content found for narration",
            "log": _log(state, "[narration] ERROR: no valid slides")
        }

    # OpenAI TTSクライアント初期化
    client = OpenAI()  # OPENAI_API_KEYから自動認証

    # 設定値取得
    from app.config import settings
    tts_model = getattr(settings, 'TTS_MODEL', 'tts-1-hd')
    tts_voice = getattr(settings, 'TTS_VOICE', 'shimmer')
    tts_speed = float(getattr(settings, 'TTS_SPEED', '1.0'))

    # 一時ディレクトリ作成
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())

    audio_files = []
    narrations = []

    try:
        for i, slide_content in enumerate(slide_contents):
            # LLMでナレーション台本生成
            prompt = get_narration_prompt(slide_content=slide_content)

            try:
                msg = llm.invoke(prompt)
                narration_text = msg.content.strip()

                # 前後の引用符を除去
                narration_text = narration_text.strip('"').strip("'")

                narrations.append(narration_text)
            except Exception as e:
                # LLMエラー時はスライド内容をそのまま使用
                narrations.append(f"{i+1}枚目のスライドです。")
                print(f"[narration] LLM error for slide {i}: {str(e)[:100]}")

            # OpenAI TTSで音声生成
            try:
                response = client.audio.speech.create(
                    model=tts_model,
                    voice=tts_voice,
                    input=narrations[-1],
                    speed=tts_speed
                )

                # 音声ファイル保存
                audio_path = temp_dir / f"narration_{i:03d}.mp3"
                response.stream_to_file(str(audio_path))
                audio_files.append(str(audio_path))

            except Exception as e:
                return {
                    "error": f"OpenAI TTS error: {str(e)}",
                    "log": _log(state, f"[narration] TTS API failed at slide {i}: {str(e)[:100]}")
                }

        return {
            "narration_scripts": narrations,
            "audio_files": audio_files,
            "_temp_narration_dir": str(temp_dir),  # 後続ノードで使用
            "log": _log(state, f"[narration] generated {len(audio_files)} audio files (model={tts_model}, voice={tts_voice})")
        }

    except Exception as e:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "error": f"narration_error: {str(e)}",
            "log": _log(state, f"[narration] EXCEPTION {str(e)[:100]}")
        }
```

**State型定義を更新**: `backend/app/agents/slide_workflow.py`（行64-128）

```python
class State(TypedDict, total=False):
    # ... 既存フィールド ...

    # ══════════════════════════════════════════════════════════
    # 動画生成 (Node G-H) - Video Narration Feature
    # ══════════════════════════════════════════════════════════
    narration_scripts: List[str]              # ナレーション台本
    audio_files: List[str]                    # 音声ファイルパス
    video_url: str                            # Supabase動画URL
    _temp_narration_dir: str                  # 一時ディレクトリ（内部用）
```

**成功基準**:
- ✅ TypeScriptエラーなし
- ✅ `generate_narration`関数が定義される

**確認方法**:
```bash
cd backend
python3 -c "from app.agents.slide_workflow import generate_narration; print('✅ Import OK')"
```

**コミット**: `feat(agents): ナレーション生成ノード実装`

---

### Step 2.3: ナレーション生成単体テスト（30分）

**目的**: LangGraphフロー統合前に`generate_narration`関数を単体テスト

**テストスクリプト**: `backend/test_narration_node.py`（一時ファイル）

```python
"""ナレーション生成ノード単体テスト"""
from app.agents.slide_workflow import generate_narration, State
from pathlib import Path

# テスト用Stateを作成
test_state: State = {
    "slide_md": """---
theme: apple-basic
---

# AIエージェント入門

LangGraphを使った実装方法

---

## LangGraphとは

LangGraphは、複数のAI処理を連携させるフレームワークです。

- **ノードベース**: 各処理をノードとして定義
- **状態管理**: TypedDictで型安全な状態管理
- **柔軟なフロー**: 条件分岐・ループ対応

---

## 実装例

1. ノード定義
2. グラフ構築
3. 実行

簡単3ステップで完成！
""",
    "title": "AIエージェント入門",
    "error": "",
    "log": []
}

# ナレーション生成実行
result = generate_narration(test_state)

# 結果確認
if result.get("error"):
    print(f"❌ エラー: {result['error']}")
else:
    print(f"✅ ナレーション生成成功")
    print(f"生成数: {len(result.get('narration_scripts', []))}個")
    print(f"音声ファイル: {len(result.get('audio_files', []))}個")
    print()

    # 台本内容を表示
    for i, script in enumerate(result.get('narration_scripts', [])):
        print(f"--- スライド {i+1} ---")
        print(script)
        print()

    # 音声ファイル確認
    for audio_file in result.get('audio_files', []):
        audio_path = Path(audio_file)
        if audio_path.exists():
            print(f"✅ {audio_path.name}: {audio_path.stat().st_size / 1024:.1f} KB")
        else:
            print(f"❌ {audio_path.name}: ファイルが存在しません")

    # 音声ファイル再生（macOS）
    first_audio = result.get('audio_files', [])[0] if result.get('audio_files') else None
    if first_audio:
        print(f"\n再生テスト: {first_audio}")
        import subprocess
        subprocess.run(["open", first_audio])
```

**実行コマンド**:
```bash
cd backend
python3 test_narration_node.py
```

**成功基準**:
- ✅ 3個の台本が生成される
- ✅ 3個の音声ファイルが生成される
- ✅ 音声ファイルサイズが5KB以上
- ✅ 音声が再生可能（日本語音声）

**期待出力例**:
```
✅ ナレーション生成成功
生成数: 3個
音声ファイル: 3個

--- スライド 1 ---
このスライドでは、LangGraphを使ったAIエージェントの実装方法を紹介します。

--- スライド 2 ---
LangGraphは、複数のAI処理を連携させるフレームワークです。ノードベースで各処理を定義し、TypedDictで型安全な状態管理ができます。

--- スライド 3 ---
実装は簡単3ステップです。まずノードを定義し、グラフを構築し、最後に実行するだけで完成します。

✅ narration_000.mp3: 12.3 KB
✅ narration_001.mp3: 18.7 KB
✅ narration_002.mp3: 15.2 KB
```

**クリーンアップ**:
```bash
rm test_narration_node.py
```

**エラー時の対処**:
- `OpenAI API error` → `.env`の`OPENAI_API_KEY`を確認
- `narration_scripts`が空 → スライド分割ロジックを確認

**コミット**: （テストファイルはコミット不要）

---

## 📋 Phase 3: 動画レンダリングノード実装（2.5時間）

### なぜこのフェーズか
- ✅ Slidev PNG export + MoviePy統合
- ✅ Supabase Storage対応
- ✅ エンドツーエンドの動画生成フロー完成

---

### Step 3.1: Slidev PNG exportテスト（30分）

**目的**: Slidevが`--format png`でスライドを画像化できることを確認

**テストスライド**: `backend/test_slides.md`（一時ファイル）

```markdown
---
theme: apple-basic
---

# テストスライド 1

これは1枚目のスライドです。

---

## テストスライド 2

- 箇条書き1
- 箇条書き2
- 箇条書き3

---

### テストスライド 3

**最後のスライド**です。
```

**実行コマンド**:
```bash
cd backend
mkdir -p test_png_output

# Slidev PNG export実行
slidev export test_slides.md --output test_png_output/slide.png --format png
```

**成功基準**:
- ✅ `test_png_output/`に複数のPNGファイルが生成される
- ✅ ファイル名が`slide-1.png`, `slide-2.png`, `slide-3.png`
- ✅ 画像サイズが1920x1080（デフォルト）

**確認方法**:
```bash
ls -lh test_png_output/
file test_png_output/slide-1.png
```

**期待出力**:
```
slide-1.png  slide-2.png  slide-3.png
test_png_output/slide-1.png: PNG image data, 1920 x 1080, 8-bit/color RGB, non-interlaced
```

**クリーンアップ**:
```bash
rm -rf test_slides.md test_png_output/
```

**エラー時の対処**:
- `slidev: command not found` → `npm install -g @slidev/cli`
- `Playwright not found` → `npx playwright install chromium`
- タイムアウトエラー → `--timeout 120000`オプション追加

---

### Step 3.2: 動画レンダリングノード実装（1.5時間）

**ファイル**: `backend/app/agents/slide_workflow.py`

**追加位置**: `generate_narration`関数の後（行900付近）

```python
# -------------------
# Node H: 動画レンダリング（MoviePy）
# -------------------
@traceable(run_name="h_render_video")
def render_video(state: State) -> Dict:
    """PNG画像 + 音声 → MP4動画生成"""
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

    if state.get("error"):
        return {}

    audio_files = state.get("audio_files", [])
    temp_narration_dir = state.get("_temp_narration_dir")
    title = state.get("title", "AIスライド")
    user_id = state.get("user_id", "anonymous")

    if not audio_files:
        return {
            "error": "No audio files for video rendering",
            "log": _log(state, "[video] ERROR: no audio files")
        }

    # 一時ディレクトリ作成
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 1. スライドファイル名の英語表記を生成（既存ロジック再利用）
        from app.prompts.slide_prompts import get_slug_prompt
        slug_prompt = get_slug_prompt(title=title)

        try:
            emsg = llm.invoke(slug_prompt)
            file_stem = _slugify_en(emsg.content.strip()) or _slugify_en(title)
        except Exception:
            file_stem = _slugify_en(title) or "ai-slide"

        # 2. Markdownを一時ファイルに保存（PNG export用）
        slide_md = state.get("slide_md", "")
        slide_md_path = temp_dir / f"{file_stem}_slidev.md"
        slide_md_path.write_text(slide_md, encoding="utf-8")

        # 3. Slidev → PNG画像シーケンス生成
        png_dir = temp_dir / "slides_png"
        png_dir.mkdir(exist_ok=True)

        slidev = shutil.which("slidev")
        if not slidev:
            return {
                "error": "slidev command not found",
                "log": _log(state, "[video] ERROR: slidev-cli not installed")
            }

        try:
            subprocess.run(
                ["slidev", "export", str(slide_md_path),
                 "--output", str(png_dir / "slide.png"),
                 "--format", "png",
                 "--timeout", "120000"],  # 2分タイムアウト
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=150  # プロセス全体のタイムアウト
            )
        except subprocess.TimeoutExpired:
            return {
                "error": "Slidev PNG export timeout",
                "log": _log(state, "[video] Slidev export timeout (150s)")
            }
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return {
                "error": f"Slidev export failed: {error_msg[:200]}",
                "log": _log(state, f"[video] Slidev export error: {error_msg[:100]}")
            }

        # 4. PNG ファイル収集
        png_files = sorted(png_dir.glob("slide-*.png"))

        if not png_files:
            return {
                "error": "No PNG files generated by Slidev",
                "log": _log(state, "[video] ERROR: no PNG files found")
            }

        # 音声ファイル数とPNGファイル数が一致しない場合の警告
        if len(png_files) != len(audio_files):
            print(f"[video] WARNING: PNG count ({len(png_files)}) != audio count ({len(audio_files)})")
            # 少ない方に合わせる
            min_count = min(len(png_files), len(audio_files))
            png_files = png_files[:min_count]
            audio_files = audio_files[:min_count]

        # 5. MoviePyで画像+音声を合成
        clips = []

        for i, (png_path, audio_path) in enumerate(zip(png_files, audio_files)):
            try:
                img_clip = ImageClip(str(png_path))
                audio_clip = AudioFileClip(audio_path)

                # 音声の長さに合わせて画像を表示
                video_clip = img_clip.set_duration(audio_clip.duration).set_audio(audio_clip)
                clips.append(video_clip)

            except Exception as e:
                print(f"[video] WARNING: Failed to process slide {i}: {str(e)[:100]}")
                continue

        if not clips:
            return {
                "error": "No video clips created",
                "log": _log(state, "[video] ERROR: all clips failed")
            }

        # 6. 全スライドを結合
        final_video = concatenate_videoclips(clips, method="compose")
        video_path = temp_dir / f"{file_stem}_video.mp4"

        final_video.write_videofile(
            str(video_path),
            fps=24,  # 滑らかな動画（静止画でも24fps推奨）
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",  # 2Mbps（高品質）
            verbose=False,
            logger=None
        )

        # 7. Supabase Storageにアップロード
        video_url = None
        md_url = None

        try:
            # 動画ファイルをアップロード
            storage_path = f"{user_id}/{file_stem}_video.mp4"
            video_url = upload_to_storage(
                bucket="slide-files",
                file_path=storage_path,
                file_data=video_path.read_bytes(),
                content_type="video/mp4"
            )

            log_msg = f"[video] rendered {len(clips)} slides → MP4 ({video_path.stat().st_size / 1024 / 1024:.1f}MB, {final_video.duration:.1f}sec)"
            log_msg += f" | uploaded to {video_url}"

        except Exception as e:
            log_msg = f"[video] rendered locally but upload failed: {str(e)[:100]}"

        # 8. クリーンアップ
        shutil.rmtree(temp_dir, ignore_errors=True)
        if temp_narration_dir:
            shutil.rmtree(temp_narration_dir, ignore_errors=True)

        return {
            "video_url": video_url,
            "log": _log(state, log_msg)
        }

    except Exception as e:
        # クリーンアップ
        shutil.rmtree(temp_dir, ignore_errors=True)
        if temp_narration_dir:
            shutil.rmtree(temp_narration_dir, ignore_errors=True)

        return {
            "error": f"video_render_error: {str(e)}",
            "log": _log(state, f"[video] EXCEPTION {str(e)[:100]}")
        }
```

**成功基準**:
- ✅ TypeScriptエラーなし
- ✅ `render_video`関数が定義される

**確認方法**:
```bash
cd backend
python3 -c "from app.agents.slide_workflow import render_video; print('✅ Import OK')"
```

**コミット**: `feat(agents): 動画レンダリングノード実装`

---

### Step 3.3: 動画レンダリング単体テスト（30分）

**目的**: `generate_narration` + `render_video`の連携動作確認

**テストスクリプト**: `backend/test_video_pipeline.py`（一時ファイル）

```python
"""動画レンダリングパイプライン テスト"""
from app.agents.slide_workflow import generate_narration, render_video, State

# テスト用State
test_state: State = {
    "slide_md": """---
theme: apple-basic
---

# 動画テスト 1

これは動画生成のテストです。

---

## 動画テスト 2

- 音声付き
- 自動生成
- MP4形式

---

### 動画テスト 3

テスト完了！
""",
    "title": "動画生成テスト",
    "user_id": "test_user",
    "error": "",
    "log": []
}

print("=== Step 1: ナレーション生成 ===")
narration_result = generate_narration(test_state)

if narration_result.get("error"):
    print(f"❌ ナレーション生成エラー: {narration_result['error']}")
    exit(1)

print(f"✅ ナレーション生成成功: {len(narration_result['audio_files'])}ファイル")

# Stateを更新
test_state.update(narration_result)

print("\n=== Step 2: 動画レンダリング ===")
video_result = render_video(test_state)

if video_result.get("error"):
    print(f"❌ 動画レンダリングエラー: {video_result['error']}")
    exit(1)

print(f"✅ 動画レンダリング成功")
print(f"動画URL: {video_result.get('video_url', 'ローカルのみ')}")
print(f"ログ: {video_result.get('log', [])[-1] if video_result.get('log') else 'なし'}")

# 動画ファイル確認（Supabaseアップロード前のローカルファイル）
print("\n=== 動画ファイル確認 ===")
print("✅ パイプラインテスト完了")
```

**実行コマンド**:
```bash
cd backend
python3 test_video_pipeline.py
```

**成功基準**:
- ✅ ナレーション生成が成功（3ファイル）
- ✅ 動画レンダリングが成功
- ✅ `video_url`が生成される（Supabase URLまたはローカルパス）

**期待出力**:
```
=== Step 1: ナレーション生成 ===
✅ ナレーション生成成功: 3ファイル

=== Step 2: 動画レンダリング ===
✅ 動画レンダリング成功
動画URL: https://xxx.supabase.co/storage/v1/object/public/slide-files/test_user/video-generation-test_video.mp4
ログ: [video] rendered 3 slides → MP4 (2.3MB, 18.5sec) | uploaded to https://...

=== 動画ファイル確認 ===
✅ パイプラインテスト完了
```

**クリーンアップ**:
```bash
rm test_video_pipeline.py
```

**エラー時の対処**:
- `slidev command not found` → `npm install -g @slidev/cli`
- `MoviePy codec error` → `brew install ffmpeg` (macOS)
- `Supabase upload failed` → `.env`の`SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`を確認

**コミット**: （テストファイルはコミット不要）

---

## 📋 Phase 4: グラフ統合（1時間）

### なぜこのフェーズか
- ✅ 既存のスライド生成フローに動画生成を統合
- ✅ フラグ制御で段階的リリース可能
- ✅ エンドツーエンドのワークフロー完成

---

### Step 4.1: 環境変数設定追加（10分）

**ファイル1**: `backend/.env.example`（テンプレート更新）

```bash
# 既存の環境変数...

# =====================================
# 動画生成設定（Video Narration Feature）
# =====================================
VIDEO_ENABLED=true                # 動画生成ON/OFF（true/false）
TTS_MODEL=tts-1-hd               # OpenAI TTSモデル（tts-1/tts-1-hd）
TTS_VOICE=shimmer                # 音声（alloy/echo/fable/onyx/nova/shimmer）
TTS_SPEED=1.0                    # 読み上げ速度（0.25-4.0）
```

**ファイル2**: `backend/.env`（実際の設定）

```bash
# 既存の設定をコピー...

# 動画生成設定（新規追加）
VIDEO_ENABLED=true
TTS_MODEL=tts-1-hd
TTS_VOICE=shimmer
TTS_SPEED=1.0
```

**ファイル3**: `backend/app/config.py`（設定読み込み追加）

**追加位置**: 行32付近

```python
# 既存のMarp設定の後に追加

# =====================================
# 動画生成設定（Video Narration Feature）
# =====================================
VIDEO_ENABLED = os.getenv("VIDEO_ENABLED", "false").lower() == "true"
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1-hd")  # tts-1 / tts-1-hd
TTS_VOICE = os.getenv("TTS_VOICE", "shimmer")   # alloy/echo/fable/onyx/nova/shimmer
TTS_SPEED = os.getenv("TTS_SPEED", "1.0")       # 0.25-4.0
```

**成功基準**:
- ✅ `backend/.env`に設定が追加される
- ✅ Python から設定値が読み込める

**確認方法**:
```bash
cd backend
python3 -c "from app.core.config import VIDEO_ENABLED, TTS_MODEL, TTS_VOICE; print(f'VIDEO_ENABLED={VIDEO_ENABLED}, TTS_MODEL={TTS_MODEL}, TTS_VOICE={TTS_VOICE}')"
```

**期待出力**:
```
VIDEO_ENABLED=True, TTS_MODEL=tts-1-hd, TTS_VOICE=shimmer
```

**コミット**: `feat(config): 動画生成設定追加`

---

### Step 4.2: グラフノード・エッジ追加（30分）

**ファイル**: `backend/app/agents/slide_workflow.py`

**変更箇所1**: グラフノード追加（行836付近）

```python
# 既存のノード追加の後に追加
graph_builder.add_node("generate_narration", generate_narration)
graph_builder.add_node("render_video", render_video)
```

**変更箇所2**: 条件分岐関数追加（行693付近、`route_after_eval_slidev`の後）

```python
def route_after_save(state: State) -> str:
    """保存後の分岐: 動画生成フラグで判定"""
    from app.core.config import VIDEO_ENABLED

    # エラーがある場合はスキップ
    if state.get("error"):
        return END

    # フラグがONの場合は動画生成へ
    if VIDEO_ENABLED:
        return "generate_narration"

    # フラグがOFFの場合は終了（PDF生成のみ）
    return END
```

**変更箇所3**: エッジ定義変更（行846-860付近）

**既存**:
```python
graph_builder.add_edge("save_and_render_slidev", END)
```

**変更後**:
```python
# 条件分岐: 動画生成フラグで判定
graph_builder.add_conditional_edges(
    "save_and_render_slidev",
    route_after_save,
    {"generate_narration": "generate_narration", END: END}
)

# 動画生成フロー
graph_builder.add_edge("generate_narration", "render_video")
graph_builder.add_edge("render_video", END)
```

**成功基準**:
- ✅ TypeScriptエラーなし
- ✅ グラフが正しくコンパイルされる

**確認方法**:
```bash
cd backend
python3 -c "from app.agents.slide_workflow import graph; print('✅ Graph compiled successfully')"
```

**コミット**: `feat(agents): 動画生成ノードをグラフに統合`

---

### Step 4.3: エンドツーエンドテスト（20分）

**目的**: 実際のスライド生成フローで動画が生成されることを確認

**テストスクリプト**: `backend/test_e2e_video.py`（一時ファイル）

```python
"""エンドツーエンド動画生成テスト"""
from app.agents.slide_workflow import graph, State
from langgraph.graph import RunnableConfig

# テスト用初期State
init_state: State = {
    "topic": "LangGraphを使ったAIエージェント構築",
    "user_id": "test_user",
    "key_points": [],
    "toc": [],
    "slide_md": "",
    "score": 0.0,
    "subscores": {},
    "reasons": {},
    "suggestions": [],
    "risk_flags": [],
    "passed": False,
    "feedback": "",
    "title": "",
    "slide_path": "",
    "attempts": 0,
    "error": "",
    "log": [],
    "context_md": "",
    "sources": {}
}

config: RunnableConfig = {
    "run_name": "e2e_video_test",
    "tags": ["test", "video"],
    "recursive_limit": 60,
}

print("=== エンドツーエンド動画生成テスト開始 ===")
print("VIDEO_ENABLEDフラグを確認...")

from app.core.config import VIDEO_ENABLED
print(f"VIDEO_ENABLED = {VIDEO_ENABLED}")

if not VIDEO_ENABLED:
    print("❌ VIDEO_ENABLEDがfalseです。.envでtrueに設定してください。")
    exit(1)

print("\nスライド生成フロー実行中...")
result = graph.invoke(init_state, config=config)

print("\n=== 結果 ===")
if result.get("error"):
    print(f"❌ エラー: {result['error']}")
else:
    print(f"✅ タイトル: {result.get('title')}")
    print(f"✅ PDFパス: {result.get('slide_path')}")
    print(f"✅ 動画URL: {result.get('video_url', 'なし')}")

    # ログ表示（最後の5件）
    print("\n=== ログ（最新5件） ===")
    for log_entry in result.get('log', [])[-5:]:
        print(log_entry)

    # 動画生成の確認
    if result.get('video_url'):
        print("\n🎬 動画生成成功！")
    else:
        print("\n⚠️  動画URLが生成されませんでした（PDF生成のみ）")
```

**実行コマンド**:
```bash
cd backend
python3 test_e2e_video.py
```

**成功基準**:
- ✅ スライド生成が完了（エラーなし）
- ✅ `video_url`が生成される
- ✅ ログに`[narration]`と`[video]`エントリが存在

**期待出力**:
```
=== エンドツーエンド動画生成テスト開始 ===
VIDEO_ENABLEDフラグを確認...
VIDEO_ENABLED = True

スライド生成フロー実行中...

=== 結果 ===
✅ タイトル: LangGraphを使ったAIエージェント構築
✅ PDFパス: https://xxx.supabase.co/.../langgraph-ai-agent-building_slidev.pdf
✅ 動画URL: https://xxx.supabase.co/.../langgraph-ai-agent-building_video.mp4

=== ログ（最新5件） ===
[slides_slidev_pdf] generated (5423 chars) from 3 chunks with mechanical structure control
[supabase] saved slide_id=abc123
[narration] generated 5 audio files (model=tts-1-hd, voice=shimmer)
[video] rendered 5 slides → MP4 (3.2MB, 24.3sec) | uploaded to https://...

🎬 動画生成成功！
```

**クリーンアップ**:
```bash
rm test_e2e_video.py
```

**エラー時の対処**:
- `video_url`が`None` → ログで`[video]`エラーを確認
- `Supabase upload failed` → `.env`のSupabase設定を確認
- タイムアウト → `recursive_limit`を80に増やす

**コミット**: （テストファイルはコミット不要）

---

## 📋 Phase 5: フロントエンド対応（2時間）

### なぜこのフェーズか
- ✅ ユーザーが動画を視聴・ダウンロードできる
- ✅ PDF/動画の切り替えUI実装
- ✅ UX完成

---

### Step 5.1: API型定義更新（15分）

**ファイル**: `frontend/src/features/slide/api/getSlide.ts`（型定義追加）

**変更箇所**: `Slide`型に`video_url`フィールド追加（行5-15付近）

```typescript
export interface Slide {
  id: string;
  user_id: string;
  title: string;
  topic: string;
  slide_md: string;
  pdf_url: string | null;
  video_url: string | null;  // ← 追加
  created_at: string;
  updated_at: string;
}
```

**成功基準**:
- ✅ TypeScriptコンパイルエラーなし

**確認方法**:
```bash
cd frontend
npm run build
```

**コミット**: `feat(types): Slide型にvideo_url追加`

---

### Step 5.2: 動画プレビューコンポーネント実装（1時間）

**ファイル**: `frontend/src/features/slide/components/SlideContentViewer.tsx`

**変更箇所1**: State追加（行10付近）

```typescript
type ViewMode = 'pdf' | 'video';

export default function SlideContentViewer({ slide }: { slide: Slide }) {
  const [viewMode, setViewMode] = useState<ViewMode>('pdf');

  // 既存のコード...
```

**変更箇所2**: 切り替えボタン追加（行50付近、PDFビューアの前）

```typescript
{/* 表示モード切り替えボタン */}
{slide.video_url && (
  <div style={{
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    justifyContent: 'center'
  }}>
    <button
      onClick={() => setViewMode('pdf')}
      style={{
        padding: '8px 16px',
        fontSize: '14px',
        background: viewMode === 'pdf' ? '#3b82f6' : '#e5e7eb',
        color: viewMode === 'pdf' ? 'white' : '#333',
        border: 'none',
        borderRadius: '6px',
        cursor: 'pointer',
        fontWeight: viewMode === 'pdf' ? 'bold' : 'normal',
        transition: 'all 0.2s'
      }}
    >
      📄 PDF表示
    </button>
    <button
      onClick={() => setViewMode('video')}
      style={{
        padding: '8px 16px',
        fontSize: '14px',
        background: viewMode === 'video' ? '#3b82f6' : '#e5e7eb',
        color: viewMode === 'video' ? 'white' : '#333',
        border: 'none',
        borderRadius: '6px',
        cursor: 'pointer',
        fontWeight: viewMode === 'video' ? 'bold' : 'normal',
        transition: 'all 0.2s'
      }}
    >
      🎬 動画表示
    </button>
  </div>
)}

{/* PDFビューア（既存） */}
{viewMode === 'pdf' && slide.pdf_url && (
  <iframe
    src={slide.pdf_url}
    style={{
      width: '100%',
      height: '80vh',
      border: '1px solid #ddd',
      borderRadius: '8px'
    }}
  />
)}

{/* 動画プレビュー（新規） */}
{viewMode === 'video' && slide.video_url && (
  <div style={{
    width: '100%',
    maxWidth: '1200px',
    margin: '0 auto',
    background: '#000',
    borderRadius: '8px',
    overflow: 'hidden'
  }}>
    <video
      src={slide.video_url}
      controls
      style={{
        width: '100%',
        display: 'block'
      }}
      preload="metadata"
    >
      お使いのブラウザは動画タグをサポートしていません。
      <a href={slide.video_url} download>動画をダウンロード</a>
    </video>
  </div>
)}

{/* 動画が存在しない場合のメッセージ */}
{viewMode === 'video' && !slide.video_url && (
  <div style={{
    padding: '40px',
    textAlign: 'center',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  }}>
    <p style={{ fontSize: '16px', color: '#6b7280' }}>
      このスライドには動画版がありません
    </p>
  </div>
)}
```

**成功基準**:
- ✅ TypeScriptコンパイルエラーなし
- ✅ フロントエンドが起動する

**確認方法**:
```bash
cd frontend
npm run dev
# ブラウザで http://localhost:5173 にアクセス
```

**コミット**: `feat(ui): スライド動画プレビュー機能追加`

---

### Step 5.3: ダウンロードボタン追加（30分）

**ファイル**: `frontend/src/features/slide/components/SlideContentViewer.tsx`

**追加位置**: 切り替えボタンの横（行70付近）

```typescript
{/* ダウンロードボタン */}
<div style={{
  display: 'flex',
  gap: '8px',
  marginLeft: 'auto'
}}>
  {slide.pdf_url && (
    <a
      href={slide.pdf_url}
      download
      style={{
        padding: '8px 16px',
        fontSize: '14px',
        background: '#10b981',
        color: 'white',
        border: 'none',
        borderRadius: '6px',
        textDecoration: 'none',
        cursor: 'pointer',
        transition: 'all 0.2s'
      }}
    >
      📥 PDFダウンロード
    </a>
  )}
  {slide.video_url && (
    <a
      href={slide.video_url}
      download
      style={{
        padding: '8px 16px',
        fontSize: '14px',
        background: '#8b5cf6',
        color: 'white',
        border: 'none',
        borderRadius: '6px',
        textDecoration: 'none',
        cursor: 'pointer',
        transition: 'all 0.2s'
      }}
    >
      🎬 動画ダウンロード
    </a>
  )}
</div>
```

**成功基準**:
- ✅ PDFダウンロードボタンが表示される
- ✅ 動画ダウンロードボタンが表示される（video_urlがある場合）

**確認方法**:
```bash
# ブラウザで実際のスライド詳細ページにアクセス
# ダウンロードボタンをクリックしてファイルがダウンロードされるか確認
```

**コミット**: `feat(ui): PDF/動画ダウンロードボタン追加`

---

### Step 5.4: レスポンシブ対応（15分）

**ファイル**: `frontend/src/features/slide/components/SlideContentViewer.tsx`

**変更箇所**: 切り替えボタンのスタイル修正（行50付近）

```typescript
{/* 表示モード切り替えボタン（レスポンシブ対応） */}
{slide.video_url && (
  <div style={{
    display: 'flex',
    flexDirection: window.innerWidth < 768 ? 'column' : 'row',
    gap: '8px',
    marginBottom: '16px',
    justifyContent: 'center',
    alignItems: 'center'
  }}>
    {/* ボタン内容は同じ */}
  </div>
)}
```

**成功基準**:
- ✅ モバイル画面（幅768px未満）でボタンが縦並び
- ✅ デスクトップ画面でボタンが横並び

**確認方法**:
```bash
# ブラウザの開発者ツールでレスポンシブモードに切り替え
# 画面幅を変更してレイアウトが変わることを確認
```

**コミット**: `style(ui): 動画プレビューのレスポンシブ対応`

---

## ✅ 完了チェックリスト

### Phase 1: 環境準備
- [ ] MoviePy/Pillowインストール完了
- [ ] OpenAI TTS API動作確認完了
- [ ] MoviePy動作確認完了

### Phase 2: ナレーション生成
- [ ] `narration_prompts.py`作成完了
- [ ] `generate_narration`ノード実装完了
- [ ] 単体テスト成功（音声ファイル生成確認）

### Phase 3: 動画レンダリング
- [ ] Slidev PNG exportテスト成功
- [ ] `render_video`ノード実装完了
- [ ] パイプラインテスト成功（動画生成確認）

### Phase 4: グラフ統合
- [ ] 環境変数設定完了（VIDEO_ENABLED=true）
- [ ] グラフノード・エッジ追加完了
- [ ] エンドツーエンドテスト成功

### Phase 5: フロントエンド
- [ ] `Slide`型に`video_url`追加完了
- [ ] 動画プレビューコンポーネント実装完了
- [ ] ダウンロードボタン実装完了
- [ ] レスポンシブ対応完了

### 最終確認
- [ ] 既存のPDF生成機能が動作（後方互換性）
- [ ] VIDEO_ENABLED=falseでPDFのみ生成
- [ ] VIDEO_ENABLED=trueで動画生成
- [ ] フロントエンドで動画再生可能
- [ ] Supabase Storageに動画保存確認

---

## 🛠️ トラブルシューティング

### よくあるエラーと解決方法

#### 1. OpenAI API エラー

**エラー**: `openai.AuthenticationError: Incorrect API key provided`

**原因**: `.env`の`OPENAI_API_KEY`が未設定または間違っている

**解決**:
```bash
# .envファイルを確認
grep OPENAI_API_KEY backend/.env

# 正しいAPIキーを設定（https://platform.openai.com/api-keys で取得）
echo "OPENAI_API_KEY=sk-..." >> backend/.env
```

---

#### 2. MoviePy エラー

**エラー**: `MoviePy Error: the file ... could not be found!`

**原因**: FFmpegがインストールされていない

**解決**:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# 確認
ffmpeg -version
```

---

#### 3. Slidev PNG export エラー

**エラー**: `Error: slidev: command not found`

**原因**: Slidev CLIがインストールされていない

**解決**:
```bash
# グローバルインストール
npm install -g @slidev/cli

# Playwrightインストール（Chromium必要）
npx playwright install chromium

# 確認
slidev --version
```

---

#### 4. Supabase Storage エラー

**エラー**: `StorageApiError: Bucket not found`

**原因**: `slide-files`バケットが存在しない

**解決**:
1. Supabaseダッシュボードにログイン
2. `Storage` → `Create a new bucket`
3. バケット名: `slide-files`
4. Public access: ON

---

#### 5. 動画が生成されない

**エラー**: `video_url`が`None`

**確認手順**:
```bash
# 1. VIDEO_ENABLEDフラグ確認
grep VIDEO_ENABLED backend/.env

# 2. ログ確認
# エンドツーエンドテストを実行してログを確認
cd backend
python3 test_e2e_video.py

# 3. エラーメッセージを確認
# [narration] または [video] エントリでエラーがないか確認
```

---

## 💰 コスト詳細

### OpenAI TTS API 料金

| モデル | 価格 | 品質 | 推奨用途 |
|-------|------|------|---------|
| tts-1 | $15/100万文字 | 標準 | コスト重視 |
| tts-1-hd | $30/100万文字 | 高品質 | **品質重視（推奨）** |

### 実際のコスト試算

**想定スライド**: 5ページ × 200文字/ページ = 1,000文字

| 生成数 | tts-1 | tts-1-hd |
|-------|-------|----------|
| 1動画 | $0.015 (約2円) | $0.030 (約4円) |
| 10動画 | $0.15 (約20円) | $0.30 (約40円) |
| 100動画 | $1.50 (約200円) | $3.00 (約400円) |
| 1,000動画 | $15.00 (約2,000円) | $30.00 (約4,000円) |

**結論**: tts-1-hd（高品質）でも1動画4円と非常に安価

---

## 🚀 Phase 2 拡張アイデア（オプション）

実装が完了し、安定稼働後に検討できる追加機能:

### 1. 音声カスタマイズUI
- フロントエンドで音声（shimmer/alloy/nova）選択
- 読み上げ速度調整（0.5x - 2.0x）

### 2. 字幕トラック生成
- WebVTT形式の字幕ファイル生成
- `<video>`タグの`<track>`要素で表示

### 3. スライドトランジション
- フェード・スライドイン効果
- MoviePyの`crossfadein`/`crossfadeout`使用

### 4. 背景音楽追加
- Creative Commons音源を自動追加
- ナレーション音声より20dB小さく設定

### 5. 動画サムネイル生成
- 最初のスライドからサムネイル画像生成
- 動画プレビューに表示

---

## 📝 実装完了後のタスク

1. **ドキュメント更新**
   - `CLAUDE.md`に動画生成機能を追記
   - `README.md`の使い方セクション更新

2. **テストケース追加**
   - `backend/tests/test_video_workflow.py`作成
   - Pytestで自動テスト実装

3. **パフォーマンス測定**
   - 5スライド動画の生成時間計測
   - ボトルネック特定（Slidev export / MoviePy）

4. **コスト監視**
   - OpenAI API使用量をLangSmithで追跡
   - 月間コストアラート設定

---

## 📊 実装進捗管理

各Phaseの所要時間を記録し、振り返りに活用してください。

| Phase | 予定 | 実績 | 差分 | メモ |
|-------|------|------|------|------|
| Phase 1 | 30分 |  |  |  |
| Phase 2 | 2時間 |  |  |  |
| Phase 3 | 2.5時間 |  |  |  |
| Phase 4 | 1時間 |  |  |  |
| Phase 5 | 2時間 |  |  |  |
| **合計** | **8時間** |  |  |  |

---

## 🎓 参考資料

- [OpenAI TTS API Documentation](https://platform.openai.com/docs/guides/text-to-speech)
- [MoviePy Documentation](https://zulko.github.io/moviepy/)
- [Slidev Export Guide](https://sli.dev/guide/exporting.html)
- [Supabase Storage Guide](https://supabase.com/docs/guides/storage)

---

**作成日**: 2025-11-21
**最終更新**: 2025-11-21
**バージョン**: 1.0.0
