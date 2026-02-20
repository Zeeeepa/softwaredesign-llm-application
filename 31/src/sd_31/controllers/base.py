"""
エージェントとのメッセージング処理
"""

from collections import Counter
from typing import Any, Sequence

from langchain.agents.middleware._redaction import PIIDetectionError
from langchain_core.messages import AIMessage
from langgraph.types import Command

from sd_31.agents import AgentResponse


def _extract_text_from_ai_message(message: AIMessage) -> str | None:
    """AIMessageから表示可能なテキストを抽出する。"""
    if isinstance(message.content, str):
        return message.content if message.content else None

    if isinstance(message.content, list):
        text_parts = [
            block["text"]
            for block in message.content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if text_parts:
            return "".join(text_parts)

    return None


def _message_id(message: Any) -> str | None:
    """メッセージIDを文字列で返す。IDがない場合はNone。"""
    message_id = getattr(message, "id", None)
    if message_id is None:
        return None
    return str(message_id)


def _message_signature(message: Any) -> tuple[str, str, str]:
    """
    IDがないメッセージ比較用のシグネチャを作る。

    同一ターン判定のフォールバック用途なので、reprベースで十分とする。
    """
    msg_type = getattr(message, "type", type(message).__name__)
    content = getattr(message, "content", None)
    tool_calls = getattr(message, "tool_calls", None)
    return (str(msg_type), repr(content), repr(tool_calls))


def _get_state_messages(agent: Any, thread_id: str) -> list[Any]:
    """チェックポイント上の現在メッセージを取得する。"""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = agent.get_state(config)
    except Exception:
        return []

    values = getattr(snapshot, "values", {})
    if not isinstance(values, dict):
        return []

    messages = values.get("messages", [])
    if isinstance(messages, list):
        return messages
    if isinstance(messages, tuple):
        return list(messages)
    return []


def _get_new_messages(previous_messages: Sequence[Any], current_messages: Sequence[Any]) -> list[Any]:
    """前状態との差分から、このターンで追加されたメッセージを抽出する。"""
    if not previous_messages:
        return list(current_messages)

    # 通常は append-only なので、先頭一致ならスライスで高速に差分抽出する。
    if len(current_messages) >= len(previous_messages):
        prefix_matches = True
        for prev, curr in zip(previous_messages, current_messages):
            prev_id = _message_id(prev)
            curr_id = _message_id(curr)
            if prev_id and curr_id:
                if prev_id != curr_id:
                    prefix_matches = False
                    break
            elif _message_signature(prev) != _message_signature(curr):
                prefix_matches = False
                break

        if prefix_matches:
            return list(current_messages[len(previous_messages):])

    # 要約などで履歴が再構成された場合は、ID優先 + シグネチャ補助で差分を取る。
    previous_ids = {_message_id(msg) for msg in previous_messages if _message_id(msg)}
    signature_counts = Counter(_message_signature(msg) for msg in previous_messages)
    new_messages: list[Any] = []

    for msg in current_messages:
        msg_id = _message_id(msg)
        if msg_id and msg_id not in previous_ids:
            new_messages.append(msg)
            continue

        signature = _message_signature(msg)
        if signature_counts[signature] > 0:
            signature_counts[signature] -= 1
        else:
            new_messages.append(msg)

    return new_messages


def _extract_new_response(result: dict, previous_messages: Sequence[Any]) -> str | None:
    """
    このターンで新規に追加されたAIメッセージのみから応答を抽出する。

    新規AIメッセージがない場合はNoneを返す。
    """
    if not isinstance(result, dict):
        return str(result)

    current_messages = result.get("messages")
    if not isinstance(current_messages, list):
        return None

    new_messages = _get_new_messages(previous_messages, current_messages)
    for msg in reversed(new_messages):
        if isinstance(msg, AIMessage):
            text = _extract_text_from_ai_message(msg)
            if text:
                return text

    return None


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
            text = _extract_text_from_ai_message(msg)
            if text:
                return text

    # AIMessageが見つからない場合は結果全体を文字列化
    return str(result)


def invoke_agent(agent, user_message: str, thread_id: str) -> AgentResponse:
    """
    エージェントにメッセージを送信し、応答を取得する。

    この関数は全エージェントで共通の対話処理を担当する。
    エージェントに設定されたミドルウェアが自動的に適用される。
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        previous_messages = _get_state_messages(agent, thread_id)

        # agent.invoke()でエージェントを実行する
        # 第1引数: メッセージを含む辞書。"messages"キーを使用
        # config: thread_idを指定することで、checkpointerで会話履歴を保存できる
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
        )

        # HumanInTheLoopMiddlewareによる割り込みを確認する
        # 承認が必要なツール実行前に、ミドルウェアが処理を中断する
        # 中断時は結果に"__interrupt__"キーが設定される
        if isinstance(result, dict) and "__interrupt__" in result:
            # 割り込み情報を取得する (ツール名、引数などが含まれる)
            interrupt_info = result["__interrupt__"][0].value if result["__interrupt__"] else {}
            # 新規に生成されたメッセージのみ対象にして、前ターンの再表示を防ぐ
            response_text = _extract_new_response(result, previous_messages)
            # 承認待ち状態として返す
            return AgentResponse(
                status="pending_approval",
                message=response_text,
                approval_info=interrupt_info,
            )

        # 通常の応答を抽出する
        # まず新規メッセージのみから抽出し、取れない場合は従来ロジックにフォールバック
        response_text = _extract_new_response(result, previous_messages)
        if response_text is None:
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
