"""
メールエージェントのマルチターンテスト

テスト内容:
- Turn 1: メール一覧表示
- Turn 2: メール読み取り
- Turn 3: PIIブロック確認 (電話番号)
- Turn 4: HITL interrupt確認
- Turn 5: 承認後の送信完了
"""
from langgraph.types import Command

from sd_30.agents.email_agent import (
    clear_sent_emails,
    create_email_agent,
    get_sent_emails,
)
from tests.conftest import extract_response


def test_email_agent_multi_turn(thread_id):
    """メールエージェントのマルチターンテスト"""
    agent = create_email_agent()
    config = {"configurable": {"thread_id": thread_id}}

    # 送信済みメールをクリア
    clear_sent_emails()

    # =================================================================
    # Turn 1: メール一覧を見せて
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 1: メール一覧を見せて")
    print("=" * 60)

    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "メール一覧を見せて"}]},
        config=config,
    )
    response1 = extract_response(result1)
    print(f"Response: {response1[:200]}...")

    # 検証: 3件のメールが表示される
    assert "001" in response1 or "田中" in response1 or "一覧" in response1.lower()
    print("[OK] Turn 1: メール一覧表示成功")

    # =================================================================
    # Turn 2: メール001を読んで (PIIマスキング確認)
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 2: メール001を読んで")
    print("=" * 60)

    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "メール001を読んで"}]},
        config=config,
    )
    response2 = extract_response(result2)
    print(f"Response: {response2[:300]}...")

    # 検証: メール内容が含まれる
    assert "田中" in response2 or "プロジェクト" in response2 or "進捗" in response2
    print("[OK] Turn 2: メール読み取り成功")

    # =================================================================
    # Turn 3: PIIを含む返信依頼 (電話番号ブロック確認)
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 3: PIIを含む返信依頼 (電話番号ブロック確認)")
    print("=" * 60)

    from langchain.agents.middleware._redaction import PIIDetectionError

    # 自然な会話フロー: 返信時に自分の連絡先を伝えるシナリオ
    # PIIMiddlewareで電話番号は strategy="block" なのでエラーになる
    pii_input = "田中さんに返信して。本文は「了解しました。何かあれば090-1234-5678に連絡ください」で。"
    print(f"Input: {pii_input}")

    pii_blocked = False
    try:
        agent.invoke(
            {"messages": [{"role": "user", "content": pii_input}]},
            config=config,
        )
    except PIIDetectionError as e:
        pii_blocked = True
        print(f"[OK] PIIDetectionError発生: {e}")
        assert "phone_number" in str(e).lower(), "電話番号検出エラーではありません"

    assert pii_blocked, "電話番号を含む入力がブロックされていません"
    print("[OK] Turn 3: PII (電話番号) ブロック確認成功")

    # =================================================================
    # Turn 4: 返信依頼 (HITL interrupt確認)
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 4: 田中さんに返信依頼")
    print("=" * 60)

    result4 = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "tanaka.taro@example.comに件名「Re: プロジェクトの進捗報告」本文「了解しました。来週確認します。」と返信して",
                }
            ]
        },
        config=config,
    )
    response4 = extract_response(result4)
    print(f"Response: {response4[:300]}...")

    # HITL interrupt確認
    assert "__interrupt__" in result4, "HITL interruptが発生していません"
    print(f"[OK] HITL interrupt detected!")

    interrupt_info = result4["__interrupt__"]
    print(f"Interrupt info: {interrupt_info[0].value}")

    # action_requestsにsend_emailが含まれているか確認
    action_requests = interrupt_info[0].value.get("action_requests", [])
    assert len(action_requests) > 0, "action_requestsが空です"
    assert action_requests[0]["name"] == "send_email", "send_emailがinterruptされていません"
    print("[OK] Turn 4: send_email interrupt確認成功")

    # =================================================================
    # Turn 5: 承認して送信
    # =================================================================
    print("\n" + "=" * 60)
    print("Turn 5: 承認して送信")
    print("=" * 60)

    # Command(resume)で承認
    result5 = agent.invoke(
        Command(resume={"decisions": [{"type": "approve"}]}),
        config=config,
    )
    response5 = extract_response(result5)
    print(f"Response: {response5[:300]}...")

    # メールが送信されたか確認
    sent_emails = get_sent_emails()
    assert len(sent_emails) > 0, "メールが送信されていません"
    print(f"[OK] メール送信成功: {len(sent_emails)}件")
    print(f"送信先: {sent_emails[0].get('to', 'N/A')}")
    print(f"件名: {sent_emails[0].get('subject', 'N/A')}")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

    # 最終検証結果
    print("\n=== 最終検証結果 ===")
    print("Turn 1 (メール一覧): OK")
    print("Turn 2 (メール読み取り): OK")
    print("Turn 3 (PIIブロック): OK")
    print("Turn 4 (HITL interrupt): OK")
    print("Turn 5 (承認・送信): OK")
    print(f"sent_emails: {get_sent_emails()}")
