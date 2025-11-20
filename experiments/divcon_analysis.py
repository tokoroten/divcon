#!/usr/bin/env python3
"""
DivCon: Division & Consensus Analysis
対立軸発見アルゴリズムのメインスクリプト

使用方法:
    python divcon_analysis.py

出力:
    - results/topics.json: 発見されたトピック
    - results/axes.json: 対立軸
    - results/anchors.json: 極端意見アンカー
    - results/scores.csv: 全意見のスコア
    - results/summary.txt: 統計サマリー
"""

import os
import json
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# UTF-8出力設定（Windows対応）
sys.stdout.reconfigure(encoding='utf-8')

# 並列処理設定
MAX_WORKERS = 10  # 並列実行数
print_lock = Lock()  # スレッドセーフな出力用

# 環境変数読み込み
load_dotenv()

# OpenAI クライアント初期化
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
MODEL = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
REASONING_EFFORT = os.getenv('REASONING_EFFORT', 'medium')

# 出力ディレクトリ
RESULTS_DIR = 'results'
os.makedirs(RESULTS_DIR, exist_ok=True)

print(f"DivCon Analysis")
print(f"=" * 60)
print(f"Model: {MODEL}")
print(f"Reasoning Effort: {REASONING_EFFORT}")
print(f"=" * 60)
print()


# ============================================================================
# Stage 1: トピック検出
# ============================================================================

class Topic(BaseModel):
    id: str
    name: str
    description: str

class TopicDiscoveryResponse(BaseModel):
    topics: List[Topic]
    reasoning: str


def stage1_topic_discovery(opinions, sample_size=500):
    """Stage 1: トピック検出（ランダムサンプリング版）"""
    # ランダムサンプリング
    if len(opinions) > sample_size:
        sampled_opinions = random.sample(opinions, sample_size)
        print(f"[Stage 1] トピック検出中... ({len(opinions)} 件から {sample_size} 件をサンプリング)")
    else:
        sampled_opinions = opinions
        print(f"[Stage 1] トピック検出中... ({len(opinions)} 件の意見)")

    # 意見テキストを結合
    opinions_text = "\n\n".join([f"[{op['id']}] {op['comment']}" for op in sampled_opinions])

    prompt = f"""以下は、エネルギー基本計画に対する市民意見です。

これらの意見を分析し、主要なトピック（議論の主題）を抽出してください。

【意見一覧】
{opinions_text}

【指示】
1. この中で議論されている主要なトピックは何ですか？
2. 最適なトピック数を自動で判断してください（3-7個程度を推奨）
3. 各トピックに明確な名前と説明を付けてください
"""

    completion = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": "あなたは市民意見を分析する専門家です。意見を読み、主要なトピックを抽出してください。"},
            {"role": "user", "content": prompt}
        ],
        reasoning_effort=REASONING_EFFORT,
        response_format=TopicDiscoveryResponse
    )

    result = completion.choices[0].message.parsed
    topics = [t.model_dump() for t in result.topics]

    print(f"[OK] {len(topics)} 個のトピックを検出")
    print(f"  理由: {result.reasoning}")
    for topic in topics:
        print(f"  - [{topic['id']}] {topic['name']}")
    print()

    return topics


# ============================================================================
# Stage 2: トピック分類
# ============================================================================

class Classification(BaseModel):
    opinion_id: str
    topic_id: str

class ClassificationResponse(BaseModel):
    classifications: List[Classification]


