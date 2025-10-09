"""Gmail送信ツール（LangChain Tool）

ReActエージェントから呼び出されるメール送信機能。
メールアドレス検証、MIME組み立て、添付ファイル処理を含む。
"""

import re
import base64
from pathlib import Path
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

from langchain_core.tools import tool
from gmail_auth import get_gmail_service


def validate_email(email: str) -> bool:
    """メールアドレスの形式を検証

    Args:
        email: 検証するメールアドレス

    Returns:
        bool: 有効ならTrue
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@tool
def send_gmail(
    to: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None
) -> str:
    """Gmail APIでメールを送信

    Args:
        to: 送信先メールアドレス
        subject: メールの件名
        body: メール本文（テキスト形式）
        attachment_path: 添付ファイルのパス（オプション）

    Returns:
        str: 送信結果メッセージ（成功 or エラー）
    """

    # メールアドレスの検証
    if not validate_email(to):
        return f"❌ エラー: 無効なメールアドレス '{to}'"

    # Gmail APIサービス取得
    try:
        service = get_gmail_service()
    except Exception as e:
        return f"❌ 認証エラー: {str(e)}"

    # MIMEメッセージの組み立て
    try:
        if attachment_path:
            # 添付ファイルあり: MIMEMultipart使用
            message = MIMEMultipart()
            message['To'] = to
            message['Subject'] = subject

            # 本文を追加
            message.attach(MIMEText(body, 'plain'))

            # 添付ファイルを追加
            attachment_file = Path(attachment_path)
            if not attachment_file.exists():
                return f"❌ エラー: 添付ファイルが見つかりません: {attachment_path}"

            with open(attachment_file, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            # Base64エンコード（メール送信の標準形式）
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment_file.name}'
            )
            message.attach(part)

        else:
            # 添付ファイルなし: シンプルなEmailMessage
            message = EmailMessage()
            message.set_content(body)
            message['To'] = to
            message['Subject'] = subject

        # メッセージをBase64URLエンコード（Gmail API仕様）
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode('utf-8')

        # Gmail APIで送信
        send_message = service.users().messages().send(
            userId='me',  # 認証済みユーザー自身
            body={'raw': raw_message}
        ).execute()

        # 送信成功
        message_id = send_message.get('id')
        return f"✅ 送信完了: {to} (Message ID: {message_id})"

    except Exception as e:
        return f"❌ 送信エラー: {str(e)}"
