"""Gmail送信ツールのテストスクリプト

使用方法:
1. credentials.jsonをbackend/に配置
2. python test_gmail.py
3. ブラウザで認証（初回のみ）
4. テストメールが送信される

注意: 実際にメールが送信されます
"""

from tools.gmail_tool import send_gmail

# テストメール送信
# 送信先: 自分のメールアドレス
TEST_EMAIL = "miyata09x0084@gmail.com"

def test_simple_email():
    """シンプルなテキストメール送信テスト"""
    print("=" * 50)
    print("テスト1: シンプルなメール送信")
    print("=" * 50)

    result = send_gmail.invoke({
        "to": TEST_EMAIL,
        "subject": "[テスト] SlidePilot Gmail API",
        "body": "これはGmail APIのテストメールです。\n\nReActエージェントから送信されました。"
    })
    print(result)
    print()


def test_email_with_attachment():
    """添付ファイル付きメール送信テスト"""
    print("=" * 50)
    print("テスト2: 添付ファイル付きメール送信")
    print("=" * 50)

    # 既存のスライドを添付（存在する場合）
    import os
    from pathlib import Path

    slides_dir = Path(__file__).parent / 'slides'
    pdf_files = list(slides_dir.glob('*.pdf'))

    if pdf_files:
        attachment = str(pdf_files[0])
        print(f"添付ファイル: {pdf_files[0].name}")

        result = send_gmail.invoke({
            "to": TEST_EMAIL,
            "subject": "[テスト] SlidePilot - 添付ファイル",
            "body": "PDFスライドを添付しました。",
            "attachment_path": attachment
        })
        print(result)
    else:
        print("⚠️ スライドが見つかりません。先にスライドを生成してください。")
    print()


def test_invalid_email():
    """無効なメールアドレスのテスト"""
    print("=" * 50)
    print("テスト3: 無効なメールアドレス（エラーハンドリング）")
    print("=" * 50)

    result = send_gmail.invoke({
        "to": "invalid-email",
        "subject": "これは送信されない",
        "body": "無効なメールアドレス"
    })
    print(result)
    print()


if __name__ == "__main__":
    print("\n🔧 Gmail API テスト開始\n")

    # 送信先の確認
    if TEST_EMAIL == "your-email@example.com":
        print("⚠️ 警告: TEST_EMAIL を自分のメールアドレスに変更してください")
        print("test_gmail.py の TEST_EMAIL 変数を編集してください\n")
        exit(1)

    print(f"送信先: {TEST_EMAIL}\n")

    # テスト実行
    test_simple_email()
    test_invalid_email()
    test_email_with_attachment()

    print("✅ テスト完了")
