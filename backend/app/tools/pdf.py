"""
PDF処理ツール (Issue #17, #29)
PDFファイルからテキストを抽出して、スライド生成に適した形式に変換

Issue #29: Supabase Storage対応
"""

from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
import json
import tempfile
from typing import Dict, Any
from app.core.storage import download_from_storage


@tool
def process_pdf(file_path: str) -> str:
    """
    PDFファイルからテキストを抽出して要約可能な形式に変換

    Supabase Storageパス or ローカルパスに対応

    Args:
        file_path: PDFファイルのパス（Storageパス: user_id/filename.pdf or ローカルパス）

    Returns:
        JSON文字列: {
            "status": "success" | "error",
            "content": str (抽出されたテキスト),
            "num_pages": int (ページ数),
            "total_chars": int (総文字数),
            "message": str (エラーメッセージ、エラー時のみ)
        }
    """
    temp_file = None
    try:
        # Supabase Storageパスの場合（user_id/filename.pdfの形式）
        if '/' in file_path and not file_path.startswith('/'):
            # Supabase Storageからダウンロード（複数user_idを試行）
            pdf_data = download_from_storage(bucket="uploads", file_path=file_path)

            # 指定されたパスでダウンロード失敗した場合、anonymous/も試す
            if not pdf_data and not file_path.startswith("anonymous/"):
                # ファイル名のみを抽出
                filename = file_path.split('/')[-1]
                fallback_path = f"anonymous/{filename}"
                print(f"[process_pdf] Trying fallback path: {fallback_path}")
                pdf_data = download_from_storage(bucket="uploads", file_path=fallback_path)

            if not pdf_data:
                return json.dumps({
                    "status": "error",
                    "message": f"Supabase Storageからファイルをダウンロードできません: {file_path}"
                }, ensure_ascii=False)

            # 一時ファイルに保存
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_file.write(pdf_data)
            temp_file.close()
            pdf_path = Path(temp_file.name)
        else:
            # ローカルパスの場合
            pdf_path = Path(file_path)
            if not pdf_path.exists():
                return json.dumps({
                    "status": "error",
                    "message": f"ファイルが見つかりません: {file_path}"
                }, ensure_ascii=False)

        if not pdf_path.suffix.lower() == '.pdf':
            return json.dumps({
                "status": "error",
                "message": "PDFファイルではありません"
            }, ensure_ascii=False)

        # PDFからテキスト抽出
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()

        if not pages:
            return json.dumps({
                "status": "error",
                "message": "PDFからテキストを抽出できませんでした"
            }, ensure_ascii=False)

        # 全ページのテキストを結合
        full_text = "\n\n".join([page.page_content for page in pages])

        if not full_text.strip():
            return json.dumps({
                "status": "error",
                "message": "PDFにテキストが含まれていません（画像のみのPDFの可能性があります）"
            }, ensure_ascii=False)

        # 長文を適切なサイズに分割（LLMのコンテキスト制限対策）
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        chunks = splitter.split_text(full_text)

        # チャンクを結合（スライド生成に使いやすい形式）
        processed_content = "\n\n---\n\n".join(chunks)

        return json.dumps({
            "status": "success",
            "content": processed_content,
            "num_pages": len(pages),
            "total_chars": len(full_text),
            "num_chunks": len(chunks)
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"PDF処理中にエラーが発生しました: {str(e)}"
        }, ensure_ascii=False)
    finally:
        # 一時ファイルを削除
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()


def test_pdf_processor(pdf_path: str) -> None:
    """PDF処理ツールのテスト用関数"""
    print(f"📄 Testing PDF processor with: {pdf_path}")
    result = process_pdf(pdf_path)
    data = json.loads(result)

    if data["status"] == "success":
        print("✅ PDF処理成功")
        print(f"   ページ数: {data['num_pages']}")
        print(f"   総文字数: {data['total_chars']}")
        print(f"   チャンク数: {data['num_chunks']}")
        print(f"   抽出テキスト（先頭200文字）:")
        print(f"   {data['content'][:200]}...")
    else:
        print(f"❌ PDF処理失敗: {data['message']}")


if __name__ == "__main__":
    # テスト実行
    import sys

    if len(sys.argv) > 1:
        test_pdf_processor(sys.argv[1])
    else:
        print("使い方: python pdf_processor.py <PDF_FILE_PATH>")
