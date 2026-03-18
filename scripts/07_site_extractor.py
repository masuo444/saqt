#!/usr/bin/env python3
"""
サイト情報抽出スクリプト - SAQT（サクッと）
相手のサイトの全テキスト・画像・ナビ構造・カラーを自動抽出。
デモサイト自動生成の入力データを作る。
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "extractions")


def fetch_page(url, timeout=15):
    """ページのHTMLを取得"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as res:
            content_type = res.headers.get("Content-Type", "")
            # 文字コード判定
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].strip()
            raw = res.read()
            # HTML内のcharset宣言を確認（最優先）
            raw_peek = raw[:2000].decode("ascii", errors="ignore")
            html_charset = re.search(r'charset[=\s]*["\']?([a-zA-Z0-9_-]+)', raw_peek, re.I)
            if html_charset:
                charset = html_charset.group(1).strip()

            # デコード試行（charset → 一般的な日本語エンコーディング）
            for enc in [charset, "shift_jis", "cp932", "euc-jp", "utf-8", "iso-2022-jp"]:
                try:
                    html = raw.decode(enc, errors="ignore")
                    # 日本語が含まれていれば成功とみなす
                    if re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', html):
                        return html
                except (LookupError, UnicodeDecodeError):
                    continue
            return raw.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  取得失敗: {e}")
        return None


def extract_title(html):
    """タイトルを抽出"""
    match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    return match.group(1).strip() if match else ""


def extract_meta_description(html):
    """meta descriptionを抽出"""
    match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.I)
    if not match:
        match = re.search(r'<meta[^>]*content=["\']([^"\']+)[^>]*name=["\']description["\']', html, re.I)
    return match.group(1).strip() if match else ""


def extract_nav_links(html, base_url):
    """ナビゲーションリンクを抽出"""
    nav_links = []
    # nav タグ内のリンク
    nav_match = re.search(r'<nav[^>]*>(.*?)</nav>', html, re.I | re.DOTALL)
    if nav_match:
        nav_html = nav_match.group(1)
    else:
        # ヘッダー内のリンクを代替
        header_match = re.search(r'<header[^>]*>(.*?)</header>', html, re.I | re.DOTALL)
        nav_html = header_match.group(1) if header_match else html[:5000]

    links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', nav_html, re.I | re.DOTALL)
    for href, text in links:
        text_clean = re.sub(r'<[^>]+>', '', text).strip()
        if text_clean and len(text_clean) < 30 and not text_clean.startswith("http"):
            # 相対URLを絶対URLに
            if href.startswith("/"):
                parsed = urllib.parse.urlparse(base_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif not href.startswith("http"):
                href = urllib.parse.urljoin(base_url, href)
            nav_links.append({"text": text_clean, "url": href})

    return nav_links


def extract_images(html, base_url):
    """画像URLを全て抽出"""
    images = []
    img_tags = re.findall(r'<img[^>]*>', html, re.I)
    for img in img_tags:
        src_match = re.search(r'src=["\']([^"\']+)["\']', img, re.I)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', img, re.I)
        if src_match:
            src = src_match.group(1)
            alt = alt_match.group(1) if alt_match else ""
            # 相対URLを絶対URLに
            if src.startswith("/"):
                parsed = urllib.parse.urlparse(base_url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            elif not src.startswith("http"):
                src = urllib.parse.urljoin(base_url, src)
            # 小さいアイコンやトラッキングピクセルを除外
            if not any(x in src.lower() for x in ["spacer", "pixel", "1x1", ".gif", "tracking", "analytics"]):
                images.append({"src": src, "alt": alt})
    return images


def extract_colors(html):
    """使用されているカラーを抽出"""
    colors = re.findall(r'#[0-9a-fA-F]{6}', html)
    # CSSファイルからも取得
    css_urls = re.findall(r'<link[^>]*href=["\']([^"\']*\.css[^"\']*)["\']', html, re.I)

    # 頻度順にソート（白黒グレー除外）
    exclude = {'#ffffff', '#000000', '#333333', '#666666', '#999999',
               '#f5f5f5', '#fafafa', '#eeeeee', '#dddddd', '#cccccc',
               '#FFFFFF', '#000000'}
    filtered = [c.lower() for c in colors if c.lower() not in {x.lower() for x in exclude}]

    if filtered:
        from collections import Counter
        counted = Counter(filtered).most_common(10)
        return [{"color": c, "count": n} for c, n in counted]
    return []


def extract_sections(html):
    """ページのセクション構造を抽出（見出し + その下のテキスト）"""
    sections = []

    # scriptとstyleを除去
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.I)

    # h1-h4を見つけてセクション分割
    headings = list(re.finditer(r'<(h[1-4])[^>]*>(.*?)</\1>', clean, re.I | re.DOTALL))

    for i, match in enumerate(headings):
        tag = match.group(1)
        heading_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if not heading_text:
            continue

        # このhタグから次のhタグまでのテキストを取得
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(clean)
        section_html = clean[start:end]

        # HTMLタグを除去してテキスト化
        section_text = re.sub(r'<[^>]+>', ' ', section_html)
        section_text = re.sub(r'\s+', ' ', section_text).strip()

        # リンクを抽出
        links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', section_html, re.I | re.DOTALL)
        section_links = []
        for href, link_text in links:
            lt = re.sub(r'<[^>]+>', '', link_text).strip()
            if lt:
                section_links.append({"text": lt, "url": href})

        if heading_text and (section_text or section_links):
            sections.append({
                "level": tag,
                "heading": heading_text,
                "text": section_text[:500],  # 長すぎるテキストは切り詰め
                "links": section_links[:10],
            })

    return sections


def extract_contact_info(html):
    """連絡先情報を抽出"""
    info = {}

    # 電話番号
    phone = re.search(r'(?:TEL|電話|tel)[：:\s]*([0-9\-()（）]+)', html, re.I)
    if phone:
        info["phone"] = phone.group(1).strip()

    # FAX
    fax = re.search(r'(?:FAX|fax)[：:\s]*([0-9\-()（）]+)', html, re.I)
    if fax:
        info["fax"] = fax.group(1).strip()

    # メール
    email = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', html)
    if email:
        info["email"] = email.group(0)

    # 住所（〒から始まる）
    addr = re.search(r'〒[\d\-]+\s*[^\n<]{5,60}', html)
    if addr:
        info["address"] = addr.group(0).strip()

    # 営業時間
    hours = re.search(r'(?:営業時間|受付時間|診療時間|開館時間)[：:\s]*([^\n<]{5,80})', html, re.I)
    if hours:
        info["hours"] = hours.group(1).strip()

    # 休業日
    holiday = re.search(r'(?:定休日|休診日|休業日|休館日)[：:\s]*([^\n<]{2,40})', html, re.I)
    if holiday:
        info["holiday"] = holiday.group(1).strip()

    return info


def extract_all(url):
    """全情報を抽出"""
    print(f"\n  URL: {url}")
    print(f"  取得中...")

    html = fetch_page(url)
    if not html:
        return None

    print(f"  HTML取得完了 ({len(html)}文字)")

    result = {
        "url": url,
        "extracted_at": datetime.now().isoformat(),
        "title": extract_title(html),
        "description": extract_meta_description(html),
        "contact": extract_contact_info(html),
        "nav_links": extract_nav_links(html, url),
        "images": extract_images(html, url),
        "colors": extract_colors(html),
        "sections": extract_sections(html),
    }

    # 全テキスト（フォールバック用）
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.I)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    result["full_text"] = text[:5000]

    return result


