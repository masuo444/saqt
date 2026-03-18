#!/usr/bin/env python3
"""
Telegram COO Bot「佐倉」（サクちゃん）- SAQT
Founderの最強の秘書。営業管理・通知・相談対応を全てTelegramで。

機能:
- 毎朝ブリーフィング（予定、返信待ち、送信済み）
- メール送信前の承認/却下
- Gmail返信検知 → 即通知
- 週次レポート
- フォローアップリマインド
- 事業相談への回答（Gemini連携）
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import smtplib
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

SENT_LOG = os.path.join(BASE_DIR, "output", "emails", "sent_log.csv")
PIPELINE_PATH = os.path.join(BASE_DIR, "output", "pipeline.csv")


# ============================================================
# Telegram送受信
# ============================================================

def send_message(text, parse_mode="HTML", reply_markup=None):
    """Telegramにメッセージを送信"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠ Telegram設定が不完全")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text[:4000],  # Telegram上限4096文字
        "parse_mode": parse_mode,
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            result = json.loads(res.read().decode("utf-8"))
            return result.get("result", {}).get("message_id")
    except Exception as e:
        print(f"  ⚠ Telegram送信エラー: {e}")
        return None


def get_updates(offset=None, timeout=30):
    """Telegramからの更新を取得"""
    if not TELEGRAM_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    try:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(full_url, timeout=timeout + 5) as res:
            return json.loads(res.read().decode("utf-8")).get("result", [])
    except Exception:
        return []


def answer_callback(callback_id):
    """コールバック応答"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    data = json.dumps({"callback_query_id": callback_id}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# ============================================================
# Gmail監視
# ============================================================

def check_new_replies():
    """Gmailで新しい返信をチェック"""
    if not SMTP_USER or not SMTP_PASS:
        return []

    replies = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SMTP_USER, SMTP_PASS)
        mail.select("inbox")

        # 直近24時間の未読メール
        since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(UNSEEN SINCE {since})')

        if status == "OK" and messages[0]:
            for num in messages[0].split()[:10]:  # 最大10件
                status, data = mail.fetch(num, "(RFC822)")
                if status == "OK":
                    msg = email_lib.message_from_bytes(data[0][1])

                    # 差出人
                    from_raw = msg.get("From", "")
                    from_decoded = ""
                    for part, enc in decode_header(from_raw):
                        if isinstance(part, bytes):
                            from_decoded += part.decode(enc or "utf-8", errors="ignore")
                        else:
                            from_decoded += part

                    # 件名
                    subject_raw = msg.get("Subject", "")
                    subject = ""
                    for part, enc in decode_header(subject_raw):
                        if isinstance(part, bytes):
                            subject += part.decode(enc or "utf-8", errors="ignore")
                        else:
                            subject += part

                    replies.append({
                        "from": from_decoded,
                        "subject": subject,
                        "date": msg.get("Date", ""),
                    })

        mail.logout()
    except Exception as e:
        print(f"  Gmail確認エラー: {e}")

    return replies


# ============================================================
# 送信ログ分析
# ============================================================

def get_sent_stats():
    """送信ログから統計を取得"""
    stats = {"total": 0, "today": 0, "this_week": 0, "followup_due": 0}

    if not os.path.exists(SENT_LOG):
        return stats

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    followup_emails = set()
    initial_emails = {}

    with open(SENT_LOG, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1
            sent_date = row.get("sent_at", "")[:10]

            if sent_date == today:
                stats["today"] += 1
            if sent_date >= week_ago:
                stats["this_week"] += 1

            if row.get("type") == "followup":
                followup_emails.add(row.get("email", ""))
            elif row.get("type") == "initial":
                due = row.get("followup_due", "")
                if due and due <= today and row.get("email") not in followup_emails:
                    stats["followup_due"] += 1

    return stats


# ============================================================
# Gemini相談機能
# ============================================================

def ask_gemini(question):
    """Geminiに事業相談"""
    if not GEMINI_API_KEY:
        return "Gemini APIキーが設定されていません。"

    system_prompt = """あなたは「佐倉」、SAQT（サクッと）のCOO（最高執行責任者）兼Founderの秘書です。

SAQTは合同会社FOMUSが運営するWeb制作サービスです。
- 古いサイトを最短3日でリニューアル
- 打ち合わせ1回、デモ無料
- チャットボット・多言語対応
- 補助金活用で実質7万円〜
- 料金: ライト20万〜 / スタンダード50万〜 / プロ100万〜
- 月額保守: 1万〜10万
- ドメイン: saqt-ai.com
- ターゲット: お金はあるけどHP放置している企業・自治体

