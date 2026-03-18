#!/usr/bin/env python3
"""
全自動営業パイプライン - SAQT（サクッと）

1コマンドで以下を一気通貫で実行:
  1. リード収集（Google Maps）
  2. サイト診断・スコアリング
  3. デモサイト自動生成
  4. 営業メール送信（デモURL付き）
  5. フォローアップ送信（3日経過分）

日次で cron 実行することを想定。
"""

import json
import os
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "settings.json")
LOG_DIR = os.path.join(BASE_DIR, "output", "logs")


def log(message):
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)

    # ファイルにも記録
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_smtp():
    """SMTP設定の確認"""
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        log(f"⚠ SMTP未設定: {', '.join(missing)}")
        log("  メール送信はスキップされます（下書きのみ保存）")
        return False
    return True


def check_google_api():
    """Google Maps API設定の確認"""
    if not os.environ.get("GOOGLE_MAPS_API_KEY"):
        log("⚠ GOOGLE_MAPS_API_KEY未設定")
        log("  リード収集はスキップされます（手動CSV使用）")
        return False
    return True


def run_step(script_name, description):
    """個別スクリプトを自動モードで実行"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        log(f"✗ {description}: スクリプトが見つかりません ({script_name})")
        return False

    log(f"▶ {description} 開始...")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input="1\n1\n",  # 自動選択（最初のオプションを選択）
            capture_output=True,
            text=True,
            timeout=300,
            cwd=BASE_DIR,
        )
        if result.returncode == 0:
            log(f"✓ {description} 完了")
            # 重要な出力行を抽出
            for line in result.stdout.split("\n"):
                if any(kw in line for kw in ["件", "完了", "保存", "送信", "成功"]):
                    log(f"  {line.strip()}")
            return True
        else:
            log(f"✗ {description} エラー")
            if result.stderr:
                log(f"  {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"✗ {description} タイムアウト（5分）")
        return False
    except Exception as e:
        log(f"✗ {description} 例外: {e}")
        return False


def main():
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║   SAQT 全自動営業パイプライン                      ║")
    print("║   リード収集 → 分析 → デモ生成 → メール送信        ║")
    print("╚════════════════════════════════════════════════════╝")
    print()

    log("=== パイプライン開始 ===")

    has_api = check_google_api()
    has_smtp = check_smtp()

    results = {}

    # Step 1: リード収集
    if has_api:
        results["collect"] = run_step("01_collect_leads.py", "Step 1: リード収集")
    else:
        log("⏭ Step 1: リード収集をスキップ（API未設定）")
        results["collect"] = None

    # Step 2: サイト診断
    results["analyze"] = run_step("02_analyze_sites.py", "Step 2: サイト診断")

    # Step 3: デモサイト生成
    results["demo"] = run_step("03_generate_demo.py", "Step 3: デモサイト生成")

    # Step 4: 営業メール送信
    if has_smtp:
        # 全自動モード（3）でOutreachを実行
        script_path = os.path.join(SCRIPTS_DIR, "04_send_outreach.py")
        log("▶ Step 4: 営業メール送信 開始...")
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                input="3\n",  # 全自動モード
                capture_output=True,
                text=True,
                timeout=600,
                cwd=BASE_DIR,
            )
            if result.returncode == 0:
                log("✓ Step 4: 営業メール送信 完了")
                for line in result.stdout.split("\n"):
                    if any(kw in line for kw in ["送信", "完了", "件", "フォロー"]):
                        log(f"  {line.strip()}")
                results["outreach"] = True
            else:
                log("✗ Step 4: エラー")
                results["outreach"] = False
        except Exception as e:
            log(f"✗ Step 4: {e}")
            results["outreach"] = False
    else:
        log("⏭ Step 4: メール送信をスキップ（SMTP未設定・下書きのみ）")
        # 下書きモードで実行
        run_step("04_send_outreach.py", "Step 4: 営業メール下書き保存")
        results["outreach"] = None

    # サマリー
    log("")
    log("=== パイプライン完了 ===")
    log("")
    for step, result in results.items():
        if result is True:
            status = "✓ 成功"
        elif result is False:
            status = "✗ 失敗"
        else:
            status = "⏭ スキップ"
        log(f"  {step}: {status}")

    log("")
    log(f"ログ: {LOG_DIR}")
    log("次回実行: crontab に登録すれば日次で自動実行されます")
    log("")
    log("  cron設定例（毎朝9時に実行）:")
    log(f"  0 9 * * 1-5 cd {BASE_DIR} && python3 scripts/06_auto_pipeline.py")
    log("")


if __name__ == "__main__":
    main()