def save_extraction(data, url):
    """抽出結果をJSONで保存"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace(".", "_")
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}_{domain}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def print_summary(data):
    """抽出結果のサマリーを表示"""
    print(f"\n  {'='*50}")
    print(f"  抽出結果サマリー")
    print(f"  {'='*50}")
    print(f"  タイトル: {data['title']}")
    print(f"  説明: {data['description'][:80]}..." if data['description'] else "  説明: なし")

    contact = data["contact"]
    if contact:
        print(f"\n  連絡先:")
        for k, v in contact.items():
            print(f"    {k}: {v}")

    print(f"\n  ナビリンク: {len(data['nav_links'])}件")
    for link in data["nav_links"][:8]:
        print(f"    - {link['text']}")

    print(f"\n  画像: {len(data['images'])}件")
    for img in data["images"][:5]:
        alt = f" ({img['alt']})" if img["alt"] else ""
        print(f"    - {img['src'][:60]}{alt}")

    print(f"\n  カラー:")
    for c in data["colors"][:5]:
        print(f"    {c['color']} ({c['count']}回)")

    print(f"\n  セクション: {len(data['sections'])}件")
    for sec in data["sections"][:8]:
        print(f"    [{sec['level']}] {sec['heading']}")


def main():
    print("=" * 60)
    print("  サイト情報抽出 - SAQT（サクッと）")
    print("=" * 60)

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("\n  抽出するサイトのURL: ").strip()

    if not url:
        print("  URLが入力されていません")
        return

    if not url.startswith("http"):
        url = "http://" + url

    data = extract_all(url)
    if not data:
        print("  抽出に失敗しました")
        return

    filepath = save_extraction(data, url)
    print_summary(data)

    print(f"\n  保存先: {filepath}")
    print(f"\n  次のステップ:")
    print(f"  この抽出データを使ってデモサイトを自動生成できます。")
    print(f"  python3 scripts/03_generate_demo.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
