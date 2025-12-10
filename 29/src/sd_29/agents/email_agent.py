"""
メールアシスタントエージェント

PIIフィルタリング、会話履歴要約、人間承認フローのデモ
"""

import json
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    PIIMiddleware,
    SummarizationMiddleware,
)
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


# モックデータを読み込み
def _load_mock_data() -> dict:
    mock_path = Path(__file__).parent.parent / "mock" / "email_agent.json"
    with open(mock_path, encoding="utf-8") as f:
        return json.load(f)


_MOCK_DATA = _load_mock_data()
_MOCK_EMAILS = _MOCK_DATA["emails"]

# 送信済みメール
_sent_emails: list[dict] = []


# ツール定義
@tool
def read_email(email_id: str) -> str:
    """
    指定したIDのメールを読み取る

    Args:
        email_id: メールID (例: "001", "002", "003")

    Returns:
        メールの内容
    """
    if email_id not in _MOCK_EMAILS:
        return f"エラー: メールID '{email_id}' は見つかりません。利用可能なID: {list(_MOCK_EMAILS.keys())}"

    email = _MOCK_EMAILS[email_id]
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
    メールを送信する

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
    _sent_emails.append(email)

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
    受信メール一覧を表示する

    Returns:
        メール一覧
    """
    result = "受信メール一覧:\n" + "=" * 50 + "\n"
    for email_id, email in _MOCK_EMAILS.items():
        result += f"[{email_id}] {email['date']} - {email['from']}\n"
        result += f"    件名: {email['subject']}\n"
        result += "-" * 50 + "\n"
    return result


EMAIL_AGENT_SYSTEM_PROMPT = """あなたはメールアシスタントです。
メール一覧表示、読み取り、送信ができます。
送信を依頼されたらすぐにsend_emailを呼び出してください。承認はシステムが処理します。
必ず日本語で対応してください。
""".strip()

def create_email_agent():
    """メールアシスタントエージェントを作成"""
    # 電話番号検出パターン
    phone_pattern = r"(?:\+?\d{1,3}[\s.-]?)*\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}"

    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=[read_email, send_email, list_emails],
        system_prompt=EMAIL_AGENT_SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
        middleware=[
            # メールアドレスをマスク
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
            # 電話番号をブロック
            PIIMiddleware(
                "phone_number",
                detector=phone_pattern,
                strategy="block",
                apply_to_input=True,
            ),
            # 長い履歴を自動要約
            SummarizationMiddleware(
                model="anthropic:claude-haiku-4-5",
                trigger=("tokens", 1_000), # 1000トークン超で自動要約
            ),
            # send_email実行前に承認を要求
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "send_email": {"allowed_decisions": ["approve", "reject"]},
                    "read_email": False,
                    "list_emails": False,
                }
            ),
        ],
    )

    return agent

# =============================================================================
# Streamlitの画面向けユーティリティ関数
# =============================================================================

def get_email_list() -> list[dict]:
    """メール一覧を取得"""
    return list(_MOCK_EMAILS.values())


def get_sent_emails() -> list[dict]:
    """送信済みメール一覧を取得"""
    return _sent_emails


def clear_sent_emails() -> None:
    """送信済みメールをクリア"""
    _sent_emails.clear()