def stage2_classification(opinions, topics, batch_size=10):
    """Stage 2: トピック分類（並列処理版）"""
    print(f"[Stage 2] トピック分類中... (バッチサイズ: {batch_size}, 並列数: {MAX_WORKERS})")

    topics_text = "\n".join([f"[{t['id']}] {t['name']}: {t['description']}" for t in topics])

    def classify_batch(batch_info):
        """バッチを分類する関数（並列実行用）"""
        i, batch = batch_info
        batch_text = "\n".join([f"[{op['id']}] {op['comment']}" for op in batch])

        prompt = f"""以下のトピック定義があります:

{topics_text}

次の意見を、最も適切なトピックに分類してください:

{batch_text}

【重要】opinion_idとtopic_idは必ず上記のリストに存在するIDを使用してください。
"""

        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": "意見を適切なトピックに分類してください。指定されたIDのみを使用してください。"},
                {"role": "user", "content": prompt}
            ],
            reasoning_effort=REASONING_EFFORT,
            response_format=ClassificationResponse
        )

        result = completion.choices[0].message.parsed
        classifications = [c.model_dump() for c in result.classifications]

        with print_lock:
            print(f"  [OK] {i+1}-{i+len(batch)} 件を分類")

        return classifications

    # バッチを作成
    batches = [(i, opinions[i:i+batch_size]) for i in range(0, len(opinions), batch_size)]

    # 並列実行
    classified_opinions = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(classify_batch, batch_info) for batch_info in batches]
        for future in as_completed(futures):
            classified_opinions.extend(future.result())

    # 分類結果を元のデータに追加
    classification_map = {c['opinion_id']: c['topic_id'] for c in classified_opinions}
    for op in opinions:
        op['topic_id'] = classification_map.get(str(op['id']), None)

    # 統計
    valid_topic_ids = {t['id'] for t in topics}
    topic_counts = {}
    unclassified = 0

    for op in opinions:
        if op['topic_id'] is None:
            unclassified += 1
        elif op['topic_id'] in valid_topic_ids:
            topic_counts[op['topic_id']] = topic_counts.get(op['topic_id'], 0) + 1

    print(f"\n  分類結果:")
    for topic_id, count in topic_counts.items():
        topic_name = next(t['name'] for t in topics if t['id'] == topic_id)
        print(f"  - [{topic_id}] {topic_name}: {count} 件")

    if unclassified > 0:
        print(f"  - 未分類: {unclassified} 件 [WARNING]")
    print()

    return opinions


# ============================================================================
# Stage 3a: 対立軸の発見
# ============================================================================

class Axis(BaseModel):
    id: str
    name: str
    left_pole: str
    right_pole: str
    strength: int
    reasoning: str

class AxisDiscoveryResponse(BaseModel):
    axes: List[Axis]


def stage3a_axis_discovery(topic, topic_opinions, sample_size=500):
    """Stage 3a: 対立軸の発見（ランダムサンプリング版）"""
    # ランダムサンプリング
    if len(topic_opinions) > sample_size:
        sampled_opinions = random.sample(topic_opinions, sample_size)
        print(f"[Stage 3a] トピック [{topic['id']}] {topic['name']} の対立軸発見中... ({len(topic_opinions)} 件から {sample_size} 件をサンプリング)")
    else:
        sampled_opinions = topic_opinions
        print(f"[Stage 3a] トピック [{topic['id']}] {topic['name']} の対立軸発見中... ({len(topic_opinions)} 件)")

    topic_opinions_text = "\n\n".join([f"[{op['id']}] {op['comment']}" for op in sampled_opinions])

    prompt = f"""以下は、「{topic['name']}」というトピックに関する市民意見です。

{topic_opinions_text}

【タスク】
この意見群の中で、人々が**対立している軸**を発見してください。

対立軸とは:
- 意見が二極化している次元
- 「AかBか」という選択を迫られる論点
- 例: "環境保護 vs 経済成長", "短期的利益 vs 長期的持続性"

【指示】
1. 主要な対立軸を2-4個抽出してください
2. 各軸に明確な名前を付けてください（"A vs B"の形式）
3. 対立の強度を5段階で評価してください：
   - 5: 非常に強い対立（意見が完全に二極化）
   - 4: 強い対立
   - 3: 中程度の対立
   - 2: やや対立
   - 1: 弱い対立
4. **重要**: reasoning（理由説明）で具体的な意見を参照する際は、必ず `[ID:XXX]` の形式を使用してください
   - 正しい例: "[ID:123]では再エネ推進を主張している"
   - 正しい例: "左極の代表例として[ID:456]、右極として[ID:789]が見られる"
   - 誤った例: "意見123では..." "ID123によると..." "コメント[123]"
"""

    completion = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": "あなたは対立構造を分析する専門家です。"},
            {"role": "user", "content": prompt}
        ],
        reasoning_effort=REASONING_EFFORT,
        response_format=AxisDiscoveryResponse
    )

    result = completion.choices[0].message.parsed
    axes = [a.model_dump() for a in result.axes]

    print(f"  [OK] {len(axes)} 個の対立軸を発見")
    strength_labels = ["", "弱い", "やや", "中程度", "強い", "非常に強い"]
    for axis in axes:
        print(f"  - [{axis['id']}] {axis['name']} (強度: {axis['strength']}/5 - {strength_labels[axis['strength']]}対立)")
    print()

    return axes


