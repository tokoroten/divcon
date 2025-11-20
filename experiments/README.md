# DivCon: Division & Consensus - 対立軸発見アルゴリズム

## プロジェクト概要

DivConは、大量の市民意見から**対立している軸**を自動発見し、意見の分布を可視化するツールです。Jigsaw Sensemakerのエンベディングレス・クラスタリングの概念を基に、対立構造の発見に特化した新しいアプローチを実装しています。

**コアコンセプト**:
- エンベディングを経由せず、LLMに直接「意味的なグルーピング」と「対立軸の発見」を行わせる
- 二段階アプローチ: 先にトピック検出 → 次に対立軸発見
- 極端意見をアンカーとして生成し、それを基準にスコアリング

## データ

**入力データ**: `experiments/data/opinions.csv`
- エネルギー基本計画に対する市民意見 1024件
- 形式: `id, comment`

**元データ**: `eng_pubcom.csv`（参考用、変更なし）

## アルゴリズムの全体像

```
入力: 1024件の市民意見

↓ Stage 1: トピック検出
├─ LLMが主要なトピックを自動抽出（3-7個程度）
└─ 出力: Topic[] (id, name, description)

↓ Stage 2: トピック分類
├─ 各意見を最も適切なトピックに割り当て
└─ 出力: 各意見にtopic_idが付与

↓ Stage 3a: 対立軸の発見
├─ 各トピック内で対立している軸を発見（2-4個）
└─ 出力: Axis[] (name, left_pole, right_pole, strength)

↓ Stage 3b: 極端意見アンカーの生成
├─ 既存の意見を参考に、極端な主張を生成
├─ 左極10個 + 右極10個 = 合計20個のアンカー
└─ 出力: left_anchors[], right_anchors[]

↓ Stage 4: 強度推定
├─ アンカーを基準に、各意見を1-5でスコアリング
└─ 出力: 各意見のスコアと理由

↓ 出力: 可視化
└─ ヒストグラム、統計情報、分断度分析
```

---

## 各Stageの詳細

### Stage 1: トピック検出（sensemakerの方式）

**目的**: 意見群から主要な議論の主題を自動抽出

**手法**:
- 全意見をLLMに提示
- 「最適なトピック数は何か」を質問
- LLMが自動判断（3-7個を推奨）

**Pydanticモデル**:
```python
class Topic(BaseModel):
    id: str
    name: str
    description: str

class TopicDiscoveryResponse(BaseModel):
    topics: List[Topic]
    reasoning: str
```

**重要な設計判断**:
- トピック数を事前に固定せず、LLMに判断させる
- Structured Outputsで確実にパース可能なJSONを取得

---

### Stage 2: トピック分類

**目的**: 各意見を適切なトピックに割り当て

**手法**:
- バッチ処理（10件ずつ）で効率化
- トピック定義を明示してLLMに分類させる

**Pydanticモデル**:
```python
class Classification(BaseModel):
    opinion_id: str
    topic_id: str

class ClassificationResponse(BaseModel):
    classifications: List[Classification]
```

**エラーハンドリング**:
- 不明なtopic_idは警告表示
- 未分類の件数を可視化
- StopIterationエラーを防ぐ

---

### Stage 3a: 対立軸の発見

**目的**: トピック内で人々が対立している軸を発見

**手法**:
- トピック内の全意見をLLMに提示
- 「意見が二極化している次元」を抽出
- 対立の強度を5段階評価（1-5）

**Pydanticモデル**:
```python
class Axis(BaseModel):
    id: str
    name: str
    left_pole: str
    right_pole: str
    strength: int  # 1-5の5段階評価
    reasoning: str

class AxisDiscoveryResponse(BaseModel):
    axes: List[Axis]
```

**重要な設計判断**:
- **強度を5段階評価にした理由**: LLMはfloat（0-1）よりも整数（1-5）の方が扱いやすく、一貫性が向上
- 強度の定義:
  - 5: 非常に強い対立（意見が完全に二極化）
  - 4: 強い対立
  - 3: 中程度の対立
  - 2: やや対立
  - 1: 弱い対立

