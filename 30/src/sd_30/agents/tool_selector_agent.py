"""
ツール選択エージェント

LLMによる動的ツール選択のデモ
"""

import json
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware
from langchain.tools import tool


# モックデータを読み込み
def _load_mock_data() -> dict:
    mock_path = Path(__file__).parent.parent / "mock" / "tool_selector_agent.json"
    with open(mock_path, encoding="utf-8") as f:
        return json.load(f)


_MOCK_DATA = _load_mock_data()

# 選択されたツール記録
_selected_tools: list[str] = []


def get_selected_tools() -> list[str]:
    """選択されたツール一覧を取得"""
    return _selected_tools.copy()


def clear_selected_tools() -> None:
    """選択されたツールをクリア"""
    _selected_tools.clear()


class LoggingToolSelectorMiddleware(LLMToolSelectorMiddleware):
    """選択結果を記録するLLMToolSelectorMiddleware"""

    def wrap_model_call(self, request, call_next):
        def logging_call_next(modified_request):
            selected_tool_names = [t.name for t in modified_request.tools]
            _selected_tools.clear()
            _selected_tools.extend(selected_tool_names)
            return call_next(modified_request)

        return super().wrap_model_call(request, logging_call_next)


# ツール定義
@tool
def calculator(expression: str) -> str:
    """
    数式を計算する

    Args:
        expression: 計算式 (例: "2 + 3 * 4", "sqrt(16)")

    Returns:
        計算結果
    """
    try:
        import math

        allowed_names = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "abs": abs,
            "round": round,
            "pi": math.pi,
            "e": math.e,
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"計算結果: {expression} = {result}"
    except Exception as e:
        return f"計算エラー: {e}"


@tool
def weather(city: str) -> str:
    """
    都市の天気を取得する

    Args:
        city: 都市名 (例: "東京", "大阪")

    Returns:
        天気情報
    """
    weather_data = _MOCK_DATA["weather"]

    if city in weather_data:
        data = weather_data[city]
        return f"{city}の天気: {data['condition']}, 気温: {data['temp']}°C, 湿度: {data['humidity']}%"
    return f"{city}の天気情報は見つかりません。対応都市: {list(weather_data.keys())}"


@tool
def search(query: str) -> str:
    """
    Web検索を実行する

    Args:
        query: 検索キーワード

    Returns:
        検索結果
    """
    return f"「{query}」の検索結果: 関連する情報が3件見つかりました。"


@tool
def translate(text: str, target_lang: str) -> str:
    """
    テキストを翻訳する

    Args:
        text: 翻訳するテキスト
        target_lang: 翻訳先言語 (例: "en", "ja", "zh")

    Returns:
        翻訳結果
    """
    translations = {
        "en": f"[English Translation] {text[:50]}...",
        "ja": f"[日本語翻訳] {text[:50]}...",
        "zh": f"[中文翻译] {text[:50]}...",
        "ko": f"[한국어 번역] {text[:50]}...",
    }
    return translations.get(target_lang, f"言語 '{target_lang}' への翻訳: {text}")


@tool
def summarize(text: str) -> str:
    """
    テキストを要約する

    Args:
        text: 要約するテキスト

    Returns:
        要約結果
    """
    return f"要約 (元: {len(text)}文字): テキストの主要ポイントを抽出しました。"


@tool
def calendar(date: str) -> str:
    """
    カレンダー情報を取得する

    Args:
        date: 日付 (例: "2025-12-10", "today")

    Returns:
        カレンダー情報
    """
    calendar_data = _MOCK_DATA["calendar"]

    if date == "today":
        date = "2025-12-10"

    if date in calendar_data:
        return f"{date}の予定:\n" + "\n".join(f"- {e}" for e in calendar_data[date])
    return f"{date}には予定がありません。"


@tool
def stock_price(symbol: str) -> str:
    """
    株価情報を取得する

    Args:
        symbol: 銘柄コード (例: "AAPL", "7203.T")

    Returns:
        株価情報
    """
    stocks = _MOCK_DATA["stocks"]

    if symbol in stocks:
        data = stocks[symbol]
        return f"{data['name']} ({symbol}): ¥{data['price']:,.2f} ({data['change']})"
    return f"銘柄 '{symbol}' の情報は見つかりません。"


@tool
def currency_convert(amount: float, from_cur: str, to_cur: str) -> str:
    """
    通貨を換算する

    Args:
        amount: 金額
        from_cur: 換算元通貨 (例: "JPY", "USD")
        to_cur: 換算先通貨

    Returns:
        換算結果
    """
    rates = _MOCK_DATA["currency_rates"]

    if from_cur not in rates or to_cur not in rates:
        return f"通貨 '{from_cur}' または '{to_cur}' はサポートされていません。"

    usd_amount = amount / rates[from_cur]
    result = usd_amount * rates[to_cur]
    return f"{amount:,.2f} {from_cur} = {result:,.2f} {to_cur}"


@tool
def news(topic: str) -> str:
    """
    ニュースを取得する

    Args:
        topic: トピック (例: "テクノロジー", "経済")

    Returns:
        ニュース一覧
    """
    news_data = _MOCK_DATA["news"]

    if topic in news_data:
        articles = news_data[topic]
        return f"「{topic}」の最新ニュース:\n" + "\n".join(f"- {a}" for a in articles)
    return f"「{topic}」に関するニュースが見つかりません。"


@tool
def dictionary(word: str) -> str:
    """
    単語の意味を検索する

    Args:
        word: 検索する単語

    Returns:
        単語の定義
    """
    definitions = _MOCK_DATA["dictionary"]

    if word.upper() in definitions:
        return f"「{word}」の定義: {definitions[word.upper()]}"
    return f"「{word}」の定義が見つかりません。"


@tool
def reminder(task: str, time: str) -> str:
    """
    リマインダーを設定する

    Args:
        task: タスクの内容
        time: リマインダー時刻 (例: "15:00")

    Returns:
        設定確認
    """
    return f"リマインダー設定: 「{task}」を {time} に通知します。"


@tool
def email_draft(to: str, subject: str, body: str) -> str:
    """
    メール下書きを作成する

    Args:
        to: 宛先
        subject: 件名
        body: 本文

    Returns:
        下書き確認
    """
    return f"""
メール下書き作成:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
宛先: {to}
件名: {subject}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{body}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# 全ツール
ALL_TOOLS = [
    calculator,
    weather,
    search,
    translate,
    summarize,
    calendar,
    stock_price,
    currency_convert,
    news,
    dictionary,
    reminder,
    email_draft,
]

TOOL_SELECTOR_AGENT_SYSTEM_PROMPT = """あなたはツール選択エージェントです。
多機能アシスタントとして、質問に応じて適切なツールを選択してください。
回答の冒頭で【使用ツール: xxx】と明示してください。
必ず日本語で対応してください。
"""

def create_tool_selector_agent():
    """ツール選択エージェントを作成"""
    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=ALL_TOOLS,
        system_prompt=TOOL_SELECTOR_AGENT_SYSTEM_PROMPT,
        middleware=[
            # LLMで事前に最大3つのツールを選択
            LoggingToolSelectorMiddleware(
                model="anthropic:claude-haiku-4-5",
                max_tools=3,
                always_include=["search"],
            )
        ],
    )

    return agent

# =============================================================================
# Streamlitの画面向けユーティリティ関数
# =============================================================================

def get_all_tool_names() -> list[str]:
    """全ツール名を取得"""
    return [t.name for t in ALL_TOOLS]
