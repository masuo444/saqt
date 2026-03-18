#!/usr/bin/env python3
"""
SAQT（サクッと）- 営業自動化システム
運営: 合同会社FOMUS
メインランチャー
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")


def main():
    print()
    print("╔════════════════════════════════════════════════╗")
    print("║   SAQT（サクッと）- 営業自動化システム          ║")
    print("║   サクッと作って、しっかり届く。                ║")
    print("╚════════════════════════════════════════════════╝")
    print()
    print("  【ワークフロー】")
    print("  Step 1 → リード収集（Google Mapsから候補を取得）")
    print("  Step 2 → サイト診断（改善余地をスコアリング）")
    print("  Step 3 → デモサイト生成（テンプレートから自動生成）")
    print("  Step 4 → 営業メール送信（パーソナライズして送信）")
    print("  Step 5 → パイプライン管理（案件の進捗管理）")
    print()

    scripts = [
        ("1", "01_collect_leads.py", "リード収集"),
        ("2", "02_analyze_sites.py", "サイト診断"),
        ("3", "03_generate_demo.py", "デモサイト生成"),
        ("4", "04_send_outreach.py", "営業メール送信"),
        ("5", "05_pipeline.py", "パイプライン管理"),
        ("6", "06_auto_pipeline.py", "全自動パイプライン（1〜4を一括実行）"),
    ]

    for num, _, label in scripts:
        print(f"  {num}. {label}")
    print(f"  q. 終了")

    choice = input("\n  実行するステップを選択: ").strip().lower()

    if choice == "q":
        print("\n  終了します。")
        return

    selected = next((s for s in scripts if s[0] == choice), None)
    if not selected:
        print("\n  無効な選択です。")
        return

    script_path = os.path.join(SCRIPTS_DIR, selected[1])
    print(f"\n  {selected[2]}を起動します...\n")
    subprocess.run([sys.executable, script_path])


if __name__ == "__main__":
    main()
