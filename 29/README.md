# LangChain Middleware デモアプリケーション

LangChainのミドルウェア機能を実演する3つのサンプルアプリケーションです。

## セットアップ

```bash
cd 29
uv sync
cp .env.sample .env
# .envにAPIキーを設定
```

## 起動

```bash
uv run python run.py
```

## シナリオ

### シナリオ1: メール処理エージェント

個人情報のフィルタリング、会話履歴の要約、人間による承認フローのデモ。

**使用ミドルウェア:**
- `PIIMiddleware`: メールアドレス・電話番号のマスキング
- `SummarizationMiddleware`: 長い履歴の自動要約
- `HumanInTheLoopMiddleware`: メール送信前の承認

### シナリオ2: レジリエンスエージェント

無限ループ防止、コスト制御、エラー耐性のデモ。

**使用ミドルウェア:**
- `ModelCallLimitMiddleware`: モデル呼び出し回数制限
- `ToolCallLimitMiddleware`: ツール呼び出し回数制限
- `ModelFallbackMiddleware`: モデルフォールバック
- `ToolRetryMiddleware` / `ModelRetryMiddleware`: 自動リトライ

### シナリオ3: ツール選択エージェント

LLMによる動的ツール選択のデモ。

**使用ミドルウェア:**
- `LLMToolSelectorMiddleware`: 12個のツールから最適な3つを自動選択

## ファイル構成

```
29/
├── src/sd_29/
│   ├── app.py                    # Streamlit メインUI
│   └── agents/
│       ├── email_assistant.py    # シナリオ1
│       ├── resilient_qa.py       # シナリオ2
│       └── tool_selector.py      # シナリオ3
├── run.py
├── pyproject.toml
└── .env.sample
```
