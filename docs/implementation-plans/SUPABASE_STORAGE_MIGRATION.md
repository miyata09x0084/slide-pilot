# Supabase Storage移行計画

## 📋 概要

**目的**: ローカルファイルシステムからSupabase Storageへ移行し、Cloud Runでの永続化対応

**背景**:
- Cloud Runはステートレス（ephemeral storage）
- ファイルはコンテナ再起動時に消失
- 複数インスタンス間でファイル共有不可

**解決策**: Supabase Storageで永続化

---

## ⚠️ 重要：Markdownデータは移行不要（既にDB保存済み）

### 現在の実装

**Markdownデータは既にSupabase DBに保存されています**:
- 保存先: Supabase DB `slides` テーブルの `slide_md` カラム
- 保存処理: [backend/app/core/supabase.py:35-100](../../backend/app/core/supabase.py) - `save_slide_to_supabase()`
- 取得処理: [backend/app/routers/slides.py:41-67](../../backend/app/routers/slides.py) - `/api/slides/{slide_id}/markdown`

### 移行対象の明確化

| データ種類 | 現在の保存先 | 移行後の保存先 | 移行必要性 |
|-----------|-------------|---------------|----------|
| **Markdown (.md)** | Supabase DB (`slides.slide_md`) | Supabase DB（変更なし） | ❌ **不要** |
| **PDF (.pdf)** | ローカル (`data/slides/*.pdf`) | Supabase Storage (`slides` bucket) | ✅ **必要** |
| **アップロードPDF** | ローカル (`data/uploads/*.pdf`) | Supabase Storage (`uploads` bucket) | ✅ **必要** |

**結論**: 本移行計画で対応するのは **PDFファイルのみ** です。

---

## 🔍 ローカルファイル保存箇所の調査結果

### 修正が必要な箇所（3箇所）

| # | ファイル | 行 | 処理内容 | 優先度 |
|---|---------|---|---------|--------|
| 1 | `backend/app/routers/uploads.py` | 59 | `file_path.open("wb")` - PDFアップロード保存 | 🔴 高 |
| 2 | `backend/app/agents/slide_workflow.py` | 632 | `slide_md_path.write_text()` - Slidev Markdown保存 | 🔴 高 |
| 3 | `backend/app/agents/slide_workflow.py` | 641-650 | `subprocess.run(["slidev", "export"])` - PDF生成後の保存 | 🔴 高 |

### 修正不要な箇所（2箇所）

| # | ファイル | 行 | 処理内容 | 理由 |
|---|---------|---|---------|------|
| 4 | `backend/app/auth/gmail.py` | 63 | `token.write()` - Gmail OAuthトークン | 認証トークンは一時保存でOK |
| 5 | `backend/app/core/utils.py` | 606 | `md_path.write_text()` - テスト用関数 | テスト関数のみ使用 |

---

## 📊 現在のフロー vs 修正後のフロー

### 現在の実装（ローカル保存）

```
[PDFアップロード]
  ↓ ローカル保存
backend/data/uploads/{uuid}_{filename}.pdf

[スライド生成]
  ↓ ローカル保存
backend/data/slides/{slug}_slidev.md
  ↓ slidev export
backend/data/slides/{slug}_slidev.pdf
  ↓ （オプション）
Supabase DB保存（メタデータのみ）
```

### 修正後（Supabase Storage）

```
[PDFアップロード]
  ↓ Supabase Storage
uploads/{user_id}/{uuid}_{filename}.pdf
  ↓ 署名付きURL返却

[スライド生成]
  ↓ 一時ファイル
/tmp/{slug}_slidev.md
  ↓ slidev export
/tmp/{slug}_slidev.pdf
  ↓ Supabase Storage
slides/{user_id}/{slug}_slidev.pdf
  ↓ 公開URL取得
Supabase DB保存（URL含む）
  ↓ 一時ファイル削除
rm -rf /tmp/{slug}_*
```