あなたの役割:
- ボス（Founder）の事業相談に的確に回答する
- 営業戦略、価格設定、クライアント対応のアドバイス
- 数字に基づいた提案
- 簡潔で実用的な回答（200文字以内）
- 「AI」という言葉は使わない
- プロフェッショナルだが親しみやすい口調
- Founderのことは必ず「ボス」と呼ぶ"""

    request_body = json.dumps({
        "contents": [
            {"role": "user", "parts": [{"text": f"{system_prompt}\n\n質問: {question}"}]}
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300, "thinkingConfig": {"thinkingBudget": 0}}
    }).encode("utf-8")

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=request_body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode("utf-8"))

        # 回答テキストを取得（thinkingパートを除外）
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        answer = ""
        for part in parts:
            if "text" in part and not part.get("thought"):
                answer += part["text"]

        if not answer:
            return "回答を生成できませんでした。"

        # HTMLタグやマークダウンを除去してクリーンに
        answer = re.sub(r'<[^>]+>', '', answer)
        return answer.strip()[:800]
    except Exception as e:
        return f"エラー: {e}"


# ============================================================
# メイン機能
# ============================================================

def morning_briefing():
    """毎朝のブリーフィング"""
    stats = get_sent_stats()
    replies = check_new_replies()

    text = f"""☀️ <b>おはようございます。佐倉です。</b>
{datetime.now().strftime('%Y年%m月%d日（%A）')}

━━━━ 📊 営業状況 ━━━━
📤 累計送信: <b>{stats['total']}通</b>
📤 今日の送信: <b>{stats['today']}通</b>
📤 今週の送信: <b>{stats['this_week']}通</b>
🔄 フォロー待ち: <b>{stats['followup_due']}件</b>"""

    if replies:
        text += f"\n\n━━━━ 💬 新着返信 ({len(replies)}件) ━━━━"
        for r in replies[:5]:
            text += f"\n📩 <b>{r['from'][:30]}</b>\n   {r['subject'][:40]}"
        text += "\n\n⚡ <b>返信あり！Gmailを確認してください。</b>"
    else:
        text += "\n\n💬 新着返信: なし"

    if stats['followup_due'] > 0:
        text += f"\n\n⏰ <b>{stats['followup_due']}件のフォローアップが必要です。</b>"

    text += "\n\n何かご指示があればこちらにどうぞ。"

    return send_message(text)


def weekly_report():
    """週次レポート"""
    stats = get_sent_stats()

    text = f"""📊 <b>佐倉の週次レポート</b>
{datetime.now().strftime('%Y年%m月%d日')}

━━━━━━━━━━━━━━━
📤 今週の送信: <b>{stats['this_week']}通</b>
📤 累計送信: <b>{stats['total']}通</b>
🔄 フォロー待ち: <b>{stats['followup_due']}件</b>
━━━━━━━━━━━━━━━

来週の営業プランについてご相談があればお知らせください。"""

    return send_message(text)


def send_approval_request(lead_name, email_to, email_subject, email_body, demo_info=""):
    """営業メール送信の承認リクエスト"""
    text = f"""🔔 <b>営業メール送信確認</b>

<b>宛先:</b> {lead_name}
<b>メール:</b> {email_to}
<b>件名:</b> {email_subject}

