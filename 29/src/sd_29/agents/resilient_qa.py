"""
シナリオ2: 信頼性・コスト管理を重視したプロダクションエージェント

無限ループ防止、コスト制御、エラー耐性のデモ

使用ミドルウェア:
- ModelCallLimitMiddleware: モデル呼び出し回数制限
- ToolCallLimitMiddleware: ツール呼び出し回数制限
- ModelFallbackMiddleware: モデルフォールバック
- ToolRetryMiddleware: ツールリトライ
- ModelRetryMiddleware: モデルリトライ
"""

import random

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

# =============================================================================
# 実行ログ（UI表示用）
# =============================================================================

EXECUTION_LOG: list[dict] = []


def log_event(event_type: str, message: str, details: dict | None = None) -> None:
    """実行イベントをログに記録"""
    EXECUTION_LOG.append({
        "type": event_type,
        "message": message,
        "details": details or {},
    })


def get_execution_log() -> list[dict]:
    """実行ログを取得"""
    return EXECUTION_LOG


def clear_execution_log() -> None:
    """実行ログをクリア"""
    EXECUTION_LOG.clear()


# =============================================================================
# モックデータ
# =============================================================================

MOCK_WEB_RESULTS = {
    "python": "Pythonは汎用プログラミング言語で、シンプルな文法と豊富なライブラリが特徴です。",
    "langchain": "LangChainはLLMアプリケーション開発のためのフレームワークで、エージェント、チェーン、メモリなどの機能を提供します。",
    "ai": "人工知能(AI)は機械学習、深層学習、自然言語処理などの技術を含む広い分野です。",
    "default": "検索結果: 関連する情報が見つかりました。詳細については専門的な資料をご参照ください。",
}

MOCK_DATABASE = {
    "users": [
        {"id": 1, "name": "田中太郎", "department": "開発部"},
        {"id": 2, "name": "山田花子", "department": "営業部"},
        {"id": 3, "name": "鈴木一郎", "department": "経理部"},
    ],
    "products": [
        {"id": 101, "name": "製品A", "price": 10000},
        {"id": 102, "name": "製品B", "price": 20000},
        {"id": 103, "name": "製品C", "price": 15000},
    ],
    "sales": [
        {"product_id": 101, "quantity": 50, "date": "2025-12"},
        {"product_id": 102, "quantity": 30, "date": "2025-12"},
        {"product_id": 103, "quantity": 45, "date": "2025-12"},
    ],
}


# =============================================================================
# ツール定義（ランダム失敗機能付き）
# =============================================================================


@tool
def search_web(query: str) -> str:
    """
    Web検索を実行します。

    Args:
        query: 検索クエリ

    Returns:
        検索結果

    Note:
        このツールは30%の確率で失敗します（ネットワークエラーのシミュレーション）
    """
    # 30%の確率で失敗
    if random.random() < 0.3:
        log_event("error", "search_web失敗: ネットワークエラー", {"query": query})
        raise ConnectionError("ネットワーク接続エラー: 検索サービスに接続できませんでした")

    log_event("success", "search_web成功", {"query": query})

    # クエリに含まれるキーワードで検索結果を返す
    query_lower = query.lower()
    for keyword, result in MOCK_WEB_RESULTS.items():
        if keyword in query_lower:
            return result
    return MOCK_WEB_RESULTS["default"]


@tool
def query_database(sql: str) -> str:
    """
    データベースクエリを実行します。

    Args:
        sql: SQLクエリ（簡易形式: "SELECT * FROM テーブル名"）

    Returns:
        クエリ結果

    Note:
        このツールは20%の確率で失敗します（DB接続エラーのシミュレーション）
    """
    # 20%の確率で失敗
    if random.random() < 0.2:
        log_event("error", f"query_database失敗: DB接続エラー", {"sql": sql})
        raise ConnectionError("データベース接続エラー: 一時的に接続できません")

    log_event("success", f"query_database成功", {"sql": sql})

    # 簡易SQLパース
    sql_lower = sql.lower()
    if "users" in sql_lower:
        return f"ユーザーテーブルの結果:\n{MOCK_DATABASE['users']}"
    elif "products" in sql_lower:
        return f"製品テーブルの結果:\n{MOCK_DATABASE['products']}"
    elif "sales" in sql_lower:
        return f"売上テーブルの結果:\n{MOCK_DATABASE['sales']}"
    else:
        return "クエリを実行しました。結果: 0件"


@tool
def analyze_data(data: str) -> str:
    """
    データを分析して洞察を提供します。

    Args:
        data: 分析対象のデータ（テキスト形式）

    Returns:
        分析結果
    """
    log_event("success", "analyze_data成功", {"data_length": len(data)})

    # シンプルな分析結果を返す
    return f"""
データ分析結果:
- 入力データ長: {len(data)}文字
- 分析タイプ: 基本統計分析
- 結論: データは正常に処理されました。詳細な分析には追加のコンテキストが必要です。
"""


# =============================================================================
# エージェント作成
# =============================================================================


def create_resilient_qa_agent():
    """
    信頼性・コスト管理を重視したプロダクションエージェントを作成
    """
    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=[search_web, query_database, analyze_data],
        system_prompt="""あなたは信頼性の高いQAアシスタントです。

主な機能:
- Web検索による情報収集 (search_web)
- データベースクエリの実行 (query_database)
- データ分析 (analyze_data)

特徴:
- ツールがエラーを返した場合は自動的にリトライされます
- モデルエラーの場合は代替モデルにフォールバックします
- 呼び出し回数には制限があり、無限ループを防止します

注意事項:
- 効率的にツールを使用してください
- 必要な情報を得たら回答をまとめてください
- 日本語で丁寧に対応してください
""",
        checkpointer=InMemorySaver(),
        middleware=[
            # モデル呼び出し制限: 1リクエストあたり最大5回
            ModelCallLimitMiddleware(run_limit=5, exit_behavior="end"),
            # ツール呼び出し制限: セッション全体で10回、リクエストあたり10回
            ToolCallLimitMiddleware(thread_limit=10, run_limit=10),
            # search_webツールの個別制限: リクエストあたり3回まで
            ToolCallLimitMiddleware(tool_name="search_web", run_limit=3),
            # モデルフォールバック: claude-sonnet-4-5 → claude-haiku-4-5
            ModelFallbackMiddleware("anthropic:claude-haiku-4-5"),
            # ツールリトライ: 最大2回、指数バックオフ
            ToolRetryMiddleware(max_retries=2, backoff_factor=2.0, initial_delay=1.0),
            # モデルリトライ: 最大2回、指数バックオフ
            ModelRetryMiddleware(max_retries=2, backoff_factor=2.0),
        ],
    )

    return agent


# =============================================================================
# メトリクス取得関数
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