---

## 🎯 実装計画

### Phase 1: Supabase Storage設定

**所要時間**: 10分

#### 1-1. Supabaseダッシュボードでバケット作成

```
1. https://supabase.com/dashboard/project/{project-id}/storage にアクセス
2. 「New bucket」をクリック
3. バケット名: uploads
   - Public: OFF（認証ユーザーのみ）
   - File size limit: 100MB
4. バケット名: slides
   - Public: ON（全員読み取り可）
   - File size limit: 50MB
```

#### 1-2. RLS（Row Level Security）ポリシー設定

**uploadsバケット**:
```sql
-- 認証ユーザーが自分のフォルダにアップロード可能
CREATE POLICY "Users can upload their own files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'uploads' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- ユーザーは自分のファイルのみ読み取り可
CREATE POLICY "Users can read their own files"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'uploads' AND
  (storage.foldername(name))[1] = auth.uid()::text
);
```

**slidesバケット**:
```sql
-- 全員読み取り可能
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'slides');

-- サービスロールのみ書き込み可（バックエンドからのみ）
CREATE POLICY "Service role can upload"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'slides');
```

**成功基準**:
- [ ] uploadsバケット作成完了
- [ ] slidesバケット作成完了
- [ ] RLSポリシー4つ作成完了

---

### Phase 2: バックエンドコード修正

**所要時間**: 60分

#### 2-1. Storageヘルパー関数作成

**新規ファイル**: `backend/app/core/storage.py`

```python
"""Supabase Storage操作ヘルパー"""
from pathlib import Path
from typing import Optional
from app.core.supabase import get_supabase_client


def upload_to_storage(
    bucket: str,
    file_path: str,
    file_data: bytes,
    content_type: str = "application/octet-stream"
) -> Optional[str]:
    """Supabase Storageにファイルをアップロード

    Args:
        bucket: バケット名（uploads or slides）
        file_path: ストレージパス（user_id/filename.pdf）
        file_data: ファイルバイナリ
        content_type: MIMEタイプ

    Returns:
        公開URL or 署名付きURL
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not configured")

    try:
        # アップロード（既存ファイルは上書き）
        client.storage.from_(bucket).upload(
            path=file_path,
            file=file_data,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        # slidesバケットは公開URL
        if bucket == "slides":
            return client.storage.from_(bucket).get_public_url(file_path)

        # uploadsバケットは署名付きURL（1時間有効）
        result = client.storage.from_(bucket).create_signed_url(file_path, 3600)
        return result["signedURL"]

    except Exception as e:
        print(f"[storage] Upload failed: {e}")
        raise


def download_from_storage(bucket: str, file_path: str) -> Optional[bytes]:
    """Supabase Storageからファイルをダウンロード

    Args:
        bucket: バケット名
        file_path: ストレージパス

    Returns:
        ファイルバイナリ
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        return client.storage.from_(bucket).download(file_path)
    except Exception as e:
        print(f"[storage] Download failed: {e}")
        return None


def delete_from_storage(bucket: str, file_path: str) -> bool:
    """Supabase Storageからファイルを削除

    Args:
        bucket: バケット名
        file_path: ストレージパス

    Returns:
        成功: True、失敗: False
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        client.storage.from_(bucket).remove([file_path])
        return True
    except Exception as e:
        print(f"[storage] Delete failed: {e}")
        return False
```

**成功基準**:
- [ ] `storage.py`作成完了
- [ ] 3つの関数実装完了（upload, download, delete）

---

#### 2-2. PDFアップロード修正

**修正ファイル**: `backend/app/routers/uploads.py`

**変更箇所**: L53-73

