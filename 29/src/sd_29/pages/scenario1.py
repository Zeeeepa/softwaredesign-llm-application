"""
シナリオ1: メール処理エージェント
"""

import streamlit as st
from langchain.agents.middleware._redaction import PIIDetectionError
from langgraph.types import Command

from sd_29.agents.email_agent import (
    clear_sent_emails,
    create_email_agent,
    get_email_list,
    get_sent_emails,
)
from sd_29.pages.common import extract_response, reset_conversation


@st.cache_resource
def get_agent():
    """エージェントをキャッシュして取得"""
    return create_email_agent()


def render() -> None:
    """シナリオ1の画面を描画"""
    st.title("メール処理エージェント")

    with st.expander("このエージェントについて", expanded=True):
        st.markdown("""
        ### 概要
        メールの読み取り・送信を行うエージェントです。個人情報の保護と、
        重要な操作 (メール送信) に対する人間の承認フローを実装しています。

        ### 使用ミドルウェア
        - **PIIMiddleware**: メールアドレス・電話番号を自動でマスキング
        - **SummarizationMiddleware**: 会話が長くなると自動で要約
        - **HumanInTheLoopMiddleware**: メール送信前に人間の承認を要求

        ### テスト方法
        1. 「メール一覧を見せて」と入力してメール一覧を確認
        2. 「メール001を読んで」と入力してメール内容を確認
        3. 電話番号を含むメッセージ (例: 「090-1234-5678に連絡して」) を入力
           - PIIMiddlewareにより入力がブロックされることを確認
        4. 「田中さんに『了解しました』と返信して」と具体的な内容を指定
           - 送信前に承認ダイアログが表示されることを確認
           - 「承認」または「却下」を選択
        """)

    with st.expander("受信メール一覧", expanded=False):
        emails = get_email_list()
        for email in emails:
            st.markdown(f"""
            **[{email['id']}] {email['subject']}**
            - 差出人: {email['from']}
            - 日付: {email['date']}
            """)
            st.divider()

    sent_emails = get_sent_emails()
    if sent_emails:
        with st.expander(f"送信済みメール ({len(sent_emails)}件)", expanded=False):
            for email in sent_emails:
                st.markdown(f"""
                **{email['subject']}**
                - 宛先: {email['to']}
                - 本文: {email['body'][:100]}...
                """)
                st.divider()

    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 承認待ちの処理
    if st.session_state.pending_approval:
        _render_approval_ui()
        return

    # チャット入力
    if prompt := st.chat_input("メールについて質問してください (例: メール一覧を見せて)"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("処理中..."):
            try:
                agent = get_agent()
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )

                if "__interrupt__" in result:
                    interrupt_info = result["__interrupt__"][0].value
                    st.session_state.pending_approval = interrupt_info
                    response = extract_response(result)
                    if response:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response
                        })
                else:
                    response = extract_response(result)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
            except PIIDetectionError as e:
                pii_type = "電話番号" if "phone" in str(e).lower() else "個人情報"
                error_msg = f"入力に{pii_type}が含まれているため、処理をブロックしました。個人情報を含まない形で再度入力してください。"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            except Exception as e:
                error_msg = f"エラーが発生しました: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
        st.rerun()

    if st.button("会話をリセット"):
        reset_conversation()
        clear_sent_emails()
        st.rerun()


def _render_approval_ui() -> None:
    """承認UIを描画"""
    approval_info = st.session_state.pending_approval
    st.warning("メール送信の承認待ちです")

    if "action_requests" in approval_info:
        for req in approval_info["action_requests"]:
            if req["name"] == "send_email":
                args = req["args"]
                st.markdown(f"""
**送信先**: {args.get('recipient', 'N/A')}

**件名**: {args.get('subject', 'N/A')}

**本文**:
> {args.get('body', '').replace(chr(10), chr(10) + '> ')}
""")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("承認", type="primary", use_container_width=True):
            with st.spinner("送信中..."):
                try:
                    agent = get_agent()
                    result = agent.invoke(
                        Command(resume={"decisions": [{"type": "approve"}]}),
                        config={"configurable": {"thread_id": st.session_state.thread_id}},
                    )
                    response = extract_response(result)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"エラー: {str(e)}"
                    })
            st.session_state.pending_approval = None
            st.rerun()
    with col2:
        if st.button("却下", use_container_width=True):
            with st.spinner("処理中..."):
                try:
                    agent = get_agent()
                    agent.invoke(
                        Command(resume={"decisions": [{"type": "reject"}]}),
                        config={"configurable": {"thread_id": st.session_state.thread_id}},
                    )
                except Exception:
                    pass
            st.session_state.pending_approval = None
            st.session_state.messages.append({
                "role": "assistant",
                "content": "メール送信を却下しました。"
            })
            st.rerun()