# ============================================================================
# Stage 3b: 極端意見アンカーの生成
# ============================================================================

class AnchorGenerationResponse(BaseModel):
    left_anchors: List[str]
    right_anchors: List[str]


def stage3b_anchor_generation(axis, topic_opinions, sample_size=500):
    """Stage 3b: 極端意見アンカーの生成（ランダムサンプリング版）"""
    print(f"[Stage 3b] 対立軸 [{axis['id']}] {axis['name']} のアンカー生成中...")

    # ランダムサンプリング
    if len(topic_opinions) > sample_size:
        sampled_opinions = random.sample(topic_opinions, sample_size)
    else:
        sampled_opinions = topic_opinions

    topic_opinions_text = "\n\n".join([f"[{op['id']}] {op['comment']}" for op in sampled_opinions])

    prompt = f"""以下の市民意見を参考にして、対立軸「{axis['name']}」について、
極端に強い主張の文章例を生成してください。

【既存の意見（参考）】
{topic_opinions_text}

【タスク】
- **左極**（{axis['left_pole']}）の極端な主張を10パターン生成
- **右極**（{axis['right_pole']}）の極端な主張を10パターン生成

【極端な文章の例】
例えば、対立軸が「環境保護 vs 経済成長」の場合：

左極（環境保護）の例:
- 「経済成長を完全に停止してでも、環境保護を最優先すべきである」
- 「全ての企業活動を即座に規制し、自然環境を元の状態に戻すべきだ」
- 「人間の経済活動は地球環境に対する犯罪であり、全面的に見直すべきである」

右極（経済成長）の例:
- 「環境規制を全て撤廃し、経済成長を最大化すべきである」
- 「環境保護は経済発展の後で考えればよく、今は成長が最優先だ」
- 「環境コストを無視してでも、産業競争力を強化すべきである」

【重要なポイント】
1. 既存の意見の文脈を保ちつつ、より極端な表現にすること
2. 「完全に」「全て」「絶対に」「即座に」などの強い表現を使用
3. 妥協や条件を一切含まない断定的な主張にすること
4. 各パターンは異なる角度から極端さを表現すること
5. 同じような主張の繰り返しは避けること
"""

    completion = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": "多様で極端な主張を生成してください。妥協のない、断定的な表現を使用してください。"},
            {"role": "user", "content": prompt}
        ],
        reasoning_effort="high",
        response_format=AnchorGenerationResponse
    )

    result = completion.choices[0].message.parsed
    anchors = {
        'left_anchors': result.left_anchors,
        'right_anchors': result.right_anchors
    }

    print(f"  [OK] アンカー生成完了 (左極: {len(anchors['left_anchors'])} 個, 右極: {len(anchors['right_anchors'])} 個)")
    print()

    return anchors


# ============================================================================
# Stage 4: 強度推定
# ============================================================================

class Score(BaseModel):
    opinion_id: str
    score: Optional[int] = None  # 1-6、または該当しない場合はnull
    excerpt: str  # 判断根拠となった本文の重要部分（切り抜きまたは要約）
    reasoning: str

class ScoringResponse(BaseModel):
    scores: List[Score]


