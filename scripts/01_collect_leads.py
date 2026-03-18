#!/usr/bin/env python3
"""
リード収集スクリプト
Google Maps APIを使って、ターゲット業界のビジネスを収集する。
APIキーがない場合は、手動CSV入力にも対応。
"""

import json
import csv
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "settings.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "leads")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search_google_maps(query, api_key, max_results=20):
    """Google Places APIでビジネスを検索"""
    results = []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "language": "ja",
        "key": api_key,
    }

    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full_url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    for place in data.get("results", [])[:max_results]:
        place_id = place.get("place_id", "")
        detail = get_place_details(place_id, api_key) if place_id else {}

        results.append({
            "name": place.get("name", ""),
            "address": place.get("formatted_address", ""),
            "rating": place.get("rating", ""),
            "reviews_count": place.get("user_ratings_total", 0),
            "place_id": place_id,
            "website": detail.get("website", ""),
            "phone": detail.get("formatted_phone_number", ""),
            "email": "",  # メールはサイトから別途抽出
            "status": "new",
        })
        time.sleep(0.3)  # レート制限対策

    return results


def get_place_details(place_id, api_key):
    """Place IDから詳細情報を取得"""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "website,formatted_phone_number",
        "language": "ja",
        "key": api_key,
    }
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full_url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("result", {})


def save_leads(leads, industry, area):
    """CSVにリードを保存"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}_{industry}_{area}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    fieldnames = [
        "name", "address", "rating", "reviews_count",
        "place_id", "website", "phone", "email", "status"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)

    print(f"  → {len(leads)}件を保存: {filepath}")
    return filepath


def create_sample_csv():
    """APIキーなしの場合のサンプルCSVテンプレートを作成"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "template_manual_input.csv")

    fieldnames = [
        "name", "address", "rating", "reviews_count",
        "place_id", "website", "phone", "email", "status"
    ]

    sample = [
        {
            "name": "サンプル店舗",
            "address": "東京都渋谷区神南1-1-1",
            "rating": "3.8",
            "reviews_count": "45",
            "place_id": "",
            "website": "https://example-business.jp",
            "phone": "03-1234-5678",
            "email": "info@example-business.jp",
            "status": "new",
        }
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample)

    print(f"\n手動入力用テンプレートを作成しました: {filepath}")
    print("このCSVにリード情報を手入力して、次のステップに進んでください。")
    print("\n【手動でリードを集める方法】")
    print("1. Google Mapsで「業種名 エリア名」（例: 美容室 渋谷区）を検索")
    print("2. 各店舗の名前・住所・サイトURL・電話番号をCSVに記入")
    print("3. statusは 'new' のままにしておく")
    return filepath


def main():
    config = load_config()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

    print("=" * 60)
    print("  リード収集 - SAQT（サクッと）")
    print("=" * 60)

    if not api_key:
        print("\n⚠ GOOGLE_MAPS_API_KEY が設定されていません。")
        print("APIキーを設定するか、手動でCSVを作成してください。")
        print("\n設定方法: export GOOGLE_MAPS_API_KEY='your-key-here'")
        create_sample_csv()
        return

    # ターゲット業界を選択
    targets = config["targets"]
    print("\nターゲット業界:")
    for i, (key, val) in enumerate(targets.items(), 1):
        print(f"  {i}. {val['label']}")
    print(f"  {len(targets) + 1}. 全て")

    choice = input("\n選択 (番号): ").strip()
    target_keys = list(targets.keys())

    if choice == str(len(targets) + 1):
        selected = target_keys
    elif choice.isdigit() and 1 <= int(choice) <= len(targets):
        selected = [target_keys[int(choice) - 1]]
    else:
        print("無効な選択です")
        return

    # エリアを選択
    areas = config["areas"]
    print("\nエリア:")
    for i, area in enumerate(areas, 1):
        print(f"  {i}. {area}")
    print(f"  {len(areas) + 1}. 全て")

    area_choice = input("\n選択 (番号/カンマ区切り): ").strip()

    if area_choice == str(len(areas) + 1):
        selected_areas = areas
    else:
        indices = [int(x.strip()) - 1 for x in area_choice.split(",") if x.strip().isdigit()]
        selected_areas = [areas[i] for i in indices if 0 <= i < len(areas)]

    if not selected_areas:
        print("エリアが選択されていません")
        return

    # 収集実行
    total_leads = 0
    for industry_key in selected:
        industry = targets[industry_key]
        print(f"\n--- {industry['label']} ---")

        for area in selected_areas:
            for query_template in industry["search_queries"]:
                query = query_template.format(area=area)
                print(f"\n検索中: {query}")
                leads = search_google_maps(query, api_key)
                if leads:
                    save_leads(leads, industry_key, area)
                    total_leads += len(leads)
                time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"  完了！ 合計 {total_leads} 件のリードを収集しました")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
