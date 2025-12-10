"""
共通ユーティリティ
"""

import uuid

import streamlit as st
from langchain_core.messages import AIMessage


def init_session_state() -> None:
    """セッションの初期状態を設定"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "pending_approval" not in st.session_state:
        st.session_state.pending_approval = None


def extract_response(result: dict) -> str:
    """エージェントの実行結果から最後のAIメッセージを抽出"""
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


def render_sidebar() -> str:
    """サイドバーを描画してシナリオを返す"""
    st.sidebar.title("LangChain Middleware デモ")
    st.sidebar.markdown("---")

    query_params = st.query_params
    scenario = query_params.get("scenario", "scenario1")

    st.sidebar.markdown("### シナリオ選択")

    btn_type_1 = "primary" if scenario == "scenario1" else "secondary"
    btn_type_2 = "primary" if scenario == "scenario2" else "secondary"
    btn_type_3 = "primary" if scenario == "scenario3" else "secondary"

    if st.sidebar.button("シナリオ1: メール処理", use_container_width=True, type=btn_type_1):
        st.query_params["scenario"] = "scenario1"
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("シナリオ2: レジリエンス", use_container_width=True, type=btn_type_2):
        st.query_params["scenario"] = "scenario2"
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("シナリオ3: ツール選択", use_container_width=True, type=btn_type_3):
        st.query_params["scenario"] = "scenario3"
        st.session_state.messages = []
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
### 使用ミドルウェア

**シナリオ1:**
- PIIMiddleware
- SummarizationMiddleware
- HumanInTheLoopMiddleware

**シナリオ2:**
- ModelCallLimitMiddleware
- ToolCallLimitMiddleware
- ModelFallbackMiddleware
- ToolRetryMiddleware
- ModelRetryMiddleware

**シナリオ3:**
- LLMToolSelectorMiddleware
""")

    return scenario


def reset_conversation() -> None:
    """会話をリセット"""
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.pending_approval = None