```python
# ──────────────────────────────────────────────────────────────
# 変更前（ローカル保存）
# ──────────────────────────────────────────────────────────────
# 一意なファイル名を生成
unique_name = f"{uuid.uuid4()}_{file.filename}"
file_path = upload_dir / unique_name

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


# ──────────────────────────────────────────────────────────────
# 変更後（Supabase Storage）
# ──────────────────────────────────────────────────────────────
from app.core.storage import upload_to_storage

# 一意なファイル名を生成
unique_name = f"{uuid.uuid4()}_{file.filename}"

# TODO: 認証実装後にJWTからuser_idを取得
user_id = "anonymous"

# Supabase Storageにアップロード
storage_path = f"{user_id}/{unique_name}"

try:
    signed_url = upload_to_storage(
        bucket="uploads",
        file_path=storage_path,
        file_data=contents,
        content_type="application/pdf"
    )

    return {
        "status": "success",
        "path": storage_path,      # Storageパス
        "url": signed_url,          # ダウンロード用URL（1時間有効）
        "filename": file.filename,
        "size": file_size
    }

except Exception as e:
    raise HTTPException(status_code=500, detail=f"ファイルアップロード失敗: {str(e)}")
```

**成功基準**:
- [ ] imports追加完了
- [ ] ローカル保存コード削除
- [ ] Supabase Storage呼び出し実装
- [ ] レスポンスに`url`フィールド追加

---

#### 2-3. スライド生成修正（最重要）

**修正ファイル**: `backend/app/agents/slide_workflow.py`

**変更箇所1**: L627-632（Markdown保存）

```python
# ──────────────────────────────────────────────────────────────
# 変更前（ローカル保存）
# ──────────────────────────────────────────────────────────────
# 統一設定からスライドディレクトリを取得
slide_dir = settings.SLIDES_DIR
slide_md_path = slide_dir / f"{file_stem}_slidev.md"
slide_md_path.write_text(slide_md, encoding="utf-8")


# ──────────────────────────────────────────────────────────────
# 変更後（一時ファイル使用）
# ──────────────────────────────────────────────────────────────
import tempfile
import shutil
from app.core.storage import upload_to_storage

# 一時ディレクトリ作成（Cloud Runでも動作）
temp_dir = Path(tempfile.mkdtemp())
slide_md_path = temp_dir / f"{file_stem}_slidev.md"
slide_md_path.write_text(slide_md, encoding="utf-8")
```

**変更箇所2**: L664-693（Supabase保存処理）

```python
# ──────────────────────────────────────────────────────────────
# 変更前（ローカルファイルパスをSupabaseに渡す）
# ──────────────────────────────────────────────────────────────
result = {
    "slide_path": out_path,
    "log": _log(state, log_msg)
}

# 実行コンテキストからuser_idを取得（Read-Only）
user_id = state.get("user_id", "anonymous")
topic = state.get("topic", "AI最新情報")

try:
    # PDFが生成された場合のみパスを渡す
    pdf_path = None
    if slidev and SLIDE_FORMAT == "pdf" and "pdf_file" in locals():
        pdf_path = pdf_file

    supabase_result = save_slide_to_supabase(
        user_id=user_id,
        title=title,
        topic=topic,
        slide_md=slide_md,
        pdf_path=pdf_path  # ローカルファイルパス
    )


# ──────────────────────────────────────────────────────────────
# 変更後（Storageアップロード後にURLを渡す）
# ──────────────────────────────────────────────────────────────
user_id = state.get("user_id", "anonymous")
topic = state.get("topic", "AI最新情報")

# Supabase Storageにアップロード
pdf_url = None
md_url = None

try:
    # PDFファイルをアップロード
    if slidev and SLIDE_FORMAT == "pdf" and pdf_file.exists():
        storage_path = f"{user_id}/{file_stem}_slidev.pdf"
        pdf_url = upload_to_storage(
            bucket="slides",
            file_path=storage_path,
            file_data=pdf_file.read_bytes(),
            content_type="application/pdf"
        )
        log_msg += f" | PDF uploaded to Supabase Storage"

    # Markdownファイルもアップロード（プレビュー用）
    md_storage_path = f"{user_id}/{file_stem}_slidev.md"
    md_url = upload_to_storage(
        bucket="slides",
        file_path=md_storage_path,
        file_data=slide_md.encode("utf-8"),
        content_type="text/markdown"
    )

    # 一時ファイル削除
    shutil.rmtree(temp_dir)
    log_msg += f" | Temp files cleaned"

except Exception as e:
    log_msg += f" | Storage upload failed: {str(e)}"

# Supabase DBにメタデータ保存
try:
    supabase_result = save_slide_to_supabase(
        user_id=user_id,
        title=title,
        topic=topic,
        slide_md=slide_md,
        pdf_url=pdf_url  # StorageのURL
    )

    if "slide_id" in supabase_result:
        result = {
            "slide_path": pdf_url or md_url,  # Storage URL
            "slide_id": supabase_result["slide_id"],
            "pdf_url": pdf_url,
            "md_url": md_url,
            "log": _log(state, log_msg)
        }
    else:
        result = {
            "slide_path": pdf_url or md_url,
            "error": supabase_result.get("error", "Unknown error"),
            "log": _log(state, log_msg)
        }

except Exception as e:
    result = {
        "slide_path": "",
        "error": f"Supabase save failed: {str(e)}",
        "log": _log(state, log_msg)
    }
```

