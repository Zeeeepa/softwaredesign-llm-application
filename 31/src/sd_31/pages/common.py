"""
共通ユーティリティ
"""

import uuid

import streamlit as st

SCENARIO_STATE_KEY = "scenario_state"


def init_session_state() -> None:
    """セッションの初期状態を設定"""
    if SCENARIO_STATE_KEY not in st.session_state:
        st.session_state[SCENARIO_STATE_KEY] = {}


def ensure_scenario_state(scenario_id: str) -> dict:
    """シナリオごとの状態を取得し、未初期化なら作成する"""
    init_session_state()
    scenario_state = st.session_state[SCENARIO_STATE_KEY]
    if scenario_id not in scenario_state:
        scenario_state[scenario_id] = {
            "messages": [],
            "thread_id": str(uuid.uuid4()),
            "pending_approval": None,
        }
    return scenario_state[scenario_id]


def reset_conversation(scenario_id: str) -> None:
    """指定シナリオの会話をリセット"""
    scenario = ensure_scenario_state(scenario_id)
    scenario["messages"] = []
    scenario["thread_id"] = str(uuid.uuid4())
    scenario["pending_approval"] = None
