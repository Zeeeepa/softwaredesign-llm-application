"""
LangChain Middleware デモアプリケーション

サイドバーでシナリオを切り替えて、各ミドルウェアの動作を確認できます。
"""

import uuid

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="LangChain Middleware デモ",
    layout="wide",
)

# =============================================================================
# サイドバー
# =============================================================================

st.sidebar.title("LangChain Middleware デモ")
st.sidebar.markdown("---")

# URLのクエリパラメータからシナリオを取得
query_params = st.query_params
scenario = query_params.get("scenario", "scenario1")

st.sidebar.markdown("### シナリオ選択")

# 選択中のシナリオはprimaryボタンで強調表示
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


# =============================================================================
# セッション管理
# =============================================================================


def init_session_state():
    """セッションの初期状態を設定"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "pending_approval" not in st.session_state:
        st.session_state.pending_approval = None


init_session_state()


def extract_response(result: dict) -> str:
    """エージェントの実行結果から最後のAIメッセージを抽出"""
    from langchain_core.messages import AIMessage

    if not isinstance(result, dict) or "messages" not in result:
        return str(result)

    # 最後のAIMessageを探す
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            # contentが文字列の場合
            if isinstance(msg.content, str):
                return msg.content
            # contentがリスト (tool_use + text) の場合
            if isinstance(msg.content, list):
                text_parts = [
                    block["text"]
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if text_parts:
                    return "".join(text_parts)

    return str(result)


# =============================================================================
# シナリオ1: メール処理エージェント
# =============================================================================


@st.cache_resource
def get_email_agent():
    """シナリオ1のエージェントをキャッシュして取得"""
    from sd_29.agents.email_assistant import create_email_assistant_agent
    return create_email_assistant_agent()


def render_scenario1():
    """シナリオ1の画面を表示"""
    from langchain.agents.middleware._redaction import PIIDetectionError
    from langgraph.types import Command

    from sd_29.agents.email_assistant import (
        clear_sent_emails,
        get_email_list,
        get_sent_emails,
    )

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

    if st.session_state.pending_approval:
        approval_info = st.session_state.pending_approval
        st.warning("メール送信の承認待ちです")

        # 承認待ちの内容を表示
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
                        agent = get_email_agent()
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
                        agent = get_email_agent()
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
        return

    if prompt := st.chat_input("メールについて質問してください (例: メール一覧を見せて)"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("処理中..."):
            try:
                agent = get_email_agent()
                # 最新のメッセージのみ渡す (checkpointerで履歴は管理される)
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )

                # HITL interrupt確認
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
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pending_approval = None
        clear_sent_emails()
        st.rerun()


# =============================================================================
# シナリオ2: レジリエンスエージェント
# =============================================================================


@st.cache_resource
def get_resilient_agent():
    """シナリオ2のエージェントをキャッシュして取得"""
    from sd_29.agents.resilient_qa import create_resilient_qa_agent
    return create_resilient_qa_agent()


def render_scenario2():
    """シナリオ2の画面を表示"""
    from sd_29.agents.resilient_qa import (
        clear_execution_log,
        get_execution_log,
        get_metrics,
    )

    st.title("レジリエンスエージェント")

    with st.expander("このエージェントについて", expanded=True):
        st.markdown("""
        ### 概要
        Web検索やデータベース問い合わせを行うエージェントです。
        ツールはランダムに失敗するよう設計されており、ミドルウェアによる
        リトライやフォールバックの動作を確認できます。

        ### 使用ミドルウェア
        - **ModelCallLimitMiddleware**: モデル呼び出し回数を制限 (最大5回/リクエスト)
        - **ToolCallLimitMiddleware**: ツール呼び出し回数を制限 (最大10回/セッション)
        - **ModelFallbackMiddleware**: モデルエラー時に代替モデルへフォールバック
        - **ToolRetryMiddleware**: ツールエラー時に自動リトライ (最大2回)
        - **ModelRetryMiddleware**: モデルエラー時に自動リトライ

        ### テスト方法
        1. 「Pythonについて検索して」と入力
           - 実行ログで成功/失敗の状態を確認
           - 失敗時は自動リトライされる
        2. 何度か質問を繰り返して、エラー発生とリトライの様子を観察
        3. メトリクスで成功率を確認
        4. search_webツールは30%、query_databaseツールは20%の確率で失敗
        """)

    col1, col2, col3, col4 = st.columns(4)
    metrics = get_metrics()
    col1.metric("総イベント数", metrics["total_events"])
    col2.metric("成功", metrics["success_count"])
    col3.metric("エラー", metrics["error_count"])
    col4.metric("成功率", f"{metrics['success_rate']:.1f}%")

    with st.expander("実行ログ", expanded=True):
        log = get_execution_log()
        if log:
            for event in log[-10:]:
                status = "[成功]" if event["type"] == "success" else "[失敗]"
                st.markdown(f"{status} {event['message']}")
        else:
            st.info("実行ログはまだありません")

    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("質問してください (例: Pythonについて教えて)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("処理中 (リトライやフォールバックが発生する場合があります)..."):
                try:
                    agent = get_resilient_agent()
                    result = agent.invoke(
                        {"messages": [{"role": "user", "content": prompt}]},
                        config={"configurable": {"thread_id": st.session_state.thread_id}},
                    )

                    response = extract_response(result)
                    st.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    error_msg = f"エラーが発生しました: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                st.rerun()

    if st.button("会話とログをリセット"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        clear_execution_log()
        st.rerun()


# =============================================================================
# シナリオ3: ツール選択エージェント
# =============================================================================


@st.cache_resource
def get_tool_selector_agent():
    """シナリオ3のエージェントをキャッシュして取得"""
    from sd_29.agents.tool_selector import create_tool_selector_agent
    return create_tool_selector_agent()


def render_scenario3():
    """シナリオ3の画面を表示"""
    from sd_29.agents.tool_selector import (
        clear_selected_tools,
        get_all_tool_names,
        get_selected_tools,
    )

    st.title("ツール選択エージェント")

    with st.expander("このエージェントについて", expanded=True):
        st.markdown("""
        ### 概要
        12個のツール (計算、天気、検索、翻訳、株価など) を持つエージェントです。
        質問内容に応じて、LLMが事前に最適なツールを3つまで選択します。
        これにより、大量のツールがあっても効率的に処理できます。

        ### 使用ミドルウェア
        - **LLMToolSelectorMiddleware**: 質問に適したツールを事前選択
          - 12個のツールから最大3個を自動選択
          - searchツールは常に含める (always_include)

        ### テスト方法
        1. 「東京の天気を教えて」と入力
           - weather と search が選択されることを確認
        2. 「100ドルは何円?」と入力
           - currency_convert と search が選択されることを確認
        3. 「Appleの株価と最新ニュースを教えて」と入力
           - stock_price, news, search が選択されることを確認
        4. 異なる質問で選択されるツールが変わることを観察
        """)

    all_tools = get_all_tool_names()
    selected_tools = get_selected_tools()

    st.subheader("利用可能なツール")
    cols = st.columns(4)
    for i, tool_name in enumerate(all_tools):
        col = cols[i % 4]
        if tool_name in selected_tools:
            col.success(f"[選択] {tool_name}")
        else:
            col.text(f"{tool_name}")

    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("質問してください (例: 東京の天気と株価を教えて)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ツールを選択して実行中..."):
                try:
                    agent = get_tool_selector_agent()
                    result = agent.invoke(
                        {"messages": [{"role": "user", "content": prompt}]},
                        config={"configurable": {"thread_id": st.session_state.thread_id}},
                    )

                    response = extract_response(result)
                    st.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    error_msg = f"エラーが発生しました: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                st.rerun()

    if st.button("会話をリセット"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        clear_selected_tools()
        st.rerun()


# =============================================================================
# メイン処理
# =============================================================================

if scenario == "scenario1":
    render_scenario1()
elif scenario == "scenario2":
    render_scenario2()
elif scenario == "scenario3":
    render_scenario3()
