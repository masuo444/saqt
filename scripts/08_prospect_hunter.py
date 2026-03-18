#!/usr/bin/env python3
"""
見込み客自動発見スクリプト - SAQT（サクッと）

Google Maps APIなしで動作。
指定エリア・業種のサイトをGoogle検索で発見し、
サイトからメールアドレスを自動抽出。
古いサイト（スコアが低い）を優先リードとしてリスト化。

使い方:
  python3 scripts/08_prospect_hunter.py
  python3 scripts/08_prospect_hunter.py --area 坂戸市 --industry 商工会
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "leads")
EXTRACT_DIR = os.path.join(BASE_DIR, "output", "extractions")


def search_google(query, num_results=20):
    """Google検索でサイトURLを取得（API不要）"""
    results = []
    # Google検索のスクレイピング（利用規約に注意。テスト用途）
    # 本番では Google Custom Search API（1日100回無料）を推奨
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}&num={num_results}&hl=ja"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="ignore")

        # URLを抽出
        urls = re.findall(r'href="/url\?q=(https?://[^&"]+)', html)
        # 重複除去 & Google自身のURLを除外
        seen = set()
        for u in urls:
            u = urllib.parse.unquote(u)
            domain = urllib.parse.urlparse(u).netloc
            if domain not in seen and "google" not in domain and "youtube" not in domain:
                seen.add(domain)
                results.append(u)
    except Exception as e:
        print(f"    検索エラー: {e}")

    return results[:num_results]


def fetch_and_extract_email(url, timeout=10):
    """サイトにアクセスしてメールアドレスを抽出"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()

        # 文字コード判定
        for enc in ["utf-8", "shift_jis", "cp932", "euc-jp"]:
            try:
                html = raw.decode(enc, errors="ignore")
                if re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', html):
                    break
            except (LookupError, UnicodeDecodeError):
                continue
        else:
            html = raw.decode("utf-8", errors="ignore")

        # メールアドレス抽出
        emails = set()

        # mailto:
        for m in re.findall(r'mailto:([^\s"\'?&]+)', html, re.I):
            m = m.strip().lower()
            if '@' in m and '.' in m.split('@')[1]:
                emails.add(m)

        # テキストから直接
        for e in re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html):
            e = e.strip().lower()
            if not any(x in e for x in ['example.', 'test.', 'noreply', '.png', '.jpg', '.css', '.js', 'wix', 'sentry', 'google.com']):
                emails.add(e)

        # タイトル抽出
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
        title = title_match.group(1).strip() if title_match else ""

        # 簡易スコアリング
        score = 100
        if not re.search(r'<meta[^>]*viewport', html, re.I):
            score -= 30
        if url.startswith("http://"):
            score -= 10
        for tag in [r'<font\s', r'<center>', r'<table[^>]*width=', r'bgcolor=']:
            if re.search(tag, html, re.I):
                score -= 5
        modern = sum(1 for p in [r'display:\s*flex', r'display:\s*grid', r'@media\s*\(']
                     if re.search(p, html, re.I))
        if modern == 0:
            score -= 10
        score = max(0, score)

        # info@ を優先
        email_list = sorted(emails, key=lambda e: (0 if e.startswith('info@') else 1))

        return {
            "title": title,
            "emails": email_list,
            "score": score,
            "html_length": len(html),
        }

    except Exception as e:
        return {"title": "", "emails": [], "score": -1, "html_length": 0, "error": str(e)}


def main():
    print("=" * 60)
    print("  見込み客自動発見 - SAQT（サクッと）")
    print("=" * 60)

    # 引数からエリアと業種を取得
    area = ""
    industry = ""
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--area" and i + 2 <= len(sys.argv[1:]):
            area = sys.argv[i + 2]
        if arg == "--industry" and i + 2 <= len(sys.argv[1:]):
            industry = sys.argv[i + 2]

    if not area:
        area = input("\n  エリア（例: 坂戸市、渋谷区）: ").strip()
    if not industry:
        industry = input("  業種（例: 美容室、歯科、商工会）: ").strip()

    if not area or not industry:
        print("  エリアと業種を指定してください")
        return

    # 検索クエリ
    queries = [
        f"{industry} {area}",
        f"{industry} {area} ホームページ",
    ]

    print(f"\n  検索: {industry} × {area}")
    print(f"  ────────────────────────")

    all_urls = []
    for query in queries:
        print(f"\n  Google検索: {query}")
        urls = search_google(query, 15)
        print(f"    → {len(urls)}件のサイトを発見")
        all_urls.extend(urls)
        time.sleep(2)  # レート制限

    # 重複除去
    seen_domains = set()
    unique_urls = []
    for url in all_urls:
        domain = urllib.parse.urlparse(url).netloc
        if domain not in seen_domains:
            seen_domains.add(domain)
            unique_urls.append(url)

    print(f"\n  ユニークサイト: {len(unique_urls)}件")
    print(f"  メールアドレス抽出中...\n")

    # 各サイトからメール抽出 + スコアリング
    leads = []
    for i, url in enumerate(unique_urls):
        domain = urllib.parse.urlparse(url).netloc
        print(f"  [{i+1}/{len(unique_urls)}] {domain}")

        result = fetch_and_extract_email(url)
        title = result["title"]
        emails = result["emails"]
        score = result["score"]

        if emails:
            email_str = emails[0]
            status = f"✓ メール発見: {email_str}"
        else:
            email_str = ""
            status = "✗ メールなし"

        if score >= 0:
            if score <= 40:
                priority = "high"
                score_label = f"スコア {score}/100 ★★★"
            elif score <= 65:
                priority = "medium"
                score_label = f"スコア {score}/100 ★★"
            else:
                priority = "low"
                score_label = f"スコア {score}/100 ★"
        else:
            priority = "error"
            score_label = "取得失敗"

        print(f"       {title[:30]}... | {score_label} | {status}")

        leads.append({
            "name": title if title else domain,
            "website": url,
            "domain": domain,
            "email": email_str,
            "emails_all": ",".join(emails),
            "score": score,
            "priority": priority,
            "area": area,
            "industry": industry,
        })

        time.sleep(1)  # レート制限

    # 結果をCSVに保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_area = area.replace(" ", "_")
    safe_industry = industry.replace(" ", "_")
    filename = f"{date_str}_{safe_industry}_{safe_area}_prospects.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    fieldnames = ["name", "website", "domain", "email", "emails_all",
                   "score", "priority", "area", "industry"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)

    # サマリー
    with_email = [l for l in leads if l["email"]]
    high_priority = [l for l in leads if l["priority"] == "high" and l["email"]]
    medium_priority = [l for l in leads if l["priority"] == "medium" and l["email"]]

    print(f"\n  {'='*50}")
    print(f"  結果サマリー")
    print(f"  {'='*50}")
    print(f"  検索サイト数: {len(leads)}")
    print(f"  メール発見:   {len(with_email)}件")
    print(f"  高優先度（メールあり・スコア低）: {len(high_priority)}件")
    print(f"  中優先度（メールあり）:           {len(medium_priority)}件")
    print(f"  保存先: {filepath}")

    if high_priority:
        print(f"\n  === 営業メール送信候補（高優先度）===")
        for l in high_priority[:10]:
            print(f"    {l['name'][:25]} | {l['email']} | スコア{l['score']}")

    print(f"\n  次のステップ:")
    print(f"  このCSVを 04_send_outreach.py に渡してメール送信")
    print(f"  または /saqt-proposal [URL] で個別にデモ生成+メール送信")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
