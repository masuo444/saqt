#!/usr/bin/env python3
"""
デモサイト自動生成スクリプト - SAQT（サクッと）
既存サイトの情報を読み取り、リニューアル後のデモを1ファイルHTMLで生成。
メール添付・ブラウザで即確認可能。
"""

import csv
import json
import os
import re
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "settings.json")
LEADS_DIR = os.path.join(BASE_DIR, "output", "leads")
DEMOS_DIR = os.path.join(BASE_DIR, "output", "demos")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_page(url, timeout=10):
    """ウェブページのHTMLを取得"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def extract_business_info(html, lead):
    """既存サイトからビジネス情報を抽出"""
    info = {
        "name": lead.get("name", "企業名"),
        "address": lead.get("address", ""),
        "phone": lead.get("phone", ""),
        "website": lead.get("website", ""),
    }

    if not html:
        return info

    # 営業時間
    time_match = re.search(
        r'(?:診療時間|受付時間|営業時間)[：:\s]*([^\n<]{5,80})',
        html, re.IGNORECASE
    )
    info["hours"] = time_match.group(1).strip() if time_match else ""

    # 定休日
    holiday_match = re.search(
        r'(?:休診日|定休日|休業日)[：:\s]*([^\n<]{2,40})',
        html, re.IGNORECASE
    )
    info["holiday"] = holiday_match.group(1).strip() if holiday_match else ""

    # サービス/メニュー
    for pattern in [
        r'(?:サービス|メニュー|事業内容|診療科目)[：:\s]*([^\n<]{5,200})',
    ]:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["services"] = match.group(1).strip()
            break
    if "services" not in info:
        info["services"] = ""

    # 代表者/院長
    rep_match = re.search(
        r'(?:代表|院長|オーナー|理事長)[：:\s]*([^\n<]{2,20})',
        html, re.IGNORECASE
    )
    info["representative"] = rep_match.group(1).strip() if rep_match else ""

    # メインカラーを推定
    colors = re.findall(r'#[0-9a-fA-F]{6}', html)
    if colors:
        filtered = [c for c in colors if c.lower() not in
                    ('#ffffff', '#000000', '#333333', '#666666', '#999999', '#f5f5f5')]
        if filtered:
            from collections import Counter
            info["theme_color"] = Counter(filtered).most_common(1)[0][0]
    if "theme_color" not in info:
        info["theme_color"] = "#f97316"

    # タイトルから業種推定
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    info["original_title"] = title_match.group(1).strip() if title_match else info["name"]

    # 説明文
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
    info["description"] = desc_match.group(1).strip() if desc_match else ""

    return info


def calculate_roi(lead):
    """ROI試算を生成"""
    score = lead.get("score", "")
    issues = lead.get("issues", "")
    roi_items = []

    if "スマホ未対応" in issues:
        roi_items.append({
            "problem": "スマートフォン未対応",
            "impact": "モバイルユーザー（全体の70%以上）がサイトを離脱",
            "solution": "レスポンシブ対応",
            "value": "問い合わせ数 1.5〜2倍の可能性"
        })

    if "予約" in issues or "問い合わせ" in issues:
        roi_items.append({
            "problem": "問い合わせ導線が不明確",
            "impact": "せっかくの訪問者が問い合わせせず離脱",
            "solution": "問い合わせ導線の最適化 + チャットボット",
            "value": "問い合わせ対応の人件費 年間最大240万円削減"
        })

    if "モダンCSS" in issues:
        roi_items.append({
            "problem": "デザインが古い印象",
            "impact": "第一印象で信頼を失い、競合に流れる",
            "solution": "モダンデザインへのリニューアル",
            "value": "ブランド信頼度の向上 → 成約率アップ"
        })

    if "SSL" in issues:
        roi_items.append({
            "problem": "SSL未対応（http://）",
            "impact": "ブラウザに「保護されていない通信」と表示",
            "solution": "SSL対応",
            "value": "セキュリティ信頼の回復 → 離脱率の低下"
        })

    # デフォルト
    if not roi_items:
        roi_items.append({
            "problem": "サイトの情報が古い",
            "impact": "最新のサービスや実績が伝わっていない",
            "solution": "コンテンツの刷新 + デザインリニューアル",
            "value": "新規顧客からの信頼獲得"
        })

    # チャットボットのROIは常に追加
    roi_items.append({
        "problem": "営業時間外の問い合わせに対応できない",
        "impact": "夜間・休日の問い合わせを取りこぼし",
        "solution": "24時間対応チャットボット導入",
        "value": "問い合わせ対応の自動化 → 人件費削減"
    })

    return roi_items


def generate_standalone_demo(info, roi_items, lead, config):
    """スタンドアロンHTMLデモを生成（1ファイルで完結）"""
    brand = config.get("brand", {})
    company = config.get("company", {})
    campaign = config.get("campaign", {}).get("chatbot_free", {})
    biz_name = info.get("name", "企業名")
    color = info.get("theme_color", "#f97316")
    score = lead.get("score", "N/A")
    issues = lead.get("issues", "")

    # ROI HTMLを生成
    roi_html = ""
    for item in roi_items:
        roi_html += f"""
        <div class="roi-item">
            <div class="roi-problem">
                <span class="roi-label">課題</span>
                <strong>{item['problem']}</strong>
                <p>{item['impact']}</p>
            </div>
            <div class="roi-arrow">→</div>
            <div class="roi-solution">
                <span class="roi-label">解決策</span>
                <strong>{item['solution']}</strong>
                <p class="roi-value">{item['value']}</p>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{biz_name}様 - リニューアルご提案 | SAQT</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Noto Sans JP', sans-serif; color: #1e293b; line-height: 1.8; background: #f8fafc; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 0 24px; }}

        /* Header */
        .header {{ background: #0f172a; color: #fff; padding: 40px 0; text-align: center; }}
        .header-badge {{ display: inline-block; background: rgba(249,115,22,0.15); color: #f97316; padding: 6px 18px; border-radius: 50px; font-size: 0.78rem; font-weight: 600; margin-bottom: 16px; border: 1px solid rgba(249,115,22,0.3); }}
        .header h1 {{ font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 8px; }}
        .header h1 span {{ color: #f97316; }}
        .header p {{ color: rgba(255,255,255,0.5); font-size: 0.85rem; }}

        /* Section */
        .section {{ padding: 48px 0; }}
        .section-title {{ font-size: 1.3rem; font-weight: 800; margin-bottom: 24px; color: #0f172a; letter-spacing: -0.03em; }}
        .section-title span {{ color: #f97316; }}

        /* Score */
        .score-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 32px; margin-bottom: 32px; }}
        .score-header {{ display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }}
        .score-circle {{ width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 900; color: #fff; flex-shrink: 0; }}
        .score-low {{ background: linear-gradient(135deg, #ef4444, #dc2626); }}
        .score-mid {{ background: linear-gradient(135deg, #f59e0b, #d97706); }}
        .score-high {{ background: linear-gradient(135deg, #10b981, #059669); }}
        .score-header h3 {{ font-size: 1.1rem; font-weight: 700; }}
        .score-header p {{ color: #64748b; font-size: 0.85rem; }}
        .issues-list {{ list-style: none; }}
        .issues-list li {{ padding: 8px 0 8px 24px; position: relative; font-size: 0.88rem; color: #475569; border-bottom: 1px solid #f1f5f9; }}
        .issues-list li::before {{ content: '!'; position: absolute; left: 0; color: #ef4444; font-weight: 700; }}

        /* ROI */
        .roi-item {{ display: flex; align-items: stretch; gap: 16px; margin-bottom: 20px; }}
        .roi-problem, .roi-solution {{ flex: 1; padding: 20px; border-radius: 12px; }}
        .roi-problem {{ background: #fef2f2; border: 1px solid #fecaca; }}
        .roi-solution {{ background: #f0fdf4; border: 1px solid #bbf7d0; }}
        .roi-label {{ display: inline-block; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 2px 10px; border-radius: 50px; margin-bottom: 8px; }}
        .roi-problem .roi-label {{ background: #fee2e2; color: #991b1b; }}
        .roi-solution .roi-label {{ background: #dcfce7; color: #166534; }}
        .roi-item strong {{ display: block; font-size: 0.92rem; margin-bottom: 4px; }}
        .roi-item p {{ font-size: 0.8rem; color: #64748b; }}
        .roi-value {{ color: #166534 !important; font-weight: 600; }}
        .roi-arrow {{ display: flex; align-items: center; color: #94a3b8; font-size: 1.2rem; font-weight: 700; flex-shrink: 0; }}

        /* Demo Preview */
        .demo-preview {{ background: #fff; border: 2px solid {color}; border-radius: 14px; overflow: hidden; margin-bottom: 32px; }}
        .demo-browser-bar {{ background: #f1f5f9; padding: 10px 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #e2e8f0; }}
        .demo-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
        .demo-dot:nth-child(1) {{ background: #ef4444; }}
        .demo-dot:nth-child(2) {{ background: #f59e0b; }}
        .demo-dot:nth-child(3) {{ background: #10b981; }}
        .demo-url {{ margin-left: 12px; background: #fff; padding: 4px 16px; border-radius: 6px; font-size: 0.75rem; color: #64748b; border: 1px solid #e2e8f0; }}
        .demo-body {{ padding: 0; }}

        /* Mini site preview */
        .mini-hero {{ background: linear-gradient(135deg, #0f172a, #1e293b); padding: 48px 32px; color: #fff; text-align: center; }}
        .mini-hero h2 {{ font-size: 1.4rem; font-weight: 800; margin-bottom: 8px; }}
        .mini-hero p {{ color: rgba(255,255,255,0.6); font-size: 0.85rem; }}
        .mini-features {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 32px; }}
        .mini-feature {{ text-align: center; padding: 20px 12px; }}
        .mini-feature-icon {{ width: 48px; height: 48px; border-radius: 12px; background: rgba(249,115,22,0.1); display: flex; align-items: center; justify-content: center; margin: 0 auto 12px; color: {color}; font-size: 1.2rem; }}
        .mini-feature h4 {{ font-size: 0.82rem; font-weight: 700; margin-bottom: 4px; }}
        .mini-feature p {{ font-size: 0.72rem; color: #64748b; }}
        .mini-cta {{ text-align: center; padding: 32px; background: {color}; color: #fff; }}
        .mini-cta h3 {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 8px; }}
        .mini-cta p {{ font-size: 0.82rem; opacity: 0.85; }}

        /* Campaign */
        .campaign-box {{ background: linear-gradient(135deg, #ea580c, #f97316); color: #fff; border-radius: 14px; padding: 32px; text-align: center; margin-bottom: 32px; }}
        .campaign-box h3 {{ font-size: 1.1rem; font-weight: 800; margin-bottom: 8px; }}
        .campaign-box p {{ font-size: 0.88rem; opacity: 0.9; }}

        /* CTA */
        .cta {{ background: #0f172a; color: #fff; padding: 48px 0; text-align: center; }}
        .cta h2 {{ font-size: 1.3rem; font-weight: 800; margin-bottom: 12px; }}
        .cta p {{ color: rgba(255,255,255,0.6); font-size: 0.88rem; margin-bottom: 24px; }}
        .cta-btn {{ display: inline-block; background: #f97316; color: #fff; padding: 14px 36px; border-radius: 50px; text-decoration: none; font-weight: 700; font-size: 0.92rem; }}

        /* Footer */
        .footer {{ padding: 24px 0; text-align: center; font-size: 0.75rem; color: #94a3b8; }}

        @media (max-width: 640px) {{
            .roi-item {{ flex-direction: column; }}
            .roi-arrow {{ transform: rotate(90deg); justify-content: center; }}
            .mini-features {{ grid-template-columns: 1fr; }}
            .score-header {{ flex-direction: column; text-align: center; }}
        }}
    </style>
</head>
<body>

    <header class="header">
        <div class="container">
            <div class="header-badge">SAQT（サクッと）からのご提案</div>
            <h1>{biz_name}様の<br>サイト<span>リニューアルプラン</span></h1>
            <p>作成日: {datetime.now().strftime('%Y年%m月%d日')}</p>
        </div>
    </header>

    <!-- 診断結果 -->
    <section class="section">
        <div class="container">
            <h2 class="section-title">現サイトの<span>診断結果</span></h2>
            <div class="score-card">
                <div class="score-header">
                    <div class="score-circle {'score-low' if str(score).isdigit() and int(score) <= 40 else 'score-mid' if str(score).isdigit() and int(score) <= 65 else 'score-high'}">
                        {score if score else '?'}
                    </div>
                    <div>
                        <h3>{biz_name}様の現サイトスコア</h3>
                        <p>{'改善の余地が大きく、リニューアルの効果が期待できます' if str(score).isdigit() and int(score) <= 50 else '改善ポイントがいくつかあります' if str(score).isdigit() and int(score) <= 70 else '基本的な対応はされていますが、さらに改善できます'}</p>
                    </div>
                </div>
                <ul class="issues-list">
                    {''.join(f'<li>{issue.strip()}</li>' for issue in issues.split('/') if issue.strip() and issue.strip() != '問題なし')}
                </ul>
            </div>
        </div>
    </section>

    <!-- ROI試算 -->
    <section class="section" style="background:#fff; border-top:1px solid #e2e8f0;">
        <div class="container">
            <h2 class="section-title">リニューアルで<span>得られる効果</span></h2>
            {roi_html}
        </div>
    </section>

    <!-- デモプレビュー -->
    <section class="section">
        <div class="container">
            <h2 class="section-title">リニューアル後の<span>イメージ</span></h2>
            <div class="demo-preview">
                <div class="demo-browser-bar">
                    <div class="demo-dot"></div>
                    <div class="demo-dot"></div>
                    <div class="demo-dot"></div>
                    <span class="demo-url">https://{biz_name.lower().replace(' ', '')}.jp</span>
                </div>
                <div class="demo-body">
                    <div class="mini-hero" style="background: linear-gradient(135deg, #0f172a, #1e293b);">
                        <h2>{biz_name}</h2>
                        <p>{info.get('description', f'{biz_name}の公式サイト')[:60]}</p>
                    </div>
                    <div class="mini-features">
                        <div class="mini-feature">
                            <div class="mini-feature-icon">📱</div>
                            <h4>スマホ完全対応</h4>
                            <p>どのデバイスでも最適表示</p>
                        </div>
                        <div class="mini-feature">
                            <div class="mini-feature-icon">💬</div>
                            <h4>チャットボット</h4>
                            <p>24時間自動で問い合わせ対応</p>
                        </div>
                        <div class="mini-feature">
                            <div class="mini-feature-icon">🌐</div>
                            <h4>多言語対応</h4>
                            <p>外国人のお客様にも対応</p>
                        </div>
                    </div>
                    <div class="mini-cta" style="background: {color};">
                        <h3>お問い合わせ・ご予約</h3>
                        <p>{info.get('phone', '')} {f"/ {info.get('hours', '')}" if info.get('hours') else ''}</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- キャンペーン -->
    <section class="section" style="padding-top:0;">
        <div class="container">
            <div class="campaign-box">
                <h3>【期間限定】チャットボット無料導入キャンペーン</h3>
                <p>{campaign.get('description', '4月末までにご依頼でチャットボット（30万円相当）を無料導入')}</p>
            </div>
        </div>
    </section>

    <!-- CTA -->
    <section class="cta">
        <div class="container">
            <h2>このリニューアルプランについて<br>詳しくお話しませんか？</h2>
            <p>オンラインで短時間、デモをお見せしながらご説明します。<br>ご採用いただかない場合でも費用は一切かかりません。</p>
            <a href="mailto:{company.get('email', 'info@saqt-ai.com')}?subject={biz_name}のリニューアルについて" class="cta-btn">
                メールで日程を調整する
            </a>
        </div>
    </section>

    <footer class="footer">
        <div class="container">
            <p>SAQT（サクッと） | {brand.get('domain', 'saqt-ai.com')} | 運営: {company.get('name', '合同会社FOMUS')}</p>
        </div>
    </footer>

</body>
</html>"""

    return html


def main():
    config = load_config()

    print("=" * 60)
    print("  デモサイト自動生成 - SAQT（サクッと）")
    print("=" * 60)

    csv_files = [f for f in os.listdir(LEADS_DIR) if f.endswith("_analyzed.csv")]

    if not csv_files:
        print("\n分析済みCSVが見つかりません。")
        print("先に 02_analyze_sites.py を実行してください。")
        return

    print("\n対象CSVファイル:")
    for i, f in enumerate(csv_files, 1):
        print(f"  {i}. {f}")

    choice = input("\n選択 (番号): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(csv_files)):
        print("無効な選択です")
        return

    csv_file = csv_files[int(choice) - 1]
    filepath = os.path.join(LEADS_DIR, csv_file)

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        leads = [row for row in reader if row.get("priority") in ("high", "medium")]

    if not leads:
        print("\n高・中優先度のリードがありません。")
        return

    print(f"\n高・中優先度リード: {len(leads)}件")
    print(f"デモサイト生成を開始...\n")

    os.makedirs(DEMOS_DIR, exist_ok=True)
    generated = []

    for lead in leads:
        name = lead.get("name", "不明")
        website = lead.get("website", "")
        print(f"  {name}")

        # 既存サイトから情報を抽出
        html = fetch_page(website) if website else None
        info = extract_business_info(html, lead)

        # ROI試算を生成
        roi_items = calculate_roi(lead)

        # スタンドアロンHTMLデモを生成
        demo_html = generate_standalone_demo(info, roi_items, lead, config)

        # 保存
        safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}_{safe_name}.html"
        filepath = os.path.join(DEMOS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(demo_html)

        print(f"    → 生成完了: {filepath}")
        generated.append({"name": name, "path": filepath})

    print(f"\n{'=' * 60}")
    print(f"  {len(generated)}件のデモを生成しました")
    print(f"  保存先: {DEMOS_DIR}")
    print(f"")
    print(f"  各HTMLファイルはブラウザで直接開けます。")
    print(f"  メールに添付して営業にも使えます。")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
