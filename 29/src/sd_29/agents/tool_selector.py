"""
シナリオ4: 多数のツールを扱うエージェントでのツール選択最適化

LLMによる動的ツール選択のデモ

使用ミドルウェア:
- LLMToolSelectorMiddleware: LLMを使った事前ツール選択
"""

from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware
from langchain.tools import tool

# =============================================================================
# 選択されたツール記録
# =============================================================================

# 最後に選択されたツール（UI表示用）
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
            # 選択後のツール名を記録
            selected_tool_names = [t.name for t in modified_request.tools]
            _selected_tools.clear()
            _selected_tools.extend(selected_tool_names)
            return call_next(modified_request)

        return super().wrap_model_call(request, logging_call_next)


# =============================================================================
# 12個のモックツール定義
# =============================================================================


@tool
def calculator(expression: str) -> str:
    """
    数式を計算します。四則演算、べき乗、平方根などをサポートします。

    Args:
        expression: 計算式（例: "2 + 3 * 4", "sqrt(16)", "2**10"）

    Returns:
        計算結果
    """
    try:
        # 安全な評価のために許可する関数を制限
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
    指定した都市の天気を取得します。

    Args:
        city: 都市名（例: "東京", "大阪", "福岡"）

    Returns:
        天気情報
    """
    # モック天気データ
    weather_data = {
        "東京": {"temp": 12, "condition": "晴れ", "humidity": 45},
        "大阪": {"temp": 14, "condition": "曇り", "humidity": 55},
        "福岡": {"temp": 15, "condition": "晴れ時々曇り", "humidity": 50},
        "札幌": {"temp": -2, "condition": "雪", "humidity": 70},
        "那覇": {"temp": 22, "condition": "晴れ", "humidity": 65},
    }

    if city in weather_data:
        data = weather_data[city]
        return f"{city}の天気: {data['condition']}, 気温: {data['temp']}°C, 湿度: {data['humidity']}%"
    return f"{city}の天気情報は見つかりませんでした。対応都市: {list(weather_data.keys())}"


@tool
def search(query: str) -> str:
    """
    Web検索を実行します。一般的な情報検索に使用してください。

    Args:
        query: 検索キーワード

    Returns:
        検索結果
    """
    # モック検索結果
    return f"「{query}」の検索結果: 関連する情報が3件見つかりました。最も関連性の高い結果は技術文書とニュース記事です。"


@tool
def translate(text: str, target_lang: str) -> str:
    """
    テキストを指定した言語に翻訳します。

    Args:
        text: 翻訳するテキスト
        target_lang: 翻訳先言語（例: "en", "ja", "zh", "ko"）

    Returns:
        翻訳結果
    """
    # モック翻訳
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
    長いテキストを要約します。

    Args:
        text: 要約するテキスト

    Returns:
        要約結果
    """
    # モック要約
    word_count = len(text)
    return f"要約（元のテキスト: {word_count}文字）: テキストの主要なポイントを抽出しました。"


@tool
def calendar(date: str) -> str:
    """
    指定した日付のカレンダー情報を取得します。

    Args:
        date: 日付（例: "2025-12-10", "today"）

    Returns:
        カレンダー情報
    """
    # モックカレンダー
    events = {
        "2025-12-10": ["10:00 チームミーティング", "14:00 クライアント打ち合わせ"],
        "2025-12-11": ["09:00 朝会", "16:00 レビュー会議"],
        "2025-12-15": ["終日 システムメンテナンス"],
    }

    if date == "today":
        date = "2025-12-10"

    if date in events:
        return f"{date}の予定:\n" + "\n".join(f"- {e}" for e in events[date])
    return f"{date}には予定がありません。"


@tool
def stock_price(symbol: str) -> str:
    """
    株価情報を取得します。

    Args:
        symbol: 銘柄コード（例: "AAPL", "GOOGL", "7203.T"）

    Returns:
        株価情報
    """
    # モック株価データ
    stocks = {
        "AAPL": {"price": 195.50, "change": "+1.2%", "name": "Apple Inc."},
        "GOOGL": {"price": 175.30, "change": "-0.5%", "name": "Alphabet Inc."},
        "7203.T": {"price": 2850, "change": "+0.8%", "name": "トヨタ自動車"},
        "9984.T": {"price": 8500, "change": "+2.1%", "name": "ソフトバンクグループ"},
    }

    if symbol in stocks:
        data = stocks[symbol]
        return f"{data['name']} ({symbol}): ¥{data['price']:,.2f} ({data['change']})"
    return f"銘柄 '{symbol}' の情報は見つかりませんでした。"


