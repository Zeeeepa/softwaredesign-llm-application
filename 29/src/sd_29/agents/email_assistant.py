"""
シナリオ1: プライバシー配慮 & 承認フロー付きメールアシスタント

PIIフィルタリング、会話履歴要約、人間承認フローのデモ

使用ミドルウェア:
- PIIMiddleware: メールアドレス・電話番号のマスキング/ブロック
- SummarizationMiddleware: 長い履歴の自動要約
- HumanInTheLoopMiddleware: メール送信前の承認
"""

from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    PIIMiddleware,
    SummarizationMiddleware,
)
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

# =============================================================================
# モックメールデータ
# =============================================================================

MOCK_EMAILS = {
    "001": {
        "id": "001",
        "from": "tanaka.taro@example.com",
        "to": "yamada.hanako@example.com",
        "subject": "プロジェクトの進捗報告",
        "body": """山田様

お疲れ様です。田中です。

プロジェクトAの進捗についてご報告いたします。
現在、開発フェーズは80%完了しており、来週中にはテストフェーズに移行できる見込みです。

ご不明な点がございましたら、お気軽にお問い合わせください。
電話番号: 03-1234-5678

よろしくお願いいたします。

田中太郎
tanaka.taro@example.com
""",
        "date": "2025-12-09",
    },
    "002": {
        "id": "002",
        "from": "suzuki.ichiro@partner.co.jp",
        "to": "yamada.hanako@example.com",
        "subject": "契約書の確認依頼",
        "body": """山田様

いつもお世話になっております。
鈴木です。

先日お送りした契約書について、ご確認いただけましたでしょうか。
修正点などございましたら、ご連絡ください。

担当: 鈴木一郎
連絡先: 090-9876-5432
メール: suzuki.ichiro@partner.co.jp

何卒よろしくお願いいたします。
""",
        "date": "2025-12-08",
    },
    "003": {
        "id": "003",
        "from": "info@newsletter.example.com",
        "to": "yamada.hanako@example.com",
        "subject": "【重要】サービスメンテナンスのお知らせ",
        "body": """お客様各位

平素より当サービスをご利用いただき、誠にありがとうございます。

下記の日程でシステムメンテナンスを実施いたします。

日時: 2025年12月15日(日) 02:00〜06:00
影響: 上記時間帯はサービスをご利用いただけません

ご不便をおかけしますが、何卒ご理解いただきますようお願い申し上げます。

サポートセンター
電話: 0120-000-000
メール: support@newsletter.example.com
""",
        "date": "2025-12-07",
    },
}

# 送信済みメール保存用
SENT_EMAILS: list[dict] = []


# =============================================================================
# ツール定義
# =============================================================================


@tool
def read_email(email_id: str) -> str:
    """
    指定したIDのメールを読み取ります。

    Args:
        email_id: メールID (例: "001", "002", "003")

    Returns:
        メールの内容
    """
    if email_id not in MOCK_EMAILS:
        return f"エラー: メールID '{email_id}' は見つかりませんでした。利用可能なID: {list(MOCK_EMAILS.keys())}"

    email = MOCK_EMAILS[email_id]
    return f"""
========================================
件名: {email['subject']}
差出人: {email['from']}
宛先: {email['to']}
日付: {email['date']}
========================================

{email['body']}
"""


@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """
    メールを送信します。

    Args:
        recipient: 宛先メールアドレス
        subject: 件名
        body: 本文

    Returns:
        送信結果
    """
    email = {
        "to": recipient,
        "subject": subject,
        "body": body,
        "status": "sent",
    }
    SENT_EMAILS.append(email)

    return f"""
メールを送信しました。

宛先: {recipient}
件名: {subject}
本文:
{body}
"""


@tool
def list_emails() -> str:
    """
    受信メール一覧を表示します。

    Returns:
        メール一覧
    """
    result = "受信メール一覧:\n" + "=" * 50 + "\n"
    for email_id, email in MOCK_EMAILS.items():
        result += f"[{email_id}] {email['date']} - {email['from']}\n"
        result += f"    件名: {email['subject']}\n"
        result += "-" * 50 + "\n"
    return result


# =============================================================================
# エージェント作成
# =============================================================================


def create_email_assistant_agent():
    """
    プライバシー配慮 & 承認フロー付きメールアシスタントエージェントを作成
    """
    # 電話番号検出用の正規表現パターン
    phone_pattern = r"(?:\+?\d{1,3}[\s.-]?)*\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}"

    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=[read_email, send_email, list_emails],
        system_prompt="""あなたはユーザーのメールアシスタントです。

主な機能:
- メール一覧の表示 (list_emails)
- メールの読み取りと要約 (read_email)
- メールの送信 (send_email)

重要:
- ユーザーからメール送信を依頼されたら、すぐにsend_emailツールを呼び出してください
- 送信前の承認はシステム (HumanInTheLoopMiddleware) が自動的に処理します
- 日本語で丁寧に対応してください
""",
        checkpointer=InMemorySaver(),
        middleware=[
            # PIIフィルタリング: メールアドレスをマスク
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
            # PIIフィルタリング: 電話番号を検出してブロック
            PIIMiddleware(
                "phone_number",
                detector=phone_pattern,
                strategy="block",
                apply_to_input=True,
            ),
            # 会話履歴要約: トークン数が500を超えたら要約
            SummarizationMiddleware(
                model="anthropic:claude-haiku-4-5",
                trigger=("tokens", 500),
            ),
            # 人間承認: send_email実行前に承認を要求
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
                    "read_email": False,  # 読み取りは承認不要
                    "list_emails": False,  # 一覧表示は承認不要
                }
            ),
        ],
    )

    return agent


# =============================================================================
# ユーティリティ関数
# =============================================================================


def get_email_list() -> list[dict]:
    """UIで表示するためのメール一覧を取得"""
    return list(MOCK_EMAILS.values())


def get_sent_emails() -> list[dict]:
    """送信済みメール一覧を取得"""
    return SENT_EMAILS


def clear_sent_emails() -> None:
    """送信済みメールをクリア"""
    SENT_EMAILS.clear()
