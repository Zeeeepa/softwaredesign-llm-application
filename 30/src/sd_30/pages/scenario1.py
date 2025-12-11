"""
シナリオ1: メール処理エージェント
"""

import streamlit as st

from sd_30.agents.email_agent import (
    clear_sent_emails,
    create_email_agent,
    get_email_list,
    get_sent_emails,
)
from sd_30.controllers import invoke_agent, resume_agent
from sd_30.pages.common import reset_conversation


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

    # チャット入力欄を表示し、ユーザーの入力を取得する
    if prompt := st.chat_input("メールについて質問してください (例: メール一覧を見せて)"):
        # ユーザーのメッセージを履歴に追加する
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("処理中..."):
            # キャッシュされたエージェントを取得する
            agent = get_agent()
            # エージェントにメッセージを送信し、応答を取得する
            response = invoke_agent(agent, prompt, st.session_state.thread_id)

            # HumanInTheLoopMiddlewareによる割り込みが発生したか確認する
            # send_emailツール実行前に承認が必要な場合、pending_approvalになる
            if response.status == "pending_approval":
                # 承認待ち情報をセッションに保存する (ツール名、引数などが含まれる)
                st.session_state.pending_approval = response.approval_info

            # エージェントの応答をチャット履歴に追加する
            if response.message:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.message
                })
        # 画面を再描画して最新の状態を表示する
        st.rerun()

    if st.button("会話をリセット"):
        reset_conversation()
        clear_sent_emails()
        st.rerun()


def _render_approval_ui() -> None:
    """承認UIを描画"""
    # セッションから承認待ち情報を取得する
    approval_info = st.session_state.pending_approval
    st.warning("メール送信の承認待ちです")

    # 割り込み情報からツール実行の詳細を表示する
    if "action_requests" in approval_info:
        for req in approval_info["action_requests"]:
            # send_emailツールの引数 (宛先、件名、本文) を表示する
            if req["name"] == "send_email":
                args = req["args"]
                st.markdown(f"""
**送信先**: {args.get('recipient', 'N/A')}

**件名**: {args.get('subject', 'N/A')}

**本文**:
> {args.get('body', '').replace(chr(10), chr(10) + '> ')}
""")

    # 承認・却下ボタンを横並びで表示する
    col1, col2 = st.columns(2)
    with col1:
        if st.button("承認", type="primary", use_container_width=True):
            with st.spinner("送信中..."):
                # キャッシュされたエージェントを取得する
                agent = get_agent()
                # "approve"を送信して、中断されていたsend_emailツールを実行する
                response = resume_agent(agent, "approve", st.session_state.thread_id)
                # ツール実行後のエージェントの応答を履歴に追加する
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.message
                })
            # 承認待ち状態をクリアする
            st.session_state.pending_approval = None
            st.rerun()
    with col2:
        if st.button("却下", use_container_width=True):
            with st.spinner("処理中..."):
                agent = get_agent()
                # "reject"を送信して、ツール実行をスキップする
                resume_agent(agent, "reject", st.session_state.thread_id)
            # 承認待ち状態をクリアする
            st.session_state.pending_approval = None
            # 却下メッセージを履歴に追加する
            st.session_state.messages.append({
                "role": "assistant",
                "content": "メール送信を却下しました。"
            })
            st.rerun()