def stage4_scoring(axis, anchors, topic_opinions, batch_size=20):
    """Stage 4: 強度推定（並列処理版）"""
    print(f"[Stage 4] 対立軸 [{axis['id']}] のスコアリング中... ({len(topic_opinions)} 件, 並列数: {MAX_WORKERS})")

    left_anchors_text = "\n".join([f"L{i+1}. {a}" for i, a in enumerate(anchors['left_anchors'])])
    right_anchors_text = "\n".join([f"R{i+1}. {a}" for i, a in enumerate(anchors['right_anchors'])])

    def score_batch(batch_info):
        """バッチをスコアリングする関数（並列実行用）"""
        i, batch = batch_info
        opinions_to_score = "\n\n".join([f"[{op['id']}] {op['comment']}" for op in batch])

        prompt = f"""以下の基準アンカーに基づいて、意見をスコアリングしてください。

【対立軸】{axis['name']}
- 左極（スコア1）: {axis['left_pole']}
- 右極（スコア5）: {axis['right_pole']}

【左極アンカー例】（スコア1に相当）
{left_anchors_text}

【右極アンカー例】（スコア5に相当）
{right_anchors_text}

【スコアリング対象の意見】
{opinions_to_score}

【タスク】
各意見を以下の基準でスコアリングしてください:

**まず、この対立軸に該当するかを判定:**
- 意見がこの対立軸について明確な立場を示している場合 → 1-6でスコアリング
- 意見がこの対立軸に全く言及していない、または判断できない場合 → scoreをnullにする

**スコアの意味（該当する場合）:**
6段階評価により、より明確な立場判定を行います。中立的なバランス点はありません。
- **1**: 左極（最も強い）- 左極アンカーに非常に近い立場
- **2**: 左寄り（強）- 左極に近いが、若干の留保がある
- **3**: 左寄り（弱）- 左寄りだが、やや穏健な立場
- **4**: 右寄り（弱）- 右寄りだが、やや穏健な立場
- **5**: 右寄り（強）- 右極に近いが、若干の留保がある
- **6**: 右極（最も強い）- 右極アンカーに非常に近い立場

**excerpt（重要部分の切り抜き）:**
- スコアを付けた場合: 判断の根拠となった本文の重要な部分を切り抜いて記載してください
  - **必ず「...」（日本語のカギ括弧）で囲んでください**。"..."（ダブルクオーテーション）は使用しないでください
  - 原文から直接引用する形式で記載してください
  - 長い場合は複数の重要箇所を抽出するか、要約してください
  - 目安: 50-150文字程度
  - フォーマット例: 「原発を最大限活用すべきである...再生可能エネルギーとの併用が重要だ」
- スコアがnullの場合: excerptは空文字列（""）にしてください

**重要**: 意見が対立軸に該当しない場合、無理にスコアを付けず、scoreフィールドをnullにしてください。
"""

        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": "アンカーを基準に意見をスコアリングしてください。"},
                {"role": "user", "content": prompt}
            ],
            reasoning_effort=REASONING_EFFORT,
            response_format=ScoringResponse
        )

        result = completion.choices[0].message.parsed
        scores = [s.model_dump() for s in result.scores]

        with print_lock:
            print(f"  [OK] {i+1}-{i+len(batch)} 件をスコアリング")

        return scores

    # バッチを作成
    batches = [(i, topic_opinions[i:i+batch_size]) for i in range(0, len(topic_opinions), batch_size)]

    # 並列実行
    all_scores = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(score_batch, batch_info) for batch_info in batches]
        for future in as_completed(futures):
            all_scores.extend(future.result())

    print(f"  [OK] スコアリング完了\n")

    return all_scores


# ============================================================================
# メイン処理
# ============================================================================

