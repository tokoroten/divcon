# DivCon - Divide and Conciliate

大量の意見から対立軸を自動抽出・可視化する汎用分析ツール

**DivCon** = **Div**ide and **Con**ciliate（分断して和解する）
※ "Divide and Conquer"（分断して統治する）をもじった造語

## 概要

DivConは、LLMを活用した2段階クラスタリング手法により、大量の意見・コメントから主要な対立軸を自動抽出・可視化する汎用ツールです。市民意見、アンケート結果、SNSコメント、パブリックコメントなど、あらゆる意見データの分析に利用できます。

### 主な機能

- **2段階クラスタリング**: トピック抽出 → 対立軸発見
- **6段階スコアリング**: 各意見を対立軸上の位置（1:左極 〜 6:右極）で評価
- **インタラクティブな可視化**:
  - 2ペインビュー: 対立する意見を左右に並べて比較
  - リストビュー: フィルタリング・検索可能な一覧表示

## デモ

GitHub Pagesでホスティングされた分析結果（エネルギー政策パブリックコメント分析の例）を確認できます:

- [2ペインビュー (メイン)](https://tokoroten.github.io/divcon/) - 対立軸ごとに左右の意見を比較
- [リストビュー](https://tokoroten.github.io/divcon/list.html) - フィルタリング・検索機能付き一覧

## サンプル分析結果（エネルギー政策パブリックコメント）

- **総意見数**: 1024件
- **抽出トピック数**: 6個
- **対立軸数**: 20個
- **スコア評価件数**: 3311件

### 主要トピック例

1. 原子力の役割・安全性・バックエンド問題
2. 再生可能エネルギーの拡大と環境・土地利用問題
3. 化石燃料の取扱いと移行技術
4. 系統・需給の柔軟化・蓄電・需要サイド対策
5. コスト・ファイナンス・市場設計と国民負担
6. 政策プロセス・透明性・国際連携・エネルギー安全保障

## 使用方法

### 環境構築

```bash
# 必要なパッケージのインストール
pip install pandas openai python-dotenv tqdm

# 環境変数の設定
cp experiments/.env.example experiments/.env
# .envファイルにOPENAI_API_KEYを設定
```

### 入力データの準備

分析対象のデータをCSV形式で用意します：

```csv
id,comment
1,意見内容1
2,意見内容2
...
```

- `id`: 意見の一意識別子
- `comment`: 分析対象の意見テキスト

データファイルを`experiments/data/opinions.csv`として保存してください。

### 分析の実行

```bash
cd experiments
python divcon_analysis.py
```

分析が完了すると、以下が自動的に生成されます：
- トピック・対立軸のJSON（`results/` フォルダ）
- インタラクティブなHTMLビュー（`results/` および `docs/` フォルダ）
  - 2ペインビュー: 対立する意見を左右に並べて表示
  - リストビュー: フィルタリング・検索可能な一覧

### HTMLビューの個別生成（オプション）

分析結果から個別にHTMLを生成する場合：

```bash
# 2ペインビューの生成
python generate_two_pane_view.py

# リストビューの生成
python generate_list_view.py
```

## ディレクトリ構造

```
divcon/
├── experiments/
│   ├── divcon_analysis.py          # メイン分析スクリプト
│   ├── generate_two_pane_view.py   # 2ペインビュー生成
│   ├── generate_list_view.py       # リストビュー生成
│   ├── data/
│   │   └── opinions.csv            # 入力データ（除外）
│   └── results/
│       ├── topics.json             # 抽出されたトピック
│       ├── axes.json               # 対立軸情報
│       ├── anchors.json            # アンカー意見
│       ├── summary.txt             # 分析サマリー
│       └── scores.csv              # スコアリング結果（除外）
├── docs/
│   ├── index.html                  # GitHub Pages用（2ペインビュー）
│   └── list.html                   # リストビュー
└── README.md

```

## 技術仕様

- **LLMモデル**: GPT-4-mini
- **並列処理**: 最大10並列でバッチ処理
- **評価スケール**: 6段階Likertスケール
  - 1: 左極（最も強い）
  - 2-3: 左寄り（強/弱）
  - 4-5: 右寄り（弱/強）
  - 6: 右極（最も強い）

## ライセンス

MIT License

## 貢献・フィードバック

バグ報告や機能リクエストは、GitHubのIssuesでお願いします。
