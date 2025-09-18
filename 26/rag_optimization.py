"""
RAG最適化スクリプト
"""

import os
import random
import dspy # type: ignore
from datetime import datetime

from config import configure_lm, configure_embedder, SMART_MODEL, FAST_MODEL
from rag_module import RAGQA
from dataset_loader import load_jqara_dataset
from evaluator import evaluation

# 最適化されたモデルの保存先（最新版へのリンク）
OPTIMIZED_MODEL_LATEST = "artifact/rag_optimized_latest.json"


def main():
    """メイン実行関数"""

    # データセット読み込み（devセットを使用）
    examples, corpus_texts = load_jqara_dataset(num_questions=50, dataset_split='dev')

    # Train/Val分割（50:50）
    random.seed(7)
    random.shuffle(examples)
    split = int(len(examples) * 0.5)
    trainset = examples[:split]
    valset = examples[split:]
    print(f"✂️ データ分割 (dev): train={len(trainset)}, val={len(valset)}")

    # testセット読み込み（30問）
    testset, test_corpus_texts = load_jqara_dataset(num_questions=30, dataset_split='test')

    # LM設定
    print("\n🔧 モデル設定中...")
    # 最適化用（高性能モデル）
    smart_lm = configure_lm(SMART_MODEL, temperature=0.0, max_tokens=4096)
    # 推論用（高速モデル）
    fast_lm = configure_lm(FAST_MODEL, temperature=0.0, max_tokens=1000)

    # 埋め込みモデル設定
    embedder = configure_embedder()

    # Retrieverの構築（devセットから得られたコーパスを使用）
    print("🔍 検索システムを構築中...")
    retriever = dspy.retrievers.Embeddings(
        embedder=embedder,
        corpus=corpus_texts,
        k=10  # 検索結果数
    )

    # DSPyで使用するデフォルトを設定
    dspy.configure(lm=fast_lm, rm=retriever)

    # ベースライン評価（testセットで評価）
    print("\n📊 ベースライン評価中...")
    baseline = RAGQA()
    base_results = evaluation(baseline, examples=testset, corpus_texts=test_corpus_texts, display_table=0)

    # MIPROv2最適化
    print("\n🚀 MIPROv2最適化を開始...")

    # 最適化対象のRAGモジュール
    rag = RAGQA()

    # 評価メトリクス（Exact Matchを使用）
    def metric(gold, pred, trace=None):
        """完全一致スコアを返すメトリクス"""
        # goldは例、predは予測結果
        pred_answer = pred.answer if hasattr(pred, 'answer') else ""
        gold_answer = gold.answer if hasattr(gold, 'answer') else ""
        return float(pred_answer.strip() == gold_answer.strip())

    # MIPROv2の設定
    optimizer = dspy.MIPROv2(
        metric=metric,
        prompt_model=smart_lm,
        auto="medium",
    )

    # 最適化実行（RAGの推論はfast_lm、プロンプト生成はsmart_lmを使用）
    optimized_rag = optimizer.compile(
        rag,
        trainset=trainset,
        valset=valset,
    )

    # 最適化後の評価（testセット）
    print("\n📊 最適化後の評価中...")
    opt_results = evaluation(optimized_rag, examples=testset, corpus_texts=test_corpus_texts, display_table=0)
    print(f"  [Baseline] EM: {base_results.score:.1f}%")
    print(f"  [Optimized] EM: {opt_results.score:.1f}%")
    print(f"  改善: {opt_results.score - base_results.score:+.1f}%")

    # タイムスタンプとスコアを含むファイル名生成（testセットのスコアを使用）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    em_score_str = f"em{int(opt_results.score):03d}"
    model_filename = f"rag_optimized_{timestamp}_{em_score_str}.json"
    model_path = os.path.join("artifact", model_filename)

    # モデルの保存
    os.makedirs("artifact", exist_ok=True)
    optimized_rag.save(model_path)
    print(f"\n💾 最適化済みモデルを保存: {model_path}")

    # 最新版へのシンボリックリンク作成
    if os.path.exists(OPTIMIZED_MODEL_LATEST):
        os.remove(OPTIMIZED_MODEL_LATEST)
    os.symlink(model_filename, OPTIMIZED_MODEL_LATEST)

    print(f"  → 最新リンク: {OPTIMIZED_MODEL_LATEST}")


if __name__ == "__main__":
    main()