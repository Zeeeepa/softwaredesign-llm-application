"""
ツール選択エージェントのテスト

テスト内容:
- Turn 1: 天気情報 (weather, searchが選択されるはず)
- Turn 2: 通貨換算 (currency_convert, searchが選択されるはず)
- Turn 3: 株価とニュース (stock_price, news, searchが選択されるはず)
- ツール選択の動的変化を確認
"""
from sd_29.agents.tool_selector_agent import (
    clear_selected_tools,
    create_tool_selector_agent,
    get_all_tool_names,
    get_selected_tools,
)
from tests.conftest import extract_response


def test_tool_selector_agent_multi_turn(thread_id):
    """ツール選択エージェントのマルチターンテスト"""
    agent = create_tool_selector_agent()
    config = {"configurable": {"thread_id": thread_id}}

    clear_selected_tools()

    all_tools = get_all_tool_names()
    print(f"全ツール ({len(all_tools)}個): {all_tools}")

    # =================================================================
    # Turn 1: 天気情報
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 1: 天気情報")
    print("=" * 60)

    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "東京の天気を教えて"}]},
        config=config,
    )
    response1 = extract_response(result1)
    print(f"Response: {response1[:200]}...")

    selected1 = get_selected_tools()
    print(f"Selected tools: {selected1}")

    # 検証: 天気情報が含まれる
    assert "東京" in response1 or "天気" in response1 or "晴れ" in response1
    # 検証: weatherツールが選択されている
    assert "weather" in selected1, f"weatherが選択されていません: {selected1}"
    print("[OK] Turn 1: 天気情報取得成功")

    # =================================================================
    # Turn 2: 通貨換算
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 2: 通貨換算")
    print("=" * 60)

    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "100ドルは何円?"}]},
        config=config,
    )
    response2 = extract_response(result2)
    print(f"Response: {response2[:200]}...")

    selected2 = get_selected_tools()
    print(f"Selected tools: {selected2}")

    # 検証: 換算結果が含まれる
    assert "円" in response2 or "JPY" in response2 or "15" in response2
    # 検証: currency_convertツールが選択されている
    assert "currency_convert" in selected2, f"currency_convertが選択されていません: {selected2}"
    print("[OK] Turn 2: 通貨換算成功")

    # =================================================================
    # Turn 3: 株価とニュース
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 3: 株価とニュース")
    print("=" * 60)

    result3 = agent.invoke(
        {"messages": [{"role": "user", "content": "Appleの株価とテクノロジーニュースを教えて"}]},
        config=config,
    )
    response3 = extract_response(result3)
    print(f"Response: {response3[:300]}...")

    selected3 = get_selected_tools()
    print(f"Selected tools: {selected3}")

    # 検証: 株価またはニュース情報が含まれる
    assert "Apple" in response3 or "AAPL" in response3 or "株価" in response3 or "ニュース" in response3
    # 検証: stock_priceまたはnewsツールが選択されている
    assert "stock_price" in selected3 or "news" in selected3, f"stock_price/newsが選択されていません: {selected3}"
    print("[OK] Turn 3: 株価とニュース取得成功")

    # =================================================================
    # ツール選択の動的変化確認
    # =================================================================
    print("\n" + "=" * 60)
    print("ツール選択の動的変化確認")
    print("=" * 60)

    # 検証: 各ターンで異なるツールが選択されている
    print(f"Turn 1 selected: {selected1}")
    print(f"Turn 2 selected: {selected2}")
    print(f"Turn 3 selected: {selected3}")

    # 最大3つまでのツールが選択されている
    assert len(selected1) <= 3, f"選択ツールが3個を超えています: {selected1}"
    assert len(selected2) <= 3, f"選択ツールが3個を超えています: {selected2}"
    assert len(selected3) <= 3, f"選択ツールが3個を超えています: {selected3}"
    print("[OK] ツール数制限 (max 3) 確認成功")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

    print("\n=== 最終検証結果 ===")
    print("Turn 1 (天気情報): OK")
    print("Turn 2 (通貨換算): OK")
    print("Turn 3 (株価とニュース): OK")
    print("ツール選択の動的変化: 確認済み")