---

### Stage 3b: 極端意見アンカーの生成（最重要）

**目的**: 各対立軸について、極端な意見をアンカーとして生成

**コアアイデア**:
- 実際の意見に十分な極端さがない場合でも、理想的な基準点を作る
- 既存の意見を参考にしつつ、より極端な表現を生成
- **左極10個 + 右極10個 = 合計20個**のアンカー

**Pydanticモデル**:
```python
class AnchorGenerationResponse(BaseModel):
    left_anchors: List[str]
    right_anchors: List[str]
```

**プロンプト設計の工夫**:
1. **Few-shot Examples**: 具体的な極端な文章例を提示
   - 例: 「経済成長を完全に停止してでも、環境保護を最優先すべきである」
2. **強い表現の使用を指示**: 「完全に」「全て」「絶対に」「即座に」
3. **妥協を含まない断定的な主張**: バランス型の意見を避ける
4. **多様性の確保**: 同じ極でも異なる角度から表現
5. **reasoning_effort="high"**: アンカー生成は高精度が必要

**重要な設計判断**:
- **なぜ20個も生成するのか**:
  - 極端さにも多様性がある
  - 10個の異なる視点があることで、より精密なスコアリングが可能
  - 単一の基準点より、複数の基準点の方が一貫性が高い

---

### Stage 4: 強度推定

**目的**: 生成されたアンカーを基準に、実際の意見を1-5でスコアリング

**手法**:
- 左極20個のアンカーと右極20個のアンカーを提示
- 各意見がどの位置にあるかをLLMに判断させる

**スコアの定義**:
- **1**: 左極アンカーに非常に近い
- **2**: 左極寄り
- **3**: バランス型・ブリッジ（両極の架け橋）
- **4**: 右極寄り
- **5**: 右極アンカーに非常に近い

**Pydanticモデル**:
```python
class Score(BaseModel):
    opinion_id: str
    score: int
    reasoning: str

class ScoringResponse(BaseModel):
    scores: List[Score]
```

**スコア3の意味**:
- 単なる「中立」ではなく、「バランス型・ブリッジ」
- 両極の架け橋となる重要な意見
- 対話や合意形成のキーパーソン候補

---

## 技術スタック

### LLMモデル
- **モデル**: GPT-5 mini（知識カットオフ以降の新モデル）
- **Reasoning機能**: `reasoning_effort` パラメータを使用
  - Stage 1, 2, 3a, 4: `medium`
  - Stage 3b（アンカー生成）: `high`

### Structured Outputs
全てのAPI呼び出しでPydanticモデルを使用:
```python
completion = client.beta.chat.completions.parse(
    model=MODEL,
    messages=[...],
    reasoning_effort=REASONING_EFFORT,
    response_format=PydanticModel
)
```

**利点**:
- JSONフォーマットが崩れない
- 型安全性が保証される
- パースエラーが発生しない

### 環境設定
`.env`ファイル:
```
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-5-mini
REASONING_EFFORT=medium
```

---

## 設計思想とSensemakerからの発展

### Sensemakerから引き継いだ概念
1. **エンベディングレス・クラスタリング**
   - ベクトル空間での距離計算を使わない
   - LLMに直接「意味的なグルーピング」を行わせる
2. **トピック検出の手法**
   - LLMに最適なトピック数を判断させる
   - 構造化出力で確実性を担保

### DivConの独自性
1. **二段階アプローチ**
   - トピックと対立軸を分離
   - トピック内での対立構造に焦点
2. **極端意見アンカーの生成**
   - 実際の意見を選ぶのではなく、理想的な極端例を生成
   - 20個の多様なアンカーで精度向上
3. **対立の定量化**
   - 5段階評価で対立の強度を測定
   - バランス型意見（スコア3）の重要性を認識

---

## 複数軸へのマッピング

**重要**: 1つの意見は複数の対立軸にマッピング可能