def main():
    """メイン処理"""
    start_time = datetime.now()

    # データ読み込み
    print("データ読み込み中...")
    df = pd.read_csv('data/opinions.csv')
    opinions = df.to_dict('records')
    print(f"[OK] {len(opinions)} 件の意見を読み込み\n")

    # Stage 1: トピック検出
    topics = stage1_topic_discovery(opinions)

    # 結果保存
    with open(f'{RESULTS_DIR}/topics.json', 'w', encoding='utf-8') as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)

    # Stage 2: トピック分類
    opinions = stage2_classification(opinions, topics)

    # 全トピックの対立軸とアンカーを保存
    all_axes = {}
    all_anchors = {}
    all_scores = []

    # ============================================================================
    # Stage 3a: 全トピックの対立軸発見を並列実行
    # ============================================================================
    print(f"\n[Stage 3a 並列実行] 全 {len(topics)} トピックの対立軸を並列発見中... (並列数: {MAX_WORKERS})\n")

    def discover_axes_for_topic(topic):
        """トピックの対立軸を発見（並列実行用）"""
        topic_opinions = [op for op in opinions if op.get('topic_id') == topic['id']]

        if len(topic_opinions) == 0:
            with print_lock:
                print(f"[WARNING] トピック [{topic['id']}] に属する意見がありません。スキップします。\n")
            return topic['id'], []

        axes = stage3a_axis_discovery(topic, topic_opinions)
        return topic['id'], axes

    # 並列実行
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(discover_axes_for_topic, topic) for topic in topics]
        for future in as_completed(futures):
            topic_id, axes = future.result()
            all_axes[topic_id] = axes

    # 軸IDを標準化（トピックID + 軸番号の形式に統一）
    print(f"[OK] 全トピックの対立軸発見完了")
    print(f"  軸IDを標準化中... (形式: T1_A1, T1_A2, ...)\n")

    for topic_id, axes in all_axes.items():
        for i, axis in enumerate(axes, 1):
            old_id = axis['id']
            new_id = f"{topic_id}_A{i}"
            axis['id'] = new_id
            print(f"  [{topic_id}] {old_id} → {new_id}")
    print()

    # ============================================================================
    # Stage 3b & 4: 全軸のアンカー生成とスコアリングを並列実行
    # ============================================================================
    # 全ての軸を収集
    all_axis_tasks = []
    for topic in topics:
        topic_opinions = [op for op in opinions if op.get('topic_id') == topic['id']]
        if topic['id'] in all_axes:
            for axis in all_axes[topic['id']]:
                all_axis_tasks.append({
                    'topic_id': topic['id'],
                    'topic_name': topic['name'],
                    'axis': axis,
                    'topic_opinions': topic_opinions
                })

    print(f"\n[Stage 3b & 4 並列実行] 全 {len(all_axis_tasks)} 軸のアンカー生成とスコアリングを並列実行中... (並列数: {MAX_WORKERS})\n")

    def process_axis(task):
        """軸のアンカー生成とスコアリング（並列実行用）"""
        axis = task['axis']
        topic_opinions = task['topic_opinions']
        topic_id = task['topic_id']

        # Stage 3b: アンカー生成
        anchors = stage3b_anchor_generation(axis, topic_opinions)

        # Stage 4: スコアリング
        scores = stage4_scoring(axis, anchors, topic_opinions)

        # 意見IDとコメントのマッピングを作成
        opinion_map = {str(op['id']): op['comment'] for op in topic_opinions}

        # スコアに追加情報を付与
        for score in scores:
            score['topic_id'] = topic_id
            score['axis_id'] = axis['id']
            score['axis_name'] = axis['name']
            score['comment'] = opinion_map.get(str(score['opinion_id']), '')

        return axis['id'], anchors, scores

    # 並列実行
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_axis, task) for task in all_axis_tasks]
        for future in as_completed(futures):
            axis_id, anchors, scores = future.result()
            all_anchors[axis_id] = anchors
            all_scores.extend(scores)

    print(f"[OK] 全軸の処理完了\n")

    # 結果保存
    print("結果を保存中...")

    # 対立軸
    with open(f'{RESULTS_DIR}/axes.json', 'w', encoding='utf-8') as f:
        json.dump(all_axes, f, ensure_ascii=False, indent=2)

    # アンカー
    with open(f'{RESULTS_DIR}/anchors.json', 'w', encoding='utf-8') as f:
        json.dump(all_anchors, f, ensure_ascii=False, indent=2)

    # スコア（CSV形式、列順序を指定）
    scores_df = pd.DataFrame(all_scores)
    column_order = ['opinion_id', 'comment', 'topic_id', 'axis_id', 'axis_name', 'score', 'excerpt', 'reasoning']
    scores_df = scores_df[column_order]
    scores_df = scores_df.sort_values(by=['axis_id', 'score'], na_position='last')
    scores_df.to_csv(f'{RESULTS_DIR}/scores.csv', index=False, encoding='utf-8-sig')

    # サマリー統計
    with open(f'{RESULTS_DIR}/summary.txt', 'w', encoding='utf-8') as f:
        f.write("DivCon Analysis Summary\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"総意見数: {len(opinions)} 件\n")
        f.write(f"トピック数: {len(topics)} 個\n")
        f.write(f"対立軸数: {sum(len(axes) for axes in all_axes.values())} 個\n")
        f.write(f"スコア数: {len(all_scores)} 件\n\n")

        f.write("トピック一覧:\n")
        for topic in topics:
            f.write(f"  - [{topic['id']}] {topic['name']}\n")
        f.write("\n")

        f.write("対立軸一覧:\n")
        for topic_id, axes in sorted(all_axes.items()):
            topic_name = next(t['name'] for t in topics if t['id'] == topic_id)
            f.write(f"  トピック: {topic_name}\n")
            for axis in axes:
                f.write(f"    - [{axis['id']}] {axis['name']} (強度: {axis['strength']}/5)\n")
        f.write("\n")

        # スコア分布
        if len(all_scores) > 0:
            import numpy as np
            score_values = [s['score'] for s in all_scores if s['score'] is not None]
            null_count = sum(1 for s in all_scores if s['score'] is None)
            f.write("スコア分布統計:\n")
            if len(score_values) > 0:
                f.write(f"  平均: {np.mean(score_values):.2f}\n")
                f.write(f"  中央値: {np.median(score_values):.1f}\n")
                f.write(f"  標準偏差: {np.std(score_values):.2f}\n")
                f.write(f"  左寄り(1-3): {sum(1 for s in score_values if s <= 3)} 件\n")
                f.write(f"    - 左極(1): {sum(1 for s in score_values if s == 1)} 件\n")
                f.write(f"    - 左寄り強(2): {sum(1 for s in score_values if s == 2)} 件\n")
                f.write(f"    - 左寄り弱(3): {sum(1 for s in score_values if s == 3)} 件\n")
                f.write(f"  右寄り(4-6): {sum(1 for s in score_values if s >= 4)} 件\n")
                f.write(f"    - 右寄り弱(4): {sum(1 for s in score_values if s == 4)} 件\n")
                f.write(f"    - 右寄り強(5): {sum(1 for s in score_values if s == 5)} 件\n")
                f.write(f"    - 右極(6): {sum(1 for s in score_values if s == 6)} 件\n")
            if null_count > 0:
                f.write(f"  該当なし: {null_count} 件\n")

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"[OK] 全処理完了！")
    print(f"  処理時間: {elapsed:.1f} 秒")
    print(f"  結果保存先: {RESULTS_DIR}/")
    print(f"    - topics.json: トピック一覧")
    print(f"    - axes.json: 対立軸一覧")
    print(f"    - anchors.json: アンカー一覧")
    print(f"    - scores.csv: 全意見のスコア")
    print(f"    - summary.txt: 統計サマリー")
    print(f"{'=' * 60}")

    # HTMLビューの自動生成
    print(f"\n[HTML生成] ビューファイルを生成中...")
    try:
        import generate_two_pane_view
        import generate_list_view

        print(f"  - 2ペインビュー生成中...")
        generate_two_pane_view.generate_html()

        print(f"  - リストビュー生成中...")
        generate_list_view.generate_html()

        # docs/へコピー
        import shutil
        docs_dir = Path('../docs')
        docs_dir.mkdir(exist_ok=True)

        print(f"  - docs/へコピー中...")
        shutil.copy(RESULTS_DIR / 'two_pane_view.html', docs_dir / 'index.html')
        shutil.copy(RESULTS_DIR / 'list_view.html', docs_dir / 'list.html')

        print(f"[OK] HTMLビュー生成完了")
        print(f"  - {RESULTS_DIR}/two_pane_view.html")
        print(f"  - {RESULTS_DIR}/list_view.html")
        print(f"  - ../docs/index.html")
        print(f"  - ../docs/list.html")
    except Exception as e:
        print(f"[WARNING] HTML生成中にエラー: {e}")
        print(f"  手動で generate_two_pane_view.py と generate_list_view.py を実行してください。")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n処理を中断しました。")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
