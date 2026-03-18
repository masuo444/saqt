#!/usr/bin/env python3
"""
パイプライン管理スクリプト
案件の進捗をトラッキングする簡易CRM。
"""

import csv
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_PATH = os.path.join(BASE_DIR, "output", "pipeline.csv")

STAGES = [
    "lead",        # リード収集済み
    "analyzed",    # サイト分析済み
    "demo_sent",   # デモ＆メール送信済み
    "replied",     # 返信あり
    "meeting",     # 面談設定
    "proposal",    # 提案中
    "won",         # 受注
    "lost",        # 失注
]

FIELDNAMES = [
    "id", "name", "industry", "website", "phone", "email",
    "score", "stage", "amount", "demo_url", "notes",
    "created_at", "updated_at"
]


def load_pipeline():
    """パイプラインデータを読み込み"""
    if not os.path.exists(PIPELINE_PATH):
        return []
    with open(PIPELINE_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_pipeline(data):
    """パイプラインデータを保存"""
    os.makedirs(os.path.dirname(PIPELINE_PATH), exist_ok=True)
    with open(PIPELINE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(data)


def add_deal(data):
    """案件を追加"""
    next_id = max([int(d.get("id", 0)) for d in data], default=0) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("\n--- 新規案件追加 ---")
    name = input("  企業・店舗名: ").strip()
    industry = input("  業界 (例: beauty/dental/restaurant/salon/realestate/legal/gym): ").strip() or "other"
    website = input("  ウェブサイト: ").strip()
    phone = input("  電話番号: ").strip()
    email = input("  メール: ").strip()
    amount = input("  見込み金額（万円）: ").strip()

    deal = {
        "id": str(next_id),
        "name": name,
        "industry": industry,
        "website": website,
        "phone": phone,
        "email": email,
        "score": "",
        "stage": "lead",
        "amount": amount,
        "demo_url": "",
        "notes": "",
        "created_at": now,
        "updated_at": now,
    }

    data.append(deal)
    save_pipeline(data)
    print(f"\n  案件 #{next_id} を追加しました")
    return data


def update_stage(data):
    """案件のステージを更新"""
    if not data:
        print("\n案件がありません")
        return data

    show_pipeline(data)
    deal_id = input("\n更新する案件ID: ").strip()
    deal = next((d for d in data if d["id"] == deal_id), None)

    if not deal:
        print("案件が見つかりません")
        return data

    print(f"\n  現在のステージ: {deal['stage']}")
    print("  ステージ一覧:")
    for i, stage in enumerate(STAGES, 1):
        marker = " ← 現在" if stage == deal["stage"] else ""
        print(f"    {i}. {stage}{marker}")

    choice = input("\n  新しいステージ (番号): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(STAGES):
        deal["stage"] = STAGES[int(choice) - 1]
        deal["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        notes = input("  メモ（任意）: ").strip()
        if notes:
            existing = deal.get("notes", "")
            deal["notes"] = f"{existing} | {notes}" if existing else notes

        save_pipeline(data)
        print(f"\n  → {deal['name']} を '{deal['stage']}' に更新しました")

    return data


def show_pipeline(data):
    """パイプラインを表示"""
    if not data:
        print("\n案件がありません")
        return

    print(f"\n{'='*70}")
    print(f"  パイプライン - SAQT（サクッと）")
    print(f"{'='*70}")

    # ステージ別サマリー
    stage_counts = {}
    stage_amounts = {}
    for d in data:
        s = d.get("stage", "lead")
        stage_counts[s] = stage_counts.get(s, 0) + 1
        amt = float(d.get("amount", 0) or 0)
        stage_amounts[s] = stage_amounts.get(s, 0) + amt

    print("\n  【ステージ別】")
    for stage in STAGES:
        count = stage_counts.get(stage, 0)
        amount = stage_amounts.get(stage, 0)
        if count > 0:
            bar = "█" * count
            print(f"    {stage:12s} {bar} {count}件  ({amount:.0f}万円)")

    total_amount = sum(float(d.get("amount", 0) or 0) for d in data if d.get("stage") == "won")
    pipeline_amount = sum(float(d.get("amount", 0) or 0) for d in data
                         if d.get("stage") not in ("won", "lost"))

    print(f"\n  受注済み合計: {total_amount:.0f}万円")
    print(f"  パイプライン: {pipeline_amount:.0f}万円")

    # 案件一覧
    print(f"\n  {'ID':>4}  {'名前':<20}  {'ステージ':<12}  {'金額':>6}  {'更新日'}")
    print(f"  {'-'*4}  {'-'*20}  {'-'*12}  {'-'*6}  {'-'*16}")

    for d in data:
        print(f"  {d['id']:>4}  {d['name']:<20}  {d.get('stage',''):<12}  "
              f"{d.get('amount',''):>5}万  {d.get('updated_at','')}")


def import_from_leads(data):
    """分析済みリードCSVからインポート"""
    leads_dir = os.path.join(BASE_DIR, "output", "leads")
    csv_files = [f for f in os.listdir(leads_dir) if f.endswith("_analyzed.csv")]

    if not csv_files:
        print("\n分析済みCSVが見つかりません")
        return data

    print("\nインポート元:")
    for i, f in enumerate(csv_files, 1):
        print(f"  {i}. {f}")

    choice = input("\n選択: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(csv_files)):
        return data

    filepath = os.path.join(leads_dir, csv_files[int(choice) - 1])
    with open(filepath, "r", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))

    # 高優先度のみインポート
    high_priority = [l for l in leads if l.get("priority") in ("high", "medium")]
    existing_names = {d["name"] for d in data}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    next_id = max([int(d.get("id", 0)) for d in data], default=0) + 1
    imported = 0

    for lead in high_priority:
        if lead["name"] in existing_names:
            continue

        data.append({
            "id": str(next_id),
            "name": lead.get("name", ""),
            "industry": "beauty" if "beauty" in filepath.lower() or "美容" in filepath else "dental",
            "website": lead.get("website", ""),
            "phone": lead.get("phone", ""),
            "email": lead.get("email", ""),
            "score": lead.get("score", ""),
            "stage": "analyzed",
            "amount": "",
            "demo_url": "",
            "notes": lead.get("issues", ""),
            "created_at": now,
            "updated_at": now,
        })
        next_id += 1
        imported += 1

    save_pipeline(data)
    print(f"\n  {imported}件をインポートしました")
    return data


def main():
    print("=" * 60)
    print("  パイプライン管理 - SAQT（サクッと）")
    print("=" * 60)

    data = load_pipeline()

    while True:
        print("\n操作:")
        print("  1. パイプライン表示")
        print("  2. 案件追加")
        print("  3. ステージ更新")
        print("  4. リードCSVからインポート")
        print("  5. 終了")

        choice = input("\n選択: ").strip()

        if choice == "1":
            show_pipeline(data)
        elif choice == "2":
            data = add_deal(data)
        elif choice == "3":
            data = update_stage(data)
        elif choice == "4":
            data = import_from_leads(data)
        elif choice == "5":
            break
        else:
            print("無効な選択です")

    print("\n終了しました。")


if __name__ == "__main__":
    main()
