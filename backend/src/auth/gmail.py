"""Gmail API OAuth認証モジュール

OAuth 2.0フローを管理し、Gmail APIサービスオブジェクトを提供する。
初回実行時はブラウザ認証、2回目以降はtoken.jsonから自動読み込み。
"""

from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail送信権限のみ（最小権限の原則）
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service():
    """Gmail APIサービスオブジェクトを取得

    フロー:
    1. token.jsonから既存トークンを読み込み
    2. 期限切れならリフレッシュトークンで自動更新
    3. トークンが無効/不在ならブラウザで再認証
    4. Gmail APIサービスを構築して返す

    Returns:
        Resource: Gmail API v1のサービスオブジェクト

    Raises:
        FileNotFoundError: credentials.jsonが見つからない場合
    """
    creds = None
    token_path = Path(__file__).parent.parent.parent / 'data' / 'tokens' / 'token.json'
    creds_path = Path(__file__).parent.parent.parent / 'data' / 'tokens' / 'credentials.json'

    # 既存トークンの読み込み
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # トークンの検証・更新
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 期限切れ → リフレッシュトークンで自動更新
            creds.refresh(Request())
        else:
            # 初回 or 無効 → ブラウザで認証
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"{creds_path} が見つかりません。\n"
                    "Google Cloud Consoleで OAuth 2.0認証情報を作成し、\n"
                    "credentials.json として保存してください。"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES
            )
            # ローカルサーバー起動 → ブラウザで認証
            creds = flow.run_local_server(port=0)

        # 新しいトークンを保存
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    # Gmail APIサービスを構築
    service = build('gmail', 'v1', credentials=creds)
    return service
