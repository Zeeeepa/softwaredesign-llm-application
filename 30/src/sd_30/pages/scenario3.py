"""
シナリオ3: ツール選択エージェント
"""

import uuid

import streamlit as st

from sd_30.agents.tool_selector_agent import (
    clear_selected_tools,
    create_tool_selector_agent,
    get_all_tool_names,
    get_selected_tools,
)
from sd_30.controllers import invoke_agent


@st.cache_resource
def get_agent():
    """エージェントをキャッシュして取得"""
    return create_tool_selector_agent()


def render() -> None:
    """シナリオ3の画面を描画"""
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

    # チャット入力欄を表示し、ユーザーの入力を取得する
    if prompt := st.chat_input("質問してください (例: 東京の天気と株価を教えて)"):
        # ユーザーのメッセージを履歴に追加する
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ツールを選択して実行中..."):
                # キャッシュされたエージェントを取得する
                agent = get_agent()
                # エージェントにメッセージを送信し、応答を取得する
                # ミドルウェアが質問を分析し、12個のツールから最適な3つを選択する
                # 選択されたツールはget_selected_tools()で確認できる
                response = invoke_agent(agent, prompt, st.session_state.thread_id)

                # エラーが発生した場合はエラー表示
                if response.status == "error":
                    st.error(response.message)
                else:
                    st.markdown(response.message)

                # エージェントの応答をチャット履歴に追加する
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.message
                })
                # 画面を再描画して最新の状態を表示する (選択されたツールも更新される)
                st.rerun()

    if st.button("会話をリセット"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        clear_selected_tools()
        st.rerun()
