#!/usr/bin/env python3
"""
サイト自動診断スクリプト
収集したリードのウェブサイトをチェックし、改善余地をスコアリングする。
"""

import csv
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADS_DIR = os.path.join(BASE_DIR, "output", "leads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "leads")


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
    except Exception as e:
        print(f"    取得失敗: {e}")
        return None


def analyze_site(html, url):
    """サイトをスコアリング（100点満点）"""
    score = 100
    issues = []

    # 1. スマホ対応チェック（viewport meta tag）
    if not re.search(r'<meta[^>]*viewport', html, re.IGNORECASE):
        score -= 30
        issues.append("スマホ未対応（viewport設定なし）")

    # 2. デザインの新しさ（CSS指標）
    old_indicators = [
        (r'<table[^>]*width=', "tableレイアウト使用"),
        (r'<font\s', "fontタグ使用（非推奨）"),
        (r'<center>', "centerタグ使用（非推奨）"),
        (r'<marquee', "marqueeタグ使用"),
        (r'bgcolor=', "bgcolor属性使用"),
    ]
    for pattern, issue in old_indicators:
        if re.search(pattern, html, re.IGNORECASE):
            score -= 5
            issues.append(issue)

    # モダンCSS/フレームワークの有無
    modern_indicators = [
        r'flexbox|display:\s*flex',
        r'grid-template|display:\s*grid',
        r'bootstrap|tailwind',
        r'@media\s*\(',
    ]
    modern_count = sum(1 for p in modern_indicators if re.search(p, html, re.IGNORECASE))
    if modern_count == 0:
        score -= 10
        issues.append("モダンCSSフレームワーク未使用")

    # 3. 予約導線チェック
    booking_patterns = [
        r'予約|reserve|booking|appointment',
        r'お問い合わせ|contact',
        r'LINE|ライン',
    ]
    booking_found = sum(1 for p in booking_patterns if re.search(p, html, re.IGNORECASE))
    if booking_found == 0:
        score -= 20
        issues.append("予約・問い合わせ導線が不明確")
    elif booking_found == 1:
        score -= 10
        issues.append("予約導線が弱い（1つしかない）")

    # 4. SSL対応チェック
    if url.startswith("http://"):
        score -= 10
        issues.append("SSL未対応（http://）")

    # 5. 基本情報の有無
    info_patterns = {
        "営業時間/診療時間": r'営業時間|診療時間|受付時間|opening hours|business hours',
        "アクセス情報": r'アクセス|access|地図|map|最寄り駅',
        "スタッフ/会社紹介": r'スタッフ|代表|院長|医師紹介|about|会社概要|staff|doctor',
    }
    for label, pattern in info_patterns.items():
        if not re.search(pattern, html, re.IGNORECASE):
            score -= 5
            issues.append(f"{label}が見つからない")

    # 6. ページ内のリンク切れ的な指標（画像alt属性）
    img_tags = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    if img_tags:
        imgs_without_alt = sum(1 for img in img_tags if 'alt=' not in img.lower())
        if imgs_without_alt > len(img_tags) * 0.5:
            score -= 5
            issues.append(f"画像のalt属性不足（{imgs_without_alt}/{len(img_tags)}）")

    score = max(0, min(100, score))
    return score, issues


def process_leads_file(filepath):
    """リードCSVファイルを処理"""
    results = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"\n  {len(leads)}件のリードを分析中...")

    for lead in leads:
        website = lead.get("website", "").strip()
        name = lead.get("name", "不明")

        if not website:
            print(f"    {name}: サイトなし → スキップ")
            lead["score"] = ""
            lead["issues"] = "ウェブサイトなし"
            lead["priority"] = "low"
            results.append(lead)
            continue

        print(f"    {name}: {website}")
        html = fetch_page(website)

        if html is None:
            lead["score"] = ""
            lead["issues"] = "サイト取得失敗"
            lead["priority"] = "low"
            results.append(lead)
            continue

        score, issues = analyze_site(html, website)
        lead["score"] = score
        lead["issues"] = " / ".join(issues) if issues else "問題なし"

        # 優先度判定
        if score <= 40:
            lead["priority"] = "high"
            print(f"      → スコア {score}/100 ★★★ 高優先度")
        elif score <= 65:
            lead["priority"] = "medium"
            print(f"      → スコア {score}/100 ★★ 中優先度")
        else:
            lead["priority"] = "low"
            print(f"      → スコア {score}/100 ★ 低優先度（改善余地少）")

        results.append(lead)

    return results


def save_analyzed(results, original_filepath):
    """分析結果を保存"""
    date_str = datetime.now().strftime("%Y%m%d")
    basename = os.path.basename(original_filepath).replace(".csv", "")
    filename = f"{basename}_analyzed.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    fieldnames = [
        "name", "address", "rating", "reviews_count",
        "website", "phone", "email", "score", "issues",
        "priority", "status"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    # 優先度別サマリー
    high = sum(1 for r in results if r.get("priority") == "high")
    medium = sum(1 for r in results if r.get("priority") == "medium")

    print(f"\n  結果保存: {filepath}")
    print(f"  高優先度: {high}件 / 中優先度: {medium}件 / 合計: {len(results)}件")
    return filepath


def main():
    print("=" * 60)
    print("  サイト自動診断 - SAQT（サクッと）")
    print("=" * 60)

    # リードCSVを探す
    csv_files = [f for f in os.listdir(LEADS_DIR)
                 if f.endswith(".csv") and "analyzed" not in f and "template" not in f]

    if not csv_files:
        print("\nリードCSVが見つかりません。")
        print("先に 01_collect_leads.py を実行してください。")
        return

    print("\n分析対象のCSVファイル:")
    for i, f in enumerate(csv_files, 1):
        print(f"  {i}. {f}")
    print(f"  {len(csv_files) + 1}. 全て")

    choice = input("\n選択 (番号): ").strip()

    if choice == str(len(csv_files) + 1):
        selected = csv_files
    elif choice.isdigit() and 1 <= int(choice) <= len(csv_files):
        selected = [csv_files[int(choice) - 1]]
    else:
        print("無効な選択です")
        return

    for csv_file in selected:
        filepath = os.path.join(LEADS_DIR, csv_file)
        print(f"\n--- {csv_file} ---")
        results = process_leads_file(filepath)
        save_analyzed(results, filepath)

    print(f"\n{'=' * 60}")
    print("  診断完了！ 高優先度のリードからデモサイトを作成しましょう")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