@tool
def currency_convert(amount: float, from_cur: str, to_cur: str) -> str:
    """
    通貨を換算します。

    Args:
        amount: 金額
        from_cur: 換算元通貨（例: "JPY", "USD", "EUR"）
        to_cur: 換算先通貨

    Returns:
        換算結果
    """
    # モック為替レート（対USD）
    rates = {
        "JPY": 150.0,
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "CNY": 7.25,
    }

    if from_cur not in rates or to_cur not in rates:
        return f"通貨 '{from_cur}' または '{to_cur}' はサポートされていません。"

    usd_amount = amount / rates[from_cur]
    result = usd_amount * rates[to_cur]
    return f"{amount:,.2f} {from_cur} = {result:,.2f} {to_cur}"


@tool
def news(topic: str) -> str:
    """
    指定したトピックの最新ニュースを取得します。

    Args:
        topic: ニューストピック（例: "テクノロジー", "経済", "スポーツ"）

    Returns:
        ニュース記事一覧
    """
    # モックニュース
    news_data = {
        "テクノロジー": [
            "AI技術の最新動向: LLMの進化が加速",
            "クラウドコンピューティング市場が拡大",
        ],
        "経済": [
            "日銀の金融政策決定会合の結果",
            "円相場、150円台で推移",
        ],
        "スポーツ": [
            "サッカー日本代表、ワールドカップ予選突破",
            "大谷翔平選手、MVPを受賞",
        ],
    }

    if topic in news_data:
        articles = news_data[topic]
        return f"「{topic}」の最新ニュース:\n" + "\n".join(f"- {a}" for a in articles)
    return f"「{topic}」に関するニュースが見つかりませんでした。"


@tool
def dictionary(word: str) -> str:
    """
    単語の意味を辞書で検索します。

    Args:
        word: 検索する単語

    Returns:
        単語の定義
    """
    # モック辞書
    definitions = {
        "AI": "Artificial Intelligence（人工知能）の略。人間の知能を模倣するコンピュータシステム。",
        "LLM": "Large Language Model（大規模言語モデル）の略。大量のテキストデータで訓練された言語モデル。",
        "API": "Application Programming Interface。ソフトウェア間の通信インターフェース。",
        "middleware": "ミドルウェア。アプリケーションとOSの間で動作するソフトウェア層。",
    }

    if word.upper() in definitions:
        return f"「{word}」の定義: {definitions[word.upper()]}"
    return f"「{word}」の定義が見つかりませんでした。"


@tool
def reminder(task: str, time: str) -> str:
    """
    リマインダーを設定します。

    Args:
        task: タスクの内容
        time: リマインダー時刻（例: "15:00", "明日 09:00"）

    Returns:
        設定確認
    """
    return f"リマインダーを設定しました: 「{task}」を {time} に通知します。"


@tool
def email_draft(to: str, subject: str, body: str) -> str:
    """
    メールの下書きを作成します。

    Args:
        to: 宛先メールアドレス
        subject: 件名
        body: 本文

    Returns:
        下書きの確認
    """
    return f"""
メール下書きを作成しました:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
宛先: {to}
件名: {subject}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{body}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# =============================================================================
# 全ツールリスト
# =============================================================================

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


def get_all_tool_names() -> list[str]:
    """全ツール名を取得"""
    return [t.name for t in ALL_TOOLS]


# =============================================================================
# エージェント作成
# =============================================================================


def create_tool_selector_agent():
    """
    ツール選択最適化エージェントを作成
    """
    agent = create_agent(
        model="anthropic:claude-sonnet-4-5",
        tools=ALL_TOOLS,
        system_prompt="""あなたは多機能アシスタントです。

利用可能なツール（12個）:
1. calculator - 数式計算
2. weather - 天気情報
3. search - Web検索
4. translate - テキスト翻訳
5. summarize - テキスト要約
6. calendar - カレンダー確認
7. stock_price - 株価情報
8. currency_convert - 通貨換算
9. news - ニュース取得
10. dictionary - 辞書検索
11. reminder - リマインダー設定
12. email_draft - メール下書き

重要:
- LLMToolSelectorMiddlewareにより、各質問に対して最大3つのツールが自動選択されます
- searchツールは常に利用可能です
- 回答の冒頭で「【使用ツール: weather, search】」のように使用したツールを明示してください
- 日本語で丁寧に対応してください
""",
        middleware=[
            # LLMによるツール選択: claude-haiku-4-5で事前に最大3つのツールを選択
            # LoggingToolSelectorMiddlewareで選択結果をSELECTED_TOOLSに記録
            LoggingToolSelectorMiddleware(
                model="anthropic:claude-haiku-4-5",
                max_tools=3,
                always_include=["search"],  # searchは常に含める
            )
        ],
    )

    return agent
