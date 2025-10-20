"""
PDF処理ツール (Issue #17)
PDFファイルからテキストを抽出して、スライド生成に適した形式に変換
"""

from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
import json
from typing import Dict, Any


@tool
def process_pdf(file_path: str) -> str:
    """
    PDFファイルからテキストを抽出して要約可能な形式に変換

    Args:
        file_path: PDFファイルのパス

    Returns:
        JSON文字列: {
            "status": "success" | "error",
            "content": str (抽出されたテキスト),
            "num_pages": int (ページ数),
            "total_chars": int (総文字数),
            "message": str (エラーメッセージ、エラー時のみ)
        }
    """
    try:
        # パスの検証
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
