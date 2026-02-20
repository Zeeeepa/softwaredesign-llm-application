"""
シナリオ2: レジリエンスエージェント
"""

import streamlit as st

from sd_31.agents.resilient_agent import (
    clear_execution_log,
    create_resilient_agent,
    get_execution_log,
    get_metrics,
)
from sd_31.controllers import invoke_agent
from sd_31.pages.common import ensure_scenario_state, reset_conversation

SCENARIO_ID = "scenario2"


@st.cache_resource
def get_agent():
    """エージェントをキャッシュして取得"""
    return create_resilient_agent()


def render() -> None:
    """シナリオ2の画面を描画"""
    state = ensure_scenario_state(SCENARIO_ID)
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
        1. 「PythonについてWebやデータベースから網羅的に検索して」と入力
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

    for message in state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # チャット入力欄を表示し、ユーザーの入力を取得する
    if prompt := st.chat_input("質問してください (例: Pythonについて教えて)"):
        # ユーザーのメッセージを履歴に追加する
        state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("処理中 (リトライやフォールバックが発生する場合があります)..."):
                # キャッシュされたエージェントを取得する
                agent = get_agent()
                # エージェントにメッセージを送信し、応答を取得する
                response = invoke_agent(agent, prompt, state["thread_id"])
                response_message = response.message

                # リトライやフォールバックでも回復できなかった場合はエラー表示
                if response.status == "error":
                    st.error(response_message or "エラーが発生しました。")
                elif response_message:
                    st.markdown(response_message)

                # エージェントの応答をチャット履歴に追加する
                if response_message:
                    state["messages"].append({
                        "role": "assistant",
                        "content": response_message
                    })
                # 画面を再描画して最新の状態を表示する
                st.rerun()

    if st.button("会話とログをリセット"):
        reset_conversation(SCENARIO_ID)
        clear_execution_log()
        st.rerun()
