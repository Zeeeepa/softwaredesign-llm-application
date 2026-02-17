"""
エージェントとのメッセージング処理
"""

from langchain.agents.middleware._redaction import PIIDetectionError
from langchain_core.messages import AIMessage
from langgraph.types import Command

from sd_31.agents import AgentResponse


def _extract_response(result: dict) -> str:
    """
    エージェントの実行結果から最後のAIメッセージを抽出する。

    agent.invoke()の戻り値は{"messages": [...]}の形式になっている。
    messagesリストを逆順に走査し、最初に見つかったAIMessageの内容を返す。
    """
    # 結果が辞書でない場合、または"messages"キーがない場合は文字列化して返す
    if not isinstance(result, dict) or "messages" not in result:
        return str(result)

    # messagesリストを逆順に走査して、最後のAIMessageを探す
    for msg in reversed(result["messages"]):
        # AIMessageかつ内容がある場合
        if isinstance(msg, AIMessage) and msg.content:
            # contentが文字列の場合はそのまま返す
            if isinstance(msg.content, str):
                return msg.content
            # contentがリストの場合 (マルチモーダル応答など) はテキスト部分を結合
            if isinstance(msg.content, list):
                text_parts = [
                    block["text"]
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if text_parts:
                    return "".join(text_parts)

    # AIMessageが見つからない場合は結果全体を文字列化
    return str(result)


def invoke_agent(agent, user_message: str, thread_id: str) -> AgentResponse:
    """
    エージェントにメッセージを送信し、応答を取得する。

    この関数は全エージェントで共通の対話処理を担当する。
    エージェントに設定されたミドルウェアが自動的に適用される。
    """
    try:
        # agent.invoke()でエージェントを実行する
        # 第1引数: メッセージを含む辞書。"messages"キーを使用
        # config: thread_idを指定することで、checkpointerで会話履歴を保存できる
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # HumanInTheLoopMiddlewareによる割り込みを確認する
        # 承認が必要なツール実行前に、ミドルウェアが処理を中断する
        # 中断時は結果に"__interrupt__"キーが設定される
        if "__interrupt__" in result:
            # 割り込み情報を取得する (ツール名、引数などが含まれる)
            interrupt_info = result["__interrupt__"][0].value
            # 割り込み前までのエージェントの応答を抽出する
            response_text = _extract_response(result)
            # 承認待ち状態として返す
            return AgentResponse(
                status="pending_approval",
                message=response_text,
                approval_info=interrupt_info,
            )

        # 通常の応答を抽出する
        # _extract_response()はmessagesリストから最後のAIMessageを取得する
        response_text = _extract_response(result)
        # 正常完了として返す
        return AgentResponse(status="success", message=response_text)

    except PIIDetectionError as e:
        # PIIMiddlewareがstrategy="block"で個人情報を検出した場合
        # 電話番号など、ブロック対象のPIIが入力に含まれていた
        pii_type = "電話番号" if "phone" in str(e).lower() else "個人情報"
        return AgentResponse(
            status="pii_blocked",
            message=f"入力に{pii_type}が含まれているため、処理をブロックしました。",
        )
    except Exception as e:
        # その他のエラー (API障害、ネットワークエラーなど)
        return AgentResponse(
            status="error",
            message=f"エラーが発生しました: {str(e)}",
        )


def resume_agent(agent, decision: str, thread_id: str) -> AgentResponse:
    """
    承認待ち状態のエージェントに決定を送信し、処理を再開する。

    HumanInTheLoopMiddlewareによる割り込み後に呼び出す。
    """
    try:
        # Command(resume=...)で割り込み状態から処理を再開する
        # decisionsリストに承認("approve")または却下("reject")を指定する
        # approveの場合: 中断されていたツールが実行される
        # rejectの場合: ツール実行がスキップされ、エージェントに却下が通知される
        result = agent.invoke(
            Command(resume={"decisions": [{"type": decision}]}),
            config={"configurable": {"thread_id": thread_id}},
        )
        # ツール実行後のエージェントの応答を抽出する
        response_text = _extract_response(result)
        return AgentResponse(status="success", message=response_text)
    except Exception as e:
        return AgentResponse(
            status="error",
            message=f"エラーが発生しました: {str(e)}",
        )
