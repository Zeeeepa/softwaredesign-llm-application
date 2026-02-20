"""controllers.base のユニットテスト"""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from sd_31.agents import AgentResponse
from sd_31.controllers import invoke_agent
from sd_31.pages.scenario1 import _apply_agent_response_to_state


class FakeAgent:
    """invoke/get_state の最小実装を持つテスト用エージェント"""

    def __init__(self, state_messages, invoke_result):
        self._state_messages = state_messages
        self._invoke_result = invoke_result

    def get_state(self, config):
        return SimpleNamespace(values={"messages": self._state_messages})

    def invoke(self, payload, config):
        return self._invoke_result


def _build_interrupt(action_requests: list[dict]) -> list[SimpleNamespace]:
    return [SimpleNamespace(value={"action_requests": action_requests})]


def test_invoke_agent_interrupt_without_new_ai_message_returns_none(thread_id):
    previous_messages = [
        HumanMessage(content="メール001を読んで", id="human-1"),
        AIMessage(content="メール001の内容を表示しました。", id="ai-1"),
    ]

    result = {
        "messages": [
            *previous_messages,
            HumanMessage(content="田中さんに『了解しました』と返信して", id="human-2"),
        ],
        "__interrupt__": _build_interrupt(
            [{"name": "send_email", "args": {"recipient": "tanaka@example.com"}}]
        ),
    }
    agent = FakeAgent(previous_messages, result)

    response = invoke_agent(agent, "田中さんに『了解しました』と返信して", thread_id)

    assert response.status == "pending_approval"
    assert response.message is None
    assert response.approval_info is not None


def test_invoke_agent_interrupt_with_new_ai_message_returns_that_message(thread_id):
    previous_messages = [
        HumanMessage(content="メール001を読んで", id="human-1"),
        AIMessage(content="メール001の内容を表示しました。", id="ai-1"),
    ]

    new_ai_message = AIMessage(content="送信内容を確認してください。", id="ai-2")
    result = {
        "messages": [
            *previous_messages,
            HumanMessage(content="田中さんに返信して", id="human-2"),
            new_ai_message,
        ],
        "__interrupt__": _build_interrupt(
            [{"name": "send_email", "args": {"recipient": "tanaka@example.com"}}]
        ),
    }
    agent = FakeAgent(previous_messages, result)

    response = invoke_agent(agent, "田中さんに返信して", thread_id)

    assert response.status == "pending_approval"
    assert response.message == "送信内容を確認してください。"


def test_apply_agent_response_to_state_does_not_append_assistant_when_message_is_none():
    state = {
        "messages": [
            {"role": "assistant", "content": "メール001の内容を表示しました。"},
        ],
        "pending_approval": None,
    }
    approval_info = {"action_requests": [{"name": "send_email", "args": {}}]}
    response = AgentResponse(
        status="pending_approval",
        message=None,
        approval_info=approval_info,
    )

    _apply_agent_response_to_state(state, "田中さんに『了解しました』と返信して", response)

    assert state["messages"] == [
        {"role": "assistant", "content": "メール001の内容を表示しました。"},
        {"role": "user", "content": "田中さんに『了解しました』と返信して"},
    ]
    assert state["pending_approval"] == approval_info