**成功基準**:
- [ ] `tempfile`使用に変更
- [ ] PDFアップロード実装
- [ ] Markdownアップロード実装
- [ ] 一時ファイル削除実装
- [ ] エラーハンドリング実装

---

#### 2-4. スライドダウンロード修正

**修正ファイル**: `backend/app/routers/slides.py`

**変更箇所**: L74-89

```python
# ──────────────────────────────────────────────────────────────
# 変更前（ローカルファイル）
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


# ──────────────────────────────────────────────────────────────
# 変更後（Supabase Storage署名付きURL）
# ──────────────────────────────────────────────────────────────
from fastapi.responses import RedirectResponse
from app.core.supabase import get_supabase_client

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
        # 1時間有効な署名付きURL生成
        result = client.storage.from_("slides").create_signed_url(
            storage_path,
            3600  # 1時間
        )
        signed_url = result["signedURL"]

        # 署名付きURLにリダイレクト
        return RedirectResponse(url=signed_url)

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {storage_path}"
        )
```

**成功基準**:
- [ ] エンドポイントパス変更（`{user_id}`追加）
- [ ] `FileResponse`削除
- [ ] `RedirectResponse`実装
- [ ] 署名付きURL生成実装

---

#### 2-5. Supabase保存関数修正

**修正ファイル**: `backend/app/core/supabase.py`

**変更箇所**: L35-100

