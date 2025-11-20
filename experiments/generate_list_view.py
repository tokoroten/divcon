#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DivCon リストビュー HTML 生成スクリプト
意見をフィルタリング・検索可能なリストビューとして表示
"""

import pandas as pd
import json

def generate_html():
    # データ読み込み
    scores_df = pd.read_csv('results/scores.csv')

    # トピック情報を読み込み
    with open('results/topics.json', 'r', encoding='utf-8') as f:
        topics_data = json.load(f)
    topic_map = {t['id']: t['name'] for t in topics_data}

    # 軸情報を読み込み
    with open('results/axes.json', 'r', encoding='utf-8') as f:
        axes_data = json.load(f)
    # axes_dataは {topic_id: [axes...]} の形式なので、平坦化する
    axis_map = {}
    for topic_axes in axes_data.values():
        for axis in topic_axes:
            axis_map[axis['id']] = axis['name']

    # nullスコアを文字列に変換
    scores_df['score'] = scores_df['score'].fillna('該当なし')
    scores_df['excerpt'] = scores_df['excerpt'].fillna('')

    # トピック名と軸名を追加
    scores_df['topic_name'] = scores_df['topic_id'].map(topic_map)
    scores_df['axis_display_name'] = scores_df['axis_id'].map(axis_map)

    # トピックと軸の一覧を取得
    topics = sorted(scores_df['topic_id'].unique())
    axes = sorted(scores_df['axis_id'].unique())

    # データをJSON形式に変換（JavaScriptで使用）
    data_json = scores_df.to_json(orient='records', force_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DivCon 意見リストビュー</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', 'Yu Gothic', 'Meiryo', sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 28px;
        }}

        .subtitle {{
            color: #7f8c8d;
            font-size: 14px;
        }}

        .filters {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }}

        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}

        .filter-group label {{
            font-size: 12px;
            color: #7f8c8d;
            font-weight: 600;
        }}

        select, input[type="text"] {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            min-width: 200px;
        }}

        input[type="text"] {{
            min-width: 300px;
        }}

        .stats {{
            background: white;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .stats-text {{
            color: #7f8c8d;
            font-size: 14px;
        }}

        .stats-number {{
            color: #2c3e50;
            font-weight: 600;
            font-size: 18px;
        }}

        .opinion-card {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #3498db;
            transition: box-shadow 0.2s;
        }}

        .opinion-card:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}

        .opinion-card.score-1 {{ border-left-color: #c0392b; }}
        .opinion-card.score-2 {{ border-left-color: #e74c3c; }}
        .opinion-card.score-3 {{ border-left-color: #e67e22; }}
        .opinion-card.score-4 {{ border-left-color: #3498db; }}
        .opinion-card.score-5 {{ border-left-color: #8e44ad; }}
        .opinion-card.score-6 {{ border-left-color: #6c3483; }}
        .opinion-card.score-null {{ border-left-color: #95a5a6; }}

        .opinion-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .opinion-id {{
            font-size: 12px;
            color: #95a5a6;
            font-weight: 600;
        }}

        .badges {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            color: white;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 300px;
        }}

        .badge-topic {{
            background: #3498db;
        }}

        .badge-score {{
            background: #2ecc71;
        }}

        .badge-score.score-1 {{ background: #c0392b; }}
        .badge-score.score-2 {{ background: #e74c3c; }}
        .badge-score.score-3 {{ background: #e67e22; }}
        .badge-score.score-4 {{ background: #3498db; }}
        .badge-score.score-5 {{ background: #8e44ad; }}
        .badge-score.score-6 {{ background: #6c3483; }}
        .badge-score.score-null {{ background: #95a5a6; }}

        .axis-name {{
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 10px;
            font-weight: 500;
        }}

        .excerpt {{
            background: #f8f9fa;
            padding: 12px 15px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 14px;
            color: #2c3e50;
            border-left: 3px solid #3498db;
            font-weight: 500;
        }}

        .comment {{
            font-size: 13px;
            color: #555;
            line-height: 1.8;
            margin-bottom: 10px;
        }}

        .reasoning {{
            font-size: 12px;
            color: #7f8c8d;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            margin-top: 10px;
        }}

        .reasoning-label {{
            font-weight: 600;
            color: #95a5a6;
            margin-bottom: 5px;
        }}

        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #95a5a6;
            font-size: 16px;
        }}

        .legend {{
            background: white;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .legend-title {{
            font-size: 12px;
            color: #7f8c8d;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .legend-items {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #555;
        }}

        .legend-color {{
            width: 20px;
            height: 12px;
            border-radius: 2px;
        }}

        button {{
            padding: 8px 16px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
        }}

        button:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DivCon 意見リストビュー</h1>
            <div class="subtitle">エネルギー政策に関する市民意見の対立軸分析</div>
        </header>

        <div class="legend">
            <div class="legend-title">スコア凡例（6段階評価）</div>
            <div class="legend-items">
                <div class="legend-item">
                    <div class="legend-color" style="background: #c0392b;"></div>
                    <span>1: 左極（最も強い）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #e74c3c;"></div>
                    <span>2: 左寄り（強）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #e67e22;"></div>
                    <span>3: 左寄り（弱）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #3498db;"></div>
                    <span>4: 右寄り（弱）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #8e44ad;"></div>
                    <span>5: 右寄り（強）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #6c3483;"></div>
                    <span>6: 右極（最も強い）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #95a5a6;"></div>
                    <span>該当なし</span>
                </div>
            </div>
        </div>

        <div class="filters">
            <div class="filter-group">
                <label>トピック</label>
                <select id="topicFilter">
                    <option value="">すべて</option>
                    {' '.join(f'<option value="{t}">[{t}] {topic_map[t]}</option>' for t in topics)}
                </select>
            </div>

            <div class="filter-group">
                <label>対立軸</label>
                <select id="axisFilter">
                    <option value="">すべて</option>
                    {' '.join(f'<option value="{a}">[{a}] {axis_map[a]}</option>' for a in axes)}
                </select>
            </div>

            <div class="filter-group">
                <label>スコア</label>
                <select id="scoreFilter">
                    <option value="">すべて</option>
                    <option value="1">1: 左極（最も強い）</option>
                    <option value="2">2: 左寄り（強）</option>
                    <option value="3">3: 左寄り（弱）</option>
                    <option value="4">4: 右寄り（弱）</option>
                    <option value="5">5: 右寄り（強）</option>
                    <option value="6">6: 右極（最も強い）</option>
                    <option value="該当なし">該当なし</option>
                </select>
            </div>

            <div class="filter-group">
                <label>キーワード検索</label>
                <input type="text" id="searchBox" placeholder="本文・excerpt・reasoning を検索...">
            </div>

            <button onclick="resetFilters()">リセット</button>
        </div>

        <div class="stats">
            <span class="stats-text">表示中: <span class="stats-number" id="visibleCount">0</span> / <span id="totalCount">0</span> 件</span>
        </div>

        <div id="opinionsList"></div>

        <div id="noResults" class="no-results" style="display: none;">
            該当する意見が見つかりませんでした
        </div>
    </div>

    <script>
        const allData = {data_json};
        let filteredData = allData;

        function renderOpinions(data) {{
            const container = document.getElementById('opinionsList');
            const noResults = document.getElementById('noResults');

            if (data.length === 0) {{
                container.innerHTML = '';
                noResults.style.display = 'block';
            }} else {{
                noResults.style.display = 'none';
                container.innerHTML = data.map(opinion => {{
                    const scoreClass = opinion.score === '該当なし' ? 'score-null' : `score-${{opinion.score}}`;
                    const scoreDisplay = opinion.score === '該当なし' ? '該当なし' : `スコア: ${{opinion.score}}`;

                    return `
                        <div class="opinion-card ${{scoreClass}}">
                            <div class="opinion-header">
                                <span class="opinion-id">ID: ${{opinion.opinion_id}}</span>
                                <div class="badges">
                                    <span class="badge badge-topic">${{opinion.topic_name}}</span>
                                    <span class="badge badge-score ${{scoreClass}}">${{scoreDisplay}}</span>
                                </div>
                            </div>

                            <div class="axis-name">${{opinion.axis_display_name}}</div>

                            ${{opinion.excerpt ? `<div class="excerpt">${{opinion.excerpt}}</div>` : ''}}

                            <div class="comment">${{opinion.comment}}</div>

                            <div class="reasoning">
                                <div class="reasoning-label">💭 判断理由</div>
                                ${{opinion.reasoning}}
                            </div>
                        </div>
                    `;
                }}).join('');
            }}

            document.getElementById('visibleCount').textContent = data.length;
            document.getElementById('totalCount').textContent = allData.length;
        }}

        function applyFilters() {{
            const topicFilter = document.getElementById('topicFilter').value;
            const axisFilter = document.getElementById('axisFilter').value;
            const scoreFilter = document.getElementById('scoreFilter').value;
            const searchText = document.getElementById('searchBox').value.toLowerCase();

            filteredData = allData.filter(opinion => {{
                if (topicFilter && opinion.topic_id !== topicFilter) return false;
                if (axisFilter && opinion.axis_id !== axisFilter) return false;
                if (scoreFilter && String(opinion.score) !== scoreFilter) return false;

                if (searchText) {{
                    const searchableText = (
                        opinion.comment + ' ' +
                        opinion.excerpt + ' ' +
                        opinion.reasoning
                    ).toLowerCase();
                    if (!searchableText.includes(searchText)) return false;
                }}

                return true;
            }});

            renderOpinions(filteredData);
        }}

        function resetFilters() {{
            document.getElementById('topicFilter').value = '';
            document.getElementById('axisFilter').value = '';
            document.getElementById('scoreFilter').value = '';
            document.getElementById('searchBox').value = '';
            applyFilters();
        }}

        // イベントリスナー
        document.getElementById('topicFilter').addEventListener('change', applyFilters);
        document.getElementById('axisFilter').addEventListener('change', applyFilters);
        document.getElementById('scoreFilter').addEventListener('change', applyFilters);
        document.getElementById('searchBox').addEventListener('input', applyFilters);

        // 初期表示
        renderOpinions(allData);
    </script>
</body>
</html>"""

    # HTMLファイルを保存
    with open('results/list_view.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("[OK] HTML生成完了: results/list_view.html")
    print(f"   総意見数: {len(scores_df)} 件")
    print(f"   トピック数: {len(topics)} 個")
    print(f"   対立軸数: {len(axes)} 個")

if __name__ == '__main__':
    generate_html()
