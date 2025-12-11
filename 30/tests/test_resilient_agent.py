"""
レジリエンスエージェントのテスト

テスト内容:
- Turn 1: Web検索 (リトライ動作確認)
- Turn 2: データベースクエリ
- Turn 3: データ分析
- メトリクス確認
"""
from sd_30.agents.resilient_agent import (
    clear_execution_log,
    create_resilient_agent,
    get_execution_log,
    get_metrics,
)
from tests.conftest import extract_response


def test_resilient_agent_multi_turn(thread_id):
    """レジリエンスエージェントのマルチターンテスト"""
    agent = create_resilient_agent()
    config = {"configurable": {"thread_id": thread_id}}

    clear_execution_log()

    # =================================================================
    # Turn 1: Web検索
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 1: Web検索")
    print("=" * 60)

    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "Pythonについて検索して"}]},
        config=config,
    )
    response1 = extract_response(result1)
    print(f"Response: {response1[:200]}...")

    # 検証: Python関連の情報が含まれる
    assert "Python" in response1 or "プログラミング" in response1 or "言語" in response1
    print("[OK] Turn 1: Web検索成功")

    # 実行ログ確認
    log = get_execution_log()
    print(f"Execution log: {len(log)} events")
    for event in log:
        print(f"  - [{event['type']}] {event['message']}")

    # =================================================================
    # Turn 2: データベースクエリ
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 2: データベースクエリ")
    print("=" * 60)

    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "ユーザー一覧をデータベースから取得して"}]},
        config=config,
    )
    response2 = extract_response(result2)
    print(f"Response: {response2[:300]}...")

    # 検証: ユーザー情報が含まれる
    assert "田中" in response2 or "山田" in response2 or "鈴木" in response2 or "ユーザー" in response2
    print("[OK] Turn 2: データベースクエリ成功")

    # =================================================================
    # Turn 3: データ分析
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 3: データ分析")
    print("=" * 60)

    result3 = agent.invoke(
        {"messages": [{"role": "user", "content": "製品の売上データを分析して"}]},
        config=config,
    )
    response3 = extract_response(result3)
    print(f"Response: {response3[:300]}...")

    # 検証: 分析結果が含まれる
    assert "分析" in response3 or "製品" in response3 or "売上" in response3
    print("[OK] Turn 3: データ分析成功")

    # =================================================================
    # メトリクス確認
    # =================================================================
    print("\n" + "=" * 60)
    print("メトリクス確認")
    print("=" * 60)

    metrics = get_metrics()
    print(f"Total events: {metrics['total_events']}")
    print(f"Success: {metrics['success_count']}")
    print(f"Error: {metrics['error_count']}")
    print(f"Success rate: {metrics['success_rate']:.1f}%")

    # 検証: 何らかのイベントが記録されている
    assert metrics["total_events"] > 0, "実行ログが空です"
    print("[OK] メトリクス取得成功")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

    print("\n=== 最終検証結果 ===")
    print("Turn 1 (Web検索): OK")
    print("Turn 2 (データベースクエリ): OK")
    print("Turn 3 (データ分析): OK")
    print(f"メトリクス: {metrics}")
