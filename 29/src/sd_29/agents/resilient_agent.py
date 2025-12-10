"""
レジリエンスエージェント

無限ループ防止、コスト制御、エラー耐性のデモ
"""

import json
import random
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


# モックデータを読み込み
def _load_mock_data() -> dict:
    mock_path = Path(__file__).parent.parent / "mock" / "resilient_agent.json"
    with open(mock_path, encoding="utf-8") as f:
        return json.load(f)


_MOCK_DATA = _load_mock_data()
_MOCK_WEB_RESULTS = _MOCK_DATA["web_results"]
_MOCK_DATABASE = _MOCK_DATA["database"]

# 実行ログ
_execution_log: list[dict] = []


def _log_event(event_type: str, message: str, details: dict | None = None) -> None:
    """イベントを記録"""
    _execution_log.append({
        "type": event_type,
        "message": message,
        "details": details or {},
    })


def get_execution_log() -> list[dict]:
    """実行ログを取得"""
    return _execution_log


def clear_execution_log() -> None:
    """実行ログをクリア"""
    _execution_log.clear()


# ツール定義
@tool
def search_web(query: str) -> str:
    """
    Web検索を実行する (30%の確率で失敗)

    Args:
        query: 検索クエリ

    Returns:
        検索結果
    """
    if random.random() < 0.3:
        _log_event("error", "search_web失敗: ネットワークエラー", {"query": query})
        raise ConnectionError("ネットワーク接続エラー: 検索サービスに接続できません")

    _log_event("success", "search_web成功", {"query": query})

    query_lower = query.lower()
    for keyword, result in _MOCK_WEB_RESULTS.items():
        if keyword in query_lower:
            return result
    return _MOCK_WEB_RESULTS["default"]


@tool
def query_database(sql: str) -> str:
    """
    データベースクエリを実行する (20%の確率で失敗)

    Args:
        sql: SQLクエリ (簡易形式: "SELECT * FROM テーブル名")

    Returns:
        クエリ結果
    """
    if random.random() < 0.2:
        _log_event("error", "query_database失敗: DB接続エラー", {"sql": sql})
        raise ConnectionError("データベース接続エラー: 一時的に接続できません")

    _log_event("success", "query_database成功", {"sql": sql})

    sql_lower = sql.lower()
    if "users" in sql_lower:
        return f"ユーザーテーブルの結果:\n{_MOCK_DATABASE['users']}"
    elif "products" in sql_lower:
        return f"製品テーブルの結果:\n{_MOCK_DATABASE['products']}"
    elif "sales" in sql_lower:
        return f"売上テーブルの結果:\n{_MOCK_DATABASE['sales']}"
    else:
        return "クエリを実行しました。結果: 0件"


@tool
def analyze_data(data: str) -> str:
    """
    データを分析する

    Args:
        data: 分析対象のデータ

    Returns:
        分析結果
    """
    _log_event("success", "analyze_data成功", {"data_length": len(data)})

    return f"""
データ分析結果:
- 入力データ長: {len(data)}文字
- 分析タイプ: 基本統計分析
- 結論: データは正常に処理されました
"""

RESILIENT_AGENT_SYSTEM_PROMPT = """あなたはレジリエンスエージェントです。
Web検索、データベースクエリ、データ分析ができます。
ツールエラーは自動リトライされ、モデルエラーは代替モデルにフォールバックします。
必ず日本語で対応してください。
""".strip()


def create_resilient_agent():
    """レジリエンスエージェントを作成"""
    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=[search_web, query_database, analyze_data],
        system_prompt=RESILIENT_AGENT_SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
        middleware=[
            # モデル呼び出し制限 (1リクエスト最大5回)
            ModelCallLimitMiddleware(run_limit=5, exit_behavior="end"),
            # ツール呼び出し制限 (セッション10回、リクエスト10回)
            ToolCallLimitMiddleware(thread_limit=10, run_limit=10),
            # search_web個別制限 (リクエスト3回まで)
            ToolCallLimitMiddleware(tool_name="search_web", run_limit=3),
            # モデルフォールバック
            ModelFallbackMiddleware("anthropic:claude-haiku-4-5"),
            # ツールリトライ (最大2回、指数バックオフ)
            ToolRetryMiddleware(max_retries=2, backoff_factor=2.0, initial_delay=1.0),
            # モデルリトライ (最大2回)
            ModelRetryMiddleware(max_retries=2, backoff_factor=2.0),
        ],
    )

    return agent

# =============================================================================
# Streamlitの画面向けユーティリティ関数
# =============================================================================

def get_metrics() -> dict:
    """実行メトリクスを取得"""
    log = get_execution_log()
    success_count = sum(1 for e in log if e["type"] == "success")
    error_count = sum(1 for e in log if e["type"] == "error")

    return {
        "total_events": len(log),
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": success_count / len(log) * 100 if log else 0,
    }