━━━━━━━━━━━━━━━
{email_body[:600]}{'...' if len(email_body) > 600 else ''}
━━━━━━━━━━━━━━━"""

    if demo_info:
        text += f"\n📎 {demo_info}"

    text += "\n\n👆 送信しますか？"

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ 送信", "callback_data": f"approve"},
                {"text": "❌ やめる", "callback_data": f"reject"},
            ]
        ]
    }

    return send_message(text, reply_markup=reply_markup)


def wait_for_response(timeout_seconds=300):
    """Telegramからの応答を待つ"""
    start = time.time()
    last_id = None

    while time.time() - start < timeout_seconds:
        updates = get_updates(offset=last_id, timeout=10)

        for update in updates:
            last_id = update["update_id"] + 1

            # ボタン押下
            callback = update.get("callback_query")
            if callback:
                answer_callback(callback["id"])
                data = callback.get("data", "")
                if data == "approve":
                    send_message("✅ 了解しました。送信します。")
                    return "approved"
                elif data == "reject":
                    send_message("❌ 了解しました。スキップします。")
                    return "rejected"

            # テキストメッセージ（相談）
            msg = update.get("message", {})
            text = msg.get("text", "")
            if text and not text.startswith("/"):
                # 事業相談として回答
                handle_consultation(text)

        time.sleep(1)

    send_message("⏰ タイムアウト。スキップしました。")
    return "timeout"


def handle_consultation(question):
    """事業相談への回答"""
    send_message("🤔 考えています...")
    answer = ask_gemini(question)
    send_message(f"💡 <b>佐倉の回答:</b>\n\n{answer}")


def check_followup_reminders():
    """フォローアップリマインド"""
    if not os.path.exists(SENT_LOG):
        return

    today = datetime.now().strftime("%Y-%m-%d")
    followup_emails = set()
    due_items = []

    with open(SENT_LOG, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        if row.get("type") == "followup":
            followup_emails.add(row.get("email", ""))

    for row in rows:
        if row.get("type") == "initial":
            due = row.get("followup_due", "")
            if due == today and row.get("email") not in followup_emails:
                due_items.append(row)

    if due_items:
        text = f"⏰ <b>フォローアップリマインド</b>\n\n以下の{len(due_items)}件が本日フォロー期限です:\n"
        for item in due_items[:5]:
            text += f"\n📌 <b>{item.get('name', '不明')}</b> ({item.get('email', '')})"
        text += "\n\nフォローアップを送信しますか？"

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ 全件送信", "callback_data": "followup_all"},
                    {"text": "👀 後で", "callback_data": "later"},
                ]
            ]
        }
        send_message(text, reply_markup=reply_markup)


def notify_new_reply(from_addr, subject):
    """新着返信の即通知"""
    text = f"""📩 <b>返信がありました！</b>

<b>差出人:</b> {from_addr}
<b>件名:</b> {subject}

Gmailを確認してください。"""

    send_message(text)


# ============================================================
# 常駐モード（バックグラウンド実行）
# ============================================================

def run_daemon():
    """常駐モード：メッセージを監視し続ける"""
    print("佐倉（サクちゃん）常駐モード開始...")
    send_message("🤖 <b>佐倉、起動しました。</b>\n\n何でもご相談ください。メッセージを送るだけでOKです。")

    last_id = None
    last_mail_check = time.time()
    mail_check_interval = 300  # 5分ごとにメールチェック

    while True:
        try:
            updates = get_updates(offset=last_id, timeout=30)

            for update in updates:
                last_id = update["update_id"] + 1

                # ボタン押下
                callback = update.get("callback_query")
                if callback:
                    answer_callback(callback["id"])
                    data = callback.get("data", "")
                    if data == "later":
                        send_message("👍 了解です。")
                    continue

                # テキストメッセージ
                msg = update.get("message", {})
                text = msg.get("text", "")

                if not text:
                    continue

                # コマンド処理
                if text == "/start":
                    send_message("🤖 <b>佐倉です。</b>SAQTのCOOとして、何でもお手伝いします。\n\nメッセージを送るだけで相談できます。\n\n<b>コマンド:</b>\n/morning - 朝のブリーフィング\n/report - 週次レポート\n/status - 営業状況\n/mail - メールチェック")
                elif text == "/morning":
                    morning_briefing()
                elif text == "/report":
                    weekly_report()
                elif text == "/status":
                    stats = get_sent_stats()
                    send_message(f"📊 累計{stats['total']}通送信 / 今日{stats['today']}通 / フォロー待ち{stats['followup_due']}件")
                elif text == "/mail":
                    replies = check_new_replies()
                    if replies:
                        text_r = f"📩 <b>{len(replies)}件の新着メール</b>\n"
                        for r in replies[:5]:
                            text_r += f"\n• {r['from'][:30]}: {r['subject'][:40]}"
                        send_message(text_r)
                    else:
                        send_message("📭 新着メールはありません。")
                else:
                    # 事業相談
                    handle_consultation(text)

            # 定期メールチェック
            if time.time() - last_mail_check > mail_check_interval:
                replies = check_new_replies()
                if replies:
                    for r in replies[:3]:
                        notify_new_reply(r["from"], r["subject"])
                last_mail_check = time.time()

        except KeyboardInterrupt:
            send_message("🔌 佐倉、シャットダウンします。")
            break
        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(5)


# ============================================================
# エントリーポイント
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "get-chat-id":
            from scripts_helper import get_chat_id
            get_chat_id()
        elif cmd == "morning":
            morning_briefing()
        elif cmd == "report":
            weekly_report()
        elif cmd == "followup":
            check_followup_reminders()
        elif cmd == "daemon":
            run_daemon()
        elif cmd == "test":
            send_message("🤖 佐倉です。テストメッセージです。正常に動作しています。")
    else:
        # デフォルト: 常駐モード
        run_daemon()
