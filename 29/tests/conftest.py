"""pytest共通フィクスチャ"""
import uuid

import pytest
from dotenv import load_dotenv
from langchain_core.messages import AIMessage

# テスト実行前に環境変数をロード
load_dotenv()


@pytest.fixture
def thread_id():
    """ユニークなスレッドIDを生成"""
    return str(uuid.uuid4())


def extract_response(result: dict) -> str:
    """エージェント結果から最後のAIMessageを抽出"""
    if not isinstance(result, dict) or "messages" not in result:
        return str(result)
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            if isinstance(msg.content, str):
                return msg.content
            if isinstance(msg.content, list):
                text_parts = [
                    block["text"]
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if text_parts:
                    return "".join(text_parts)
    return str(result)
