#!/bin/bash
# === SAQT 本番起動スクリプト ===
# 使い方: chmod +x start.sh && ./start.sh

set -e
cd "$(dirname "$0")"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   SAQT（サクッと）本番セットアップ              ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# --- .env 読み込み ---
if [ -f .env ]; then
    echo "✓ .env ファイル読み込み"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠ .env ファイルが見つかりません"
    echo "  cp .env.example .env して値を設定してください"
    exit 1
fi

# --- 必須チェック ---
ERRORS=0

if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASS" ]; then
    echo "✗ SMTP設定が不完全です（メール送信不可）"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ SMTP: $SMTP_USER"
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠ GEMINI_API_KEY 未設定（テンプレートモードで動作）"
else
    echo "✓ Gemini API: 設定済み"
fi

if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
    echo "⚠ GOOGLE_MAPS_API_KEY 未設定（手動CSV入力モード）"
else
    echo "✓ Google Maps API: 設定済み"
fi

echo ""

if [ $ERRORS -gt 0 ]; then
    echo "エラーがあります。.env を確認してください。"
    exit 1
fi

# --- メニュー ---
echo "何をしますか？"
echo ""
echo "  1. HPをローカルで確認（ブラウザで開く）"
echo "  2. HPをVercelにデプロイ"
echo "  3. 全自動営業パイプラインを実行（1回）"
echo "  4. 全自動営業パイプラインをcronに登録（平日毎朝9時）"
echo "  5. メインランチャー（個別スクリプト実行）"
echo ""

read -p "  選択 (1-5): " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "ブラウザで開きます..."
        open fomus-hp/index.html
        ;;
    2)
        echo ""
        echo "Vercelにデプロイします..."
        if ! command -v vercel &> /dev/null; then
            echo "Vercel CLIがインストールされていません。"
            echo "  npm i -g vercel"
            echo "でインストールしてから再実行してください。"
            exit 1
        fi
        cd fomus-hp
        vercel --prod
        cd ..
        echo ""
        echo "✓ デプロイ完了！"
        ;;
    3)
        echo ""
        echo "全自動営業パイプラインを実行します..."
        python3 scripts/06_auto_pipeline.py
        ;;
    4)
        echo ""
        SCRIPT_PATH="$(pwd)/scripts/06_auto_pipeline.py"
        ENV_PATH="$(pwd)/.env"

        # launchd plist を作成
        PLIST_PATH="$HOME/Library/LaunchAgents/jp.saqt.autopipeline.plist"

        cat > "$PLIST_PATH" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>jp.saqt.autopipeline</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>export \$(grep -v '^#' ${ENV_PATH} | xargs) && /usr/bin/python3 ${SCRIPT_PATH}</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>${HOME}/Desktop/web制作/output/logs/cron_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/Desktop/web制作/output/logs/cron_stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
</dict>
</plist>
PLISTEOF

        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"

        echo "✓ cron登録完了！"
        echo "  スケジュール: 月〜金 毎朝9:00"
        echo "  ログ: output/logs/"
        echo ""
        echo "  停止するには:"
        echo "  launchctl unload $PLIST_PATH"
        ;;
    5)
        python3 run.py
        ;;
    *)
        echo "無効な選択です"
        ;;
esac