```python
# ──────────────────────────────────────────────────────────────
# 変更前（ローカルファイルパスを受け取る）
# ──────────────────────────────────────────────────────────────
def save_slide_to_supabase(
    user_id: str,
    title: str,
    topic: str,
    slide_md: str,
    pdf_path: Optional[Path] = None  # ローカルファイルパス
) -> Dict:
    """スライドをSupabaseに保存（DB + Storage）"""
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase not configured"}

    try:
        # PDF をStorageにアップロード（存在する場合）
        pdf_url = None
        if pdf_path and pdf_path.exists():
            storage_path = f"{user_id}/{pdf_path.name}"

            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            # Storageにアップロード（既存ファイルは上書き）
            result = client.storage.from_("slide-files").upload(
                path=storage_path,
                file=pdf_data,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

            # 公開URLを取得
            pdf_url = client.storage.from_("slide-files").get_public_url(storage_path)

        # DBにメタデータを保存
        # ...


# ──────────────────────────────────────────────────────────────
# 変更後（URLを直接受け取る）
# ──────────────────────────────────────────────────────────────
def save_slide_to_supabase(
    user_id: str,
    title: str,
    topic: str,
    slide_md: str,
    pdf_url: Optional[str] = None  # StorageのURL
) -> Dict:
    """スライドをSupabase DBに保存（Storageアップロードは別で実施済み）

    Args:
        user_id: ユーザー識別子（emailなど）
        title: スライドタイトル
        topic: スライドのトピック（入力値）
        slide_md: Markdownコンテンツ
        pdf_url: PDFの公開URL（既にStorageにアップロード済み）

    Returns:
        成功時: {"slide_id": str, "pdf_url": str}
        失敗時: {"error": str}
    """
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase not configured"}

    try:
        # DBにメタデータを保存（Storageアップロードは呼び出し元で実施済み）
        data = {
            "user_id": user_id,
            "title": title,
            "topic": topic,
            "slide_md": slide_md,
            "pdf_url": pdf_url  # 既にStorageにアップロード済みのURL
        }

        response = client.table("slides").insert(data).execute()

        if response.data and len(response.data) > 0:
            slide_record = response.data[0]
            return {
                "slide_id": slide_record["id"],
                "pdf_url": pdf_url
            }
        else:
            return {"error": "Failed to insert slide record"}

    except Exception as e:
        return {"error": f"Supabase save failed: {str(e)}"}
```

**成功基準**:
- [ ] 関数シグネチャ変更（`pdf_path: Path` → `pdf_url: str`）
- [ ] Storageアップロードコード削除
- [ ] DBメタデータ保存のみ実装

---

#### 2-6. 設定ファイル修正

**修正ファイル**: `backend/app/config.py`

**変更箇所**: L36-66

```python
# ──────────────────────────────────────────────────────────────
# 変更前（ローカルディレクトリ使用）
# ──────────────────────────────────────────────────────────────
# データディレクトリ（環境変数で制御可能）
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))

# ファイルパス設定（DATA_DIRベース）
UPLOAD_DIR: Path = DATA_DIR / "uploads"
SLIDES_DIR: Path = DATA_DIR / "slides"
TOKENS_DIR: Path = DATA_DIR / "tokens"

def __init__(self):
    """ディレクトリを自動作成"""
    self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    self.SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    self.TOKENS_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# 変更後（Supabase使用、一時ファイルのみローカル）
# ──────────────────────────────────────────────────────────────
# データディレクトリ（tokensのみ使用）
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))

# ファイルパス設定（tokensのみローカル、他はSupabase Storage）
TOKENS_DIR: Path = DATA_DIR / "tokens"

# Supabase設定（Storage使用）
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")

def __init__(self):
    """必要最小限のディレクトリを作成"""
    self.TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    # LangSmith環境変数設定
    os.environ.setdefault("LANGCHAIN_TRACING_V2", self.LANGCHAIN_TRACING_V2)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", self.LANGCHAIN_ENDPOINT)
```

**成功基準**:
- [ ] `UPLOAD_DIR`, `SLIDES_DIR`削除
- [ ] `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`追加
- [ ] `__init__`メソッド簡略化

---

#### 2-7. 依存性注入修正

**修正ファイル**: `backend/app/dependencies.py`

```python
# ──────────────────────────────────────────────────────────────
# 変更前
# ──────────────────────────────────────────────────────────────
def get_upload_dir() -> Path:
    """アップロードディレクトリを取得"""
    return settings.UPLOAD_DIR


def get_slides_dir() -> Path:
    """スライドディレクトリを取得"""
    return settings.SLIDES_DIR


# ──────────────────────────────────────────────────────────────
# 変更後（削除または未使用に変更）
# ──────────────────────────────────────────────────────────────
# get_upload_dir() - 削除（未使用）
# get_slides_dir() - 削除（未使用）

# 必要な場合のみ残す
def get_max_file_size() -> int:
    """最大ファイルサイズを取得"""
    return settings.MAX_FILE_SIZE
```

