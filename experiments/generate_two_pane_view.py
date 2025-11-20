#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DivCon 2ペイン対立ビュー HTML 生成スクリプト
左ペイン（スコア1,2,3）と右ペイン（スコア6,5,4）に分けて表示
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
    axis_map = {}
    axis_to_topic = {}  # 軸IDからトピックIDへのマッピング
    axis_full_info = {}  # 軸の完全情報（名前と両極情報）
    for topic_id, topic_axes in axes_data.items():
        for axis in topic_axes:
            axis_map[axis['id']] = axis['name']
            axis_to_topic[axis['id']] = topic_id
            axis_full_info[axis['id']] = {
                'name': axis['name'],
                'left_pole': axis['left_pole'],
                'right_pole': axis['right_pole']
            }

    # 合意可能性分析を読み込み
    try:
        with open('results/consensus.json', 'r', encoding='utf-8') as f:
            consensus_data = json.load(f)
        # 軸IDでインデックス化
        consensus_map = {item['axis_id']: item for item in consensus_data}
    except FileNotFoundError:
        consensus_map = {}

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
    axis_to_topic_json = json.dumps(axis_to_topic, ensure_ascii=False)
    axis_map_json = json.dumps(axis_map, ensure_ascii=False)
    axis_full_info_json = json.dumps(axis_full_info, ensure_ascii=False)
    consensus_map_json = json.dumps(consensus_map, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DivCon 対立ビュー（2ペイン）</title>
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
            overflow-x: hidden;
        }}

        .container {{
            max-width: 1800px;
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

        .toggle-container {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .toggle-label {{
            font-size: 14px;
            color: #555;
            font-weight: 600;
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

        select {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            min-width: 200px;
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

        .two-pane-container {{
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }}

        .pane {{
            width: 50%;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .pane-header {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            font-weight: 600;
            font-size: 16px;
            position: sticky;
            top: 20px;
            z-index: 10;
        }}

        .pane-header.left {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
        }}

        .pane-header.right {{
            background: linear-gradient(135deg, #6c3483 0%, #8e44ad 100%);
            color: white;
        }}

        .pane-header-title {{
            font-size: 18px;
            margin-bottom: 8px;
        }}

        .pane-header-axis {{
            font-size: 13px;
            opacity: 0.9;
            line-height: 1.6;
            margin-top: 5px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }}

        .pane-header-pole {{
            font-weight: 400;
            margin-top: 5px;
        }}

        .opinion-card {{
            background: white;
            padding: 6px 10px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border-left: 3px solid #3498db;
            transition: box-shadow 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
            cursor: pointer;
        }}

        .opinion-card:hover {{
            box-shadow: 0 2px 6px rgba(0,0,0,0.12);
        }}

        .opinion-card.score-1 {{ border-left-color: #c0392b; }}
        .opinion-card.score-2 {{ border-left-color: #e74c3c; }}
        .opinion-card.score-3 {{ border-left-color: #e67e22; }}
        .opinion-card.score-4 {{ border-left-color: #3498db; }}
        .opinion-card.score-5 {{ border-left-color: #8e44ad; }}
        .opinion-card.score-6 {{ border-left-color: #6c3483; }}

        .opinion-header {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }}

        .opinion-id {{
            font-size: 10px;
            color: #95a5a6;
            font-weight: 600;
            white-space: nowrap;
        }}

        .badge {{
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 600;
            color: white;
            white-space: nowrap;
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

        .axis-name {{
            font-size: 13px;
            color: #7f8c8d;
            margin-bottom: 10px;
            font-weight: 500;
        }}

        .excerpt {{
            font-size: 12px;
            color: #2c3e50;
            line-height: 1.4;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .tooltip {{
            position: absolute;
            bottom: 100%;
            left: 0;
            margin-bottom: 8px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.6;
            max-width: 400px;
            min-width: 300px;
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            white-space: normal;
            word-wrap: break-word;
        }}

        .opinion-card:hover .tooltip {{
            opacity: 1;
        }}

        .comment {{
            font-size: 12px;
            color: #555;
            line-height: 1.8;
            display: none;  /* デフォルトで非表示 */
        }}

        .reasoning {{
            font-size: 11px;
            color: #7f8c8d;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            margin-top: 8px;
            display: none;  /* デフォルトで非表示 */
        }}

        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #95a5a6;
            font-size: 16px;
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

        @media (max-width: 1200px) {{
            .two-pane-container {{
                flex-direction: column;
            }}
        }}

        /* 合意可能性分析セクション */
        .consensus-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .consensus-section h3 {{
            margin: 0 0 20px 0;
            color: #2c3e50;
            font-size: 1.3em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}

        .consensus-tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}

        .consensus-tab {{
            padding: 10px 20px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
        }}

        .consensus-tab:hover {{
            background: #ecf0f1;
        }}

        .consensus-tab.active {{
            background: #3498db;
            color: white;
            border-color: #3498db;
        }}

        .consensus-tab.consensus-active {{
            background: #27ae60;
            color: white;
            border-color: #27ae60;
        }}

        .consensus-tab.conflict-active {{
            background: #e74c3c;
            color: white;
            border-color: #e74c3c;
        }}

        .consensus-content {{
            display: none;
        }}

        .consensus-content.active {{
            display: block;
        }}

        .consensus-points, .conflict-points {{
            display: grid;
            gap: 15px;
        }}

        .consensus-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #27ae60;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .conflict-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #e74c3c;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .consensus-item h4, .conflict-item h4 {{
            margin: 0 0 8px 0;
            color: #2c3e50;
            font-size: 1.1em;
        }}

        .consensus-item p, .conflict-item p {{
            margin: 0 0 10px 0;
            color: #555;
            line-height: 1.6;
        }}

        .supporting-opinions {{
            margin-top: 10px;
            padding: 10px;
            background: #f1f8f4;
            border-radius: 4px;
            font-size: 0.9em;
            color: #666;
        }}

        .opposing-opinions {{
            margin-top: 10px;
            padding: 10px;
            background: #fef5f5;
            border-radius: 4px;
            font-size: 0.9em;
        }}

        .left-opinions {{
            color: #c0392b;
            margin-bottom: 5px;
        }}

        .right-opinions {{
            color: #2980b9;
        }}

        .no-consensus-data {{
            padding: 20px;
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
        }}

        /* ジャンプリンク */
        .jump-link {{
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 8px;
            display: none;
        }}

        .jump-link a {{
            display: inline-block;
            padding: 12px 24px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .jump-link a:hover {{
            background: #2980b9;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }}

        .jump-link-icon {{
            margin-left: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DivCon 対立ビュー（2ペイン）</h1>
            <div class="subtitle">左ペイン（左寄り 1,2,3）vs 右ペイン（右寄り 6,5,4）</div>
        </header>

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

            <div class="toggle-container">
                <span class="toggle-label">中間意見を中央に</span>
                <input type="checkbox" id="reverseToggle" onchange="toggleReverse()">
            </div>

            <button onclick="resetFilters()">リセット</button>
        </div>

        <div class="stats">
            <span class="stats-text">
                左寄り（1-3）: <span class="stats-number" id="leftCount">0</span> 件 |
                右寄り（4-6）: <span class="stats-number" id="rightCount">0</span> 件
            </span>
        </div>

        <!-- ジャンプリンク -->
        <div id="jumpLink" class="jump-link">
            <a href="#consensusSection">
                ▼ 合意可能性分析を見る <span class="jump-link-icon">▼</span>
            </a>
        </div>

        <div class="two-pane-container">
            <div class="pane">
                <div class="pane-header left" id="leftHeader">
                    <div class="pane-header-title">← 左寄り（1, 2, 3）</div>
                    <div class="pane-header-axis" id="leftAxisInfo"></div>
                </div>
                <div id="leftPane"></div>
            </div>

            <div class="pane">
                <div class="pane-header right" id="rightHeader">
                    <div class="pane-header-title">右寄り（6, 5, 4） →</div>
                    <div class="pane-header-axis" id="rightAxisInfo"></div>
                </div>
                <div id="rightPane"></div>
            </div>
        </div>

        <!-- 合意可能性分析セクション -->
        <div id="consensusSection" class="consensus-section" style="display: none;">
            <h3>合意可能性分析</h3>

            <div class="consensus-tabs">
                <div class="consensus-tab" id="consensusTab" onclick="switchConsensusTab('consensus')">
                    合意可能なポイント (<span id="consensusCount">0</span>)
                </div>
                <div class="consensus-tab" id="conflictTab" onclick="switchConsensusTab('conflict')">
                    合意不可能なポイント (<span id="conflictCount">0</span>)
                </div>
            </div>

            <div id="consensusContent" class="consensus-content active">
                <div id="consensusPoints" class="consensus-points"></div>
            </div>

            <div id="conflictContent" class="consensus-content">
                <div id="conflictPoints" class="conflict-points"></div>
            </div>
        </div>

        <div id="noResults" class="no-results" style="display: none;">
            該当する意見が見つかりませんでした
        </div>
    </div>

    <script>
        const allData = {data_json};
        const axisToTopic = {axis_to_topic_json};
        const axisMap = {axis_map_json};
        const axisFullInfo = {axis_full_info_json};
        const consensusMap = {consensus_map_json};
        let filteredData = allData;
        let isReversed = false;

        function updateAxisHeaders() {{
            const axisFilter = document.getElementById('axisFilter').value;
            const leftAxisInfo = document.getElementById('leftAxisInfo');
            const rightAxisInfo = document.getElementById('rightAxisInfo');

            if (axisFilter && axisFullInfo[axisFilter]) {{
                const axisInfo = axisFullInfo[axisFilter];
                leftAxisInfo.innerHTML = `
                    <div style="margin-bottom: 5px;"><strong>${{axisInfo.name}}</strong></div>
                    <div class="pane-header-pole">${{axisInfo.left_pole}}</div>
                `;
                rightAxisInfo.innerHTML = `
                    <div style="margin-bottom: 5px;"><strong>${{axisInfo.name}}</strong></div>
                    <div class="pane-header-pole">${{axisInfo.right_pole}}</div>
                `;
                leftAxisInfo.style.display = 'block';
                rightAxisInfo.style.display = 'block';
            }} else {{
                leftAxisInfo.style.display = 'none';
                rightAxisInfo.style.display = 'none';
            }}
        }}

        function renderOpinions(data) {{
            const leftPane = document.getElementById('leftPane');
            const rightPane = document.getElementById('rightPane');
            const noResults = document.getElementById('noResults');

            // スコアが数値のデータのみフィルター
            const validData = data.filter(op => typeof op.score === 'number' && op.score >= 1 && op.score <= 6);

            // 左寄り（1-3）と右寄り（4-6）に分類
            let leftData = validData.filter(op => op.score <= 3);
            let rightData = validData.filter(op => op.score >= 4);

            // ソート順を制御
            if (isReversed) {{
                // 中間意見を中央に: 左は3,2,1 / 右は4,5,6
                leftData = leftData.sort((a, b) => b.score - a.score);
                rightData = rightData.sort((a, b) => a.score - b.score);
            }} else {{
                // デフォルト: 左は1,2,3 / 右は6,5,4
                leftData = leftData.sort((a, b) => a.score - b.score);
                rightData = rightData.sort((a, b) => b.score - a.score);
            }}

            if (leftData.length === 0 && rightData.length === 0) {{
                leftPane.innerHTML = '';
                rightPane.innerHTML = '';
                noResults.style.display = 'block';
            }} else {{
                noResults.style.display = 'none';

                // 左ペイン
                leftPane.innerHTML = leftData.map(opinion => {{
                    const scoreClass = `score-${{opinion.score}}`;
                    const scoreLabel = [
                        '', '1:左極', '2:左寄り強', '3:左寄り弱'
                    ][opinion.score];

                    return `
                        <div class="opinion-card ${{scoreClass}}">
                            <div class="opinion-header">
                                <span class="opinion-id">ID: ${{opinion.opinion_id}}</span>
                                <span class="badge badge-score ${{scoreClass}}">${{scoreLabel}}</span>
                            </div>
                            ${{opinion.excerpt ? `<div class="excerpt">${{opinion.excerpt}}</div>` : ''}}
                            <div class="tooltip">${{opinion.comment}}</div>
                        </div>
                    `;
                }}).join('');

                // 右ペイン
                rightPane.innerHTML = rightData.map(opinion => {{
                    const scoreClass = `score-${{opinion.score}}`;
                    const scoreLabel = [
                        '', '', '', '', '4:右寄り弱', '5:右寄り強', '6:右極'
                    ][opinion.score];

                    return `
                        <div class="opinion-card ${{scoreClass}}">
                            <div class="opinion-header">
                                <span class="opinion-id">ID: ${{opinion.opinion_id}}</span>
                                <span class="badge badge-score ${{scoreClass}}">${{scoreLabel}}</span>
                            </div>
                            ${{opinion.excerpt ? `<div class="excerpt">${{opinion.excerpt}}</div>` : ''}}
                            <div class="tooltip">${{opinion.comment}}</div>
                        </div>
                    `;
                }}).join('');
            }}

            document.getElementById('leftCount').textContent = leftData.length;
            document.getElementById('rightCount').textContent = rightData.length;
        }}

        function applyFilters() {{
            const topicFilter = document.getElementById('topicFilter').value;
            const axisFilter = document.getElementById('axisFilter').value;

            filteredData = allData.filter(opinion => {{
                if (topicFilter && opinion.topic_id !== topicFilter) return false;
                if (axisFilter && opinion.axis_id !== axisFilter) return false;
                return true;
            }});

            updateAxisHeaders();
            renderOpinions(filteredData);
            renderConsensus();
        }}

        function updateAxisDropdown() {{
            const topicFilter = document.getElementById('topicFilter').value;
            const axisFilter = document.getElementById('axisFilter');
            const currentValue = axisFilter.value;

            // ドロップダウンをクリア
            axisFilter.innerHTML = '<option value="">すべて</option>';

            // トピックが選択されている場合は、そのトピックの軸のみを表示
            const filteredAxes = Object.keys(axisMap).filter(axisId => {{
                if (!topicFilter) return true; // トピック未選択なら全軸表示
                return axisToTopic[axisId] === topicFilter;
            }}).sort();

            // オプションを追加
            filteredAxes.forEach(axisId => {{
                const option = document.createElement('option');
                option.value = axisId;
                option.textContent = `[${{axisId}}] ${{axisMap[axisId]}}`;
                axisFilter.appendChild(option);
            }});

            // 前の選択値が新しいリストにあれば復元
            if (filteredAxes.includes(currentValue)) {{
                axisFilter.value = currentValue;
            }}
        }}

        function toggleReverse() {{
            isReversed = document.getElementById('reverseToggle').checked;
            renderOpinions(filteredData);
        }}

        function resetFilters() {{
            document.getElementById('topicFilter').value = '';
            document.getElementById('axisFilter').value = '';
            document.getElementById('reverseToggle').checked = false;
            isReversed = false;
            updateAxisDropdown();
            applyFilters();
        }}

        // 合意可能性分析の表示切り替え
        function switchConsensusTab(tab) {{
            const consensusTab = document.getElementById('consensusTab');
            const conflictTab = document.getElementById('conflictTab');
            const consensusContent = document.getElementById('consensusContent');
            const conflictContent = document.getElementById('conflictContent');

            if (tab === 'consensus') {{
                consensusTab.classList.add('active', 'consensus-active');
                conflictTab.classList.remove('active', 'conflict-active');
                consensusContent.classList.add('active');
                conflictContent.classList.remove('active');
            }} else {{
                conflictTab.classList.add('active', 'conflict-active');
                consensusTab.classList.remove('active', 'consensus-active');
                conflictContent.classList.add('active');
                consensusContent.classList.remove('active');
            }}
        }}

        // 合意可能性分析のレンダリング
        function renderConsensus() {{
            const axisFilter = document.getElementById('axisFilter').value;
            const consensusSection = document.getElementById('consensusSection');
            const consensusPoints = document.getElementById('consensusPoints');
            const conflictPoints = document.getElementById('conflictPoints');
            const consensusCount = document.getElementById('consensusCount');
            const conflictCount = document.getElementById('conflictCount');
            const jumpLink = document.getElementById('jumpLink');

            // 軸が選択されていない場合は非表示
            if (!axisFilter || !consensusMap[axisFilter]) {{
                consensusSection.style.display = 'none';
                jumpLink.style.display = 'none';
                return;
            }}

            const consensus = consensusMap[axisFilter];
            consensusSection.style.display = 'block';
            jumpLink.style.display = 'block';

            // 合意可能なポイントを表示
            const consensusItems = consensus.consensus_points || [];
            consensusCount.textContent = consensusItems.length;

            if (consensusItems.length === 0) {{
                consensusPoints.innerHTML = '<div class="no-consensus-data">合意可能なポイントが見つかりませんでした</div>';
            }} else {{
                consensusPoints.innerHTML = consensusItems.map(item => `
                    <div class="consensus-item">
                        <h4>${{item.point}}</h4>
                        <p>${{item.explanation}}</p>
                        <div class="supporting-opinions">
                            <strong>サポートする意見:</strong> ${{item.supporting_opinions.join(', ')}}
                        </div>
                    </div>
                `).join('');
            }}

            // 合意不可能なポイントを表示
            const conflictItems = consensus.conflict_points || [];
            conflictCount.textContent = conflictItems.length;

            if (conflictItems.length === 0) {{
                conflictPoints.innerHTML = '<div class="no-consensus-data">合意不可能なポイントが見つかりませんでした</div>';
            }} else {{
                conflictPoints.innerHTML = conflictItems.map(item => `
                    <div class="conflict-item">
                        <h4>${{item.point}}</h4>
                        <p>${{item.explanation}}</p>
                        <div class="opposing-opinions">
                            <div class="left-opinions">
                                <strong>左側の意見:</strong> ${{item.left_opinions.join(', ')}}
                            </div>
                            <div class="right-opinions">
                                <strong>右側の意見:</strong> ${{item.right_opinions.join(', ')}}
                            </div>
                        </div>
                    </div>
                `).join('');
            }}

            // デフォルトで合意可能タブを表示
            switchConsensusTab('consensus');
        }}

        // イベントリスナー
        document.getElementById('topicFilter').addEventListener('change', () => {{
            updateAxisDropdown();
            applyFilters();
        }});
        document.getElementById('axisFilter').addEventListener('change', applyFilters);

        // 初期表示
        updateAxisDropdown();
        updateAxisHeaders();
        renderOpinions(allData);
        renderConsensus();
    </script>
</body>
</html>"""

    # HTMLファイルを保存
    with open('results/two_pane_view.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("[OK] 2ペインHTML生成完了: results/two_pane_view.html")
    print(f"   総意見数: {len(scores_df)} 件")
    print(f"   トピック数: {len(topics)} 個")
    print(f"   対立軸数: {len(axes)} 個")

if __name__ == '__main__':
    generate_html()