```
意見X: "再生可能エネルギーへの移行は必要だが、
       段階的に進め、雇用への配慮も必要"

マッピング結果:
  軸1（環境 vs 経済）= 3（バランス型）
  軸2（急進 vs 漸進）= 4（漸進寄り）
  軸3（政府主導 vs 市場主導）= (言及なし)
```

---

## コードの見通しを良くする工夫

### Pydanticモデルの配置
- 各Stageのセル内にモデル定義を配置
- 最初のセルにまとめず、API呼び出しの直前に定義
- 各セルが自己完結的で理解しやすい

### プロンプト設計
1. **明確な指示**: タスクを明確に定義
2. **Few-shot Examples**: 具体例を提示
3. **制約の明示**: 「指定されたIDのみを使用」など
4. **出力形式の指定**: JSON構造を明示

---

## 実行方法

### 1. 環境準備
```bash
cd experiments
pip install openai python-dotenv pandas matplotlib seaborn pydantic
```

### 2. API設定
`.env`ファイルを作成（`.env.example`を参考）:
```
OPENAI_API_KEY=your-actual-api-key
OPENAI_MODEL=gpt-5-mini
REASONING_EFFORT=medium
```

### 3. Jupyter Notebook実行
```bash
jupyter notebook divcon-experiment.ipynb
```

### 4. セルを順番に実行
- セル1: 環境セットアップ
- セル2: データ読み込み
- セル3-7: 各Stageの実行
- セル8: 結果の可視化

---

## パフォーマンス最適化

### サンプリング
```python
SAMPLE_SIZE = 100  # まず100件でテスト
```
- 全件（1024件）は高コスト
- 最初は小規模でアルゴリズムを検証

### バッチ処理
```python
BATCH_SIZE = 10  # Stage 2で10件ずつ分類
```
- API呼び出し回数を削減
- コスト効率の向上

---

## 今後の拡張可能性

### 1. 全トピックへの拡張
現在は最初のトピックのみ実験。ループで全トピックに適用可能。

### 2. 時系列分析
意見の収集時期を考慮し、対立の変化を追跡。

### 3. 可視化の強化
- 2D散布図（複数軸を同時表示）
- ネットワークグラフ（意見間の関係）
- インタラクティブダッシュボード

### 4. 自動レポート生成
分析結果を自動でマークダウン/HTMLレポートに出力。

---

## トラブルシューティング

### Stage 2でStopIterationエラー
- **原因**: LLMが存在しないtopic_idを返した
- **対策**: エラーハンドリングを追加済み（不明なトピックは警告表示）

### JSONパースエラー
- **原因**: LLMが無効なJSON構造を返した
- **対策**: Structured Outputsを使用（現在は発生しない）

### API料金が高い
- **対策**: `SAMPLE_SIZE`を小さくする（10-50件）
- **対策**: 高コストなStageのみ実行

---

## 参考: Jigsaw Sensemaker

本プロジェクトは`sensemaking-tools/`ディレクトリ内のJigsaw Sensemakerを参考にしています。

**Sensemakerの特徴**:
- Google Vertex AI / Gemini モデル使用
- トピック検出 + カテゴリ分類 + サマリゼーション
- 投票データとの統合（Community Notes風）

**DivConとの違い**:
- OpenAI GPT-5 miniを使用
- 対立軸の発見に特化
- 極端意見アンカーの生成

---

## まとめ

DivConは、市民意見から対立構造を自動発見する革新的なアルゴリズムです。以下の特徴があります：

1. **エンベディングレス**: ベクトル計算不要、LLMの意味理解を直接活用
2. **二段階アプローチ**: トピック → 対立軸の順で構造化
3. **極端意見アンカー**: 20個の多様な基準点で精密なスコアリング
4. **Structured Outputs**: JSONフォーマットを厳密に保証
5. **GPT-5 mini + Reasoning**: 最新モデルの推論能力を活用

このアルゴリズムは、政治、都市計画、政策決定など、様々な分野での合意形成支援に応用可能です。