**成功基準**:
- [ ] 未使用の依存性注入削除

---

### Phase 3: テスト

**所要時間**: 30分

#### 3-1. ローカル環境テスト

```bash
# バックエンド起動
cd backend
python3 -m langgraph_cli dev --host 0.0.0.0 --port 2024 &
cd app
python3 main.py &

# フロントエンド起動
cd frontend
npm run dev
```

**テストケース**:

1. **PDFアップロードテスト**
   - [ ] PDFファイルをアップロード
   - [ ] Supabase Storage `uploads`バケットに保存確認
   - [ ] レスポンスに`url`フィールドあり
   - [ ] 署名付きURLでダウンロード可能

2. **スライド生成テスト**
   - [ ] トピック入力してスライド生成
   - [ ] Supabase Storage `slides`バケットにPDF保存確認
   - [ ] Supabase DB `slides`テーブルにレコード追加確認
   - [ ] `pdf_url`が公開URLになっている

3. **スライドダウンロードテスト**
   - [ ] `/api/slides/{user_id}/{filename}` にアクセス
   - [ ] 署名付きURLにリダイレクト
   - [ ] PDFダウンロード成功

4. **一時ファイル削除確認**
   - [ ] スライド生成後に`/tmp`内のファイルが削除されている

---

## 📝 最終チェックリスト

### Supabase設定
- [ ] `uploads`バケット作成完了
- [ ] `slides`バケット作成完了
- [ ] RLSポリシー4つ作成完了
- [ ] 環境変数設定済み（`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`）

### バックエンド修正
- [ ] `backend/app/core/storage.py` 新規作成
- [ ] `backend/app/routers/uploads.py` 修正完了
- [ ] `backend/app/agents/slide_workflow.py` 修正完了
- [ ] `backend/app/routers/slides.py` 修正完了
- [ ] `backend/app/core/supabase.py` 修正完了
- [ ] `backend/app/config.py` 修正完了
- [ ] `backend/app/dependencies.py` 修正完了

### テスト
- [ ] PDFアップロードテスト成功
- [ ] スライド生成テスト成功
- [ ] スライドダウンロードテスト成功
- [ ] 一時ファイル削除確認

### ドキュメント
- [ ] 本ドキュメント作成完了
- [ ] `README.md`に追記

---

## 🎯 移行の利点

| 項目 | ローカルストレージ | Supabase Storage |
|------|-------------------|------------------|
| Cloud Run互換 | ❌ 再起動で消失 | ✅ 永続化 |
| 複数インスタンス | ❌ 共有不可 | ✅ 全インスタンス共有 |
| バックアップ | ❌ 手動 | ✅ 自動 |
| CDN配信 | ❌ なし | ✅ グローバルCDN |
| アクセス制御 | ❌ 困難 | ✅ RLS + 署名付きURL |
| コスト | $0（ローカル） | $0（1GB無料枠） |
| 運用負荷 | 高（手動管理） | 低（マネージド） |

---

## 🚨 注意事項

1. **一時ファイルのクリーンアップ**
   - `/tmp`は定期的にクリーンアップされるが、明示的な削除推奨
   - `shutil.rmtree(temp_dir)`を確実に実行

2. **エラーハンドリング**
   - Storageアップロード失敗時もログに記録
   - 一時ファイルは必ず削除（finally句使用推奨）

3. **user_id管理**
   - 現在は`anonymous`固定
   - 認証実装後にJWTから取得するよう修正必要

4. **バケット容量**
   - 無料枠1GB
   - 定期的な古いファイル削除バッチ推奨

---

## 📚 参考資料

- [Supabase Storage公式ドキュメント](https://supabase.com/docs/guides/storage)
- [Cloud Run Ephemeral Storage](https://cloud.google.com/run/docs/using-in-memory-file-system)
- [Python tempfile](https://docs.python.org/3/library/tempfile.html)
