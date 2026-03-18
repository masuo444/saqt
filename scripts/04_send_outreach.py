#!/usr/bin/env python3
"""
営業メール自動生成・送信スクリプト - SAQT（サクッと）
デモサイトURLを含むパーソナライズメールを送信。
フォローアップ（3日後自動再送）にも対応。
"""

import csv
import json
import os
import re
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "settings.json")
LEADS_DIR = os.path.join(BASE_DIR, "output", "leads")
EMAILS_DIR = os.path.join(BASE_DIR, "output", "emails")
DEMOS_DIR = os.path.join(BASE_DIR, "output", "demos")
SENT_LOG = os.path.join(EMAILS_DIR, "sent_log.csv")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_site_content(url, timeout=10):
    """営業対象サイトの内容を取得（メール個別化のため）"""
    if not url:
        return ""
    try:
        import urllib.request
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # HTMLからテキストを抽出（タグ除去、スクリプト除去）
        import re
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:3000]  # トークン節約のため3000文字まで
    except Exception:
        return ""


def generate_email_with_gemini(lead, config, site_text):
    """Gemini APIでプロ品質の個別営業メールを生成"""
    import urllib.request
    import urllib.parse

    biz_name = lead.get("name", "")
    website = lead.get("website", "")
    issues = lead.get("issues", "")
    score = lead.get("score", "")
    address = lead.get("address", "")
    phone = lead.get("phone", "")
    company = config["company"]
    brand = config.get("brand", {})
    campaign = config.get("campaign", {}).get("chatbot_free", {})
    demo_file = find_demo_file(biz_name)

    prompt = f"""あなたはSAQT（サクッと）という Web制作サービスのトップ営業担当です。
年間100件以上の受注実績があり、初回メールの返信率は業界平均の3倍です。

以下の企業に対して、完全にパーソナライズされた営業メールを1通作成してください。

■ 営業対象の企業情報
企業名: {biz_name}
サイトURL: {website}
住所: {address}
電話: {phone}
サイト診断スコア: {score}/100
検出された問題: {issues}

■ 企業サイトから読み取った内容（抜粋）:
{site_text[:2000] if site_text else "（サイト情報取得不可）"}

■ SAQTのサービス情報（提案に使ってよい）:
- 最短3日でサイトリニューアル完了
- 打ち合わせは1回だけ、オンラインで完結
- ライト20万〜 / スタンダード50万〜 / プロ100万〜
- 補助金活用で実質7万円〜
- チャットボット導入でお問い合わせ対応を自動化
- 多言語対応可能
- キャンペーン: {campaign.get('description', '4月末までチャットボット無料導入')}
{'- デモHTMLを添付しています（ブラウザで開くとリニューアル案が見れます）' if demo_file else ''}

■ メール作成ルール（厳守）:
1. 件名に企業名を必ず入れる
2. 冒頭で「なぜこの企業に連絡したのか」を具体的に書く（サイトの何を見て、何が気になったか）
3. その企業固有の課題を2-3個、具体的に指摘する（一般論ではなく、実際にサイトを見た上での指摘）
4. その課題が放置されるとどうなるか（機会損失の金額感を出す）
5. SAQTならどう解決するかを簡潔に
6. 「お試しでリニューアル案を作成しました」的な文言を自然に入れる（添付ファイルがある場合）
7. 売り込み臭を出さない。あくまで「気づいたので共有します」というスタンス
8. 文末は「ご興味があれば」程度。押し売りしない
9. 全体で300〜400文字程度。長すぎない
10. 「AI」「人工知能」という言葉は絶対に使わない
11. 下手に出すぎない。プロフェッショナルとして対等に
12. テンプレート感を一切出さない。この企業のためだけに書いた文章にする

■ 出力フォーマット（このまま送信するので正確に）:
1行目: SUBJECT: （件名）
2行目: 空行
3行目以降: 本文

本文の最後に以下の署名を付ける:
━━━━━━━━━━━━━━━━━━
SAQT（サクッと）
{company.get('representative', '担当')}
Web: {brand.get('domain', 'saqt-ai.com')}
Email: {company.get('email', '')}
{f"Tel: {company['phone']}" if company.get('phone') else ""}
運営: 合同会社FOMUS
━━━━━━━━━━━━━━━━━━"""

    request_body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
        }
    }).encode("utf-8")

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(
            url,
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        if not text or "SUBJECT:" not in text:
            return None, None

        # 件名と本文を分離
        lines = text.strip().split("\n")
        subject_line = ""
        body_lines = []
        found_subject = False

        for line in lines:
            if line.strip().startswith("SUBJECT:") and not found_subject:
                subject_line = line.replace("SUBJECT:", "").strip()
                found_subject = True
            elif found_subject:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        if subject_line and body:
            return subject_line, body
        return None, None

    except Exception as e:
        print(f"    ⚠ Gemini API エラー: {e}")
        return None, None


def find_demo_file(lead_name):
    """リード名に対応するデモHTMLファイルを探す"""
    if not os.path.exists(DEMOS_DIR):
        return None
    safe_name = re.sub(r'[^\w\s-]', '', lead_name).strip().replace(' ', '_')
    for filename in sorted(os.listdir(DEMOS_DIR), reverse=True):
        if filename.endswith('.html') and safe_name in filename:
            return os.path.join(DEMOS_DIR, filename)
    return None


def generate_initial_email(lead, config):
    """初回営業メール（デモURL付き）"""
    biz_name = lead.get("name", "")
    issues = lead.get("issues", "")
    score = lead.get("score", "")
    company = config["company"]
    brand = config.get("brand", {})
    campaign = config.get("campaign", {}).get("chatbot_free", {})
    demo_file = find_demo_file(biz_name)

    # 課題から具体的な改善提案を生成
    improvements = []
    if "スマホ未対応" in issues:
        improvements.append("スマートフォン対応（現在未対応のため、モバイルユーザーを逃している可能性があります）")
    if "予約" in issues or "問い合わせ" in issues:
        improvements.append("問い合わせ導線の最適化（現在、問い合わせまでの動線が不明確です）")
    if "モダンCSS" in issues:
        improvements.append("デザインの刷新（現在のデザインは一世代前の印象です）")
    if "SSL" in issues:
        improvements.append("SSL対応（ブラウザに「保護されていない通信」と表示される状態です）")
    if "alt属性" in issues:
        improvements.append("SEO基礎の改善（画像のalt属性などが不足しています）")

    if not improvements:
        improvements.append("デザインの刷新により、第一印象を大幅に改善できます")

    # 上位2つに絞る
    improvement_text = "\n".join(f"  ・{imp}" for imp in improvements[:2])

    # 件名に会社名を入れる（開封率1.5倍）
    subject = f"{biz_name}様のサイトリニューアル案をお作りしました"

    demo_note = ""
    if demo_file:
        demo_note = """
■ リニューアル後のイメージ
添付ファイルをブラウザで開いてご覧ください。
貴社の情報をもとに、お試しでリニューアル案を作成しました。"""
    else:
        demo_note = """
■ リニューアル後のイメージ
貴社専用のデモサイトを無料でお作りします。"""

    body = f"""{biz_name}
ご担当者様

SAQT（サクッと）の{company.get('representative', '担当')}です。

貴社のホームページを拝見し、リニューアルのご提案を
お持ちしたくご連絡いたしました。

■ 現サイトの改善ポイント
{improvement_text}
{demo_note}

ご契約いただかない場合でも費用は一切かかりません。
打ち合わせも1回のみ、オンラインで完結します。

■ SAQTの特徴
・最短3日でリニューアル完了
・打ち合わせは1回だけ。あとは全てこちらで対応
・チャットボット導入・多言語対応もワンストップ
・補助金活用で実質負担を大幅軽減

{f"【期間限定】{campaign.get('description', '')}".strip()}

ご興味があればご都合のよい日時をお知らせください。

━━━━━━━━━━━━━━━━━━
SAQT（サクッと）
{company.get('representative', '担当')}
Web: {brand.get('domain', 'saqt-ai.com')}
Email: {company.get('email', '')}
{f"Tel: {company['phone']}" if company.get('phone') else ""}
運営: 合同会社FOMUS
━━━━━━━━━━━━━━━━━━"""

    return subject, body


def generate_followup_with_gemini(lead, config):
    """Geminiでフォローアップメールも個別生成"""
    if not GEMINI_API_KEY:
        return None
    import urllib.request

    biz_name = lead.get("name", "")
    company = config["company"]
    brand = config.get("brand", {})

    prompt = f"""あなたはSAQT（サクッと）のトップ営業担当です。

3日前に{biz_name}様にサイトリニューアルの提案メールを送りましたが、まだ返信がありません。
フォローアップメールを1通作成してください。

■ ルール:
1. しつこくない。さりげなく。「見ていただけましたか？」程度
2. 新しい情報を1つ追加する（例: キャンペーンの残り枠が少ない、別の切り口での価値提案）
3. 不要なら返信くださいと明記（誠実さを見せる）
4. 150〜200文字程度の短いメール
5. 「AI」「人工知能」は使わない
6. 押し売り感ゼロ

■ 出力フォーマット:
1行目: SUBJECT: （件名。「Re:」で始める）
2行目: 空行
3行目以降: 本文

署名:
━━━━━━━━━━━━━━━━━━
SAQT（サクッと）
{company.get('representative', '担当')}
Web: {brand.get('domain', 'saqt-ai.com')}
Email: {company.get('email', '')}
運営: 合同会社FOMUS
━━━━━━━━━━━━━━━━━━"""

    request_body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 400}
    }).encode("utf-8")

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=request_body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not text or "SUBJECT:" not in text:
            return None

        lines = text.strip().split("\n")
        subject_line = ""
        body_lines = []
        found = False
        for line in lines:
            if line.strip().startswith("SUBJECT:") and not found:
                subject_line = line.replace("SUBJECT:", "").strip()
                found = True
            elif found:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if subject_line and body:
            return subject_line, body
        return None
    except Exception:
        return None


def generate_followup_email(lead, config):
    """フォローアップメール（3日後）"""
    biz_name = lead.get("name", "")
    company = config["company"]
    brand = config.get("brand", {})

    subject = f"Re: {biz_name}様のサイトリニューアル案をお作りしました"

    body = f"""{biz_name}
ご担当者様

先日ご連絡いたしましたSAQTの{company.get('representative', '担当')}です。

その後、いかがでしょうか。
貴社のサイト改善について、具体的なデモをお見せできればと思い
改めてご連絡いたしました。

お忙しいところ恐縮ですが、
10分でもお時間をいただければ、リニューアル後の
完成イメージをお見せできます。

もしご不要でしたら、お手数ですがその旨ご返信ください。
今後のご連絡は控えさせていただきます。

━━━━━━━━━━━━━━━━━━
SAQT（サクッと）
{company.get('representative', '担当')}
Web: {brand.get('domain', 'saqt-ai.com')}
Email: {company.get('email', '')}
運営: 合同会社FOMUS
━━━━━━━━━━━━━━━━━━"""

    return subject, body


def send_email(to_addr, subject, body, config, attachment_path=None):
    """SMTPでメールを送信（ファイル添付対応）"""
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_addr = config["company"]["email"]

    if not all([smtp_host, smtp_user, smtp_pass, from_addr]):
        return False, "SMTP設定が不完全です"

    msg = MIMEMultipart()
    msg["From"] = f"SAQT <{from_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # ファイル添付
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("text", "html")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(attachment_path)
            part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
            msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "送信成功"
    except Exception as e:
        return False, str(e)


def save_email_draft(lead, subject, body, email_type="initial"):
    """メール下書きをファイルに保存"""
    os.makedirs(EMAILS_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    safe_name = lead.get("name", "unknown").replace(" ", "_")[:30]
    filename = f"{date_str}_{email_type}_{safe_name}.txt"
    filepath = os.path.join(EMAILS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"To: {lead.get('email', '要確認')}\n")
        f.write(f"Subject: {subject}\n")
        f.write(f"Type: {email_type}\n")
        f.write(f"Business: {lead.get('name', '')}\n")
        f.write(f"Phone: {lead.get('phone', '')}\n")
        f.write(f"Website: {lead.get('website', '')}\n")
        f.write(f"Priority: {lead.get('priority', '')}\n")
        f.write(f"Score: {lead.get('score', '')}\n")
        f.write("-" * 50 + "\n\n")
        f.write(body)

    return filepath


def log_sent(lead, email_type):
    """送信ログを記録"""
    os.makedirs(EMAILS_DIR, exist_ok=True)
    is_new = not os.path.exists(SENT_LOG)
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["name", "email", "type", "sent_at", "followup_due"])
        followup_due = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d") if email_type == "initial" else ""
        writer.writerow([
            lead.get("name", ""),
            lead.get("email", ""),
            email_type,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            followup_due,
        ])


def get_already_sent():
    """送信済みメールアドレス・企業名のセットを取得"""
    sent_emails = set()
    sent_names = set()
    if not os.path.exists(SENT_LOG):
        return sent_emails, sent_names
    with open(SENT_LOG, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("type") == "initial":
                if row.get("email"):
                    sent_emails.add(row["email"].strip().lower())
                if row.get("name"):
                    sent_names.add(row["name"].strip())
    return sent_emails, sent_names


def get_followup_due():
    """フォローアップが必要なリードを取得"""
    if not os.path.exists(SENT_LOG):
        return []
    today = datetime.now().strftime("%Y-%m-%d")
    due = []
    sent_followups = set()

    with open(SENT_LOG, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # フォロー済みをマーク
    for row in rows:
        if row.get("type") == "followup":
            sent_followups.add(row.get("email", ""))

    # 期限が来ている初回送信を取得
    for row in rows:
        if row.get("type") == "initial" and row.get("followup_due", "") <= today:
            if row.get("email") not in sent_followups:
                due.append(row)

    return due


def main():
    config = load_config()

    print("=" * 60)
    print("  営業メール送信 - SAQT（サクッと）")
    print("=" * 60)

    print("\n  モード選択:")
    print("  1. 初回メール送信（分析済みリードに送信）")
    print("  2. フォローアップ送信（3日経過した未返信リードに再送）")
    print("  3. 全自動（初回 + フォローアップ）")
    print("  4. 下書きのみ（送信しない）")

    mode = input("\n  選択 (1-4): ").strip()

    # API/SMTP確認
    if GEMINI_API_KEY:
        print(f"\n  ✓ Gemini API: 有効（個別メール生成モード）")
    else:
        print(f"\n  ⚠ GEMINI_API_KEY 未設定（テンプレートモードで動作）")
        print("    個別メール生成を有効にするには:")
        print("    export GEMINI_API_KEY='your-api-key'")

    smtp_available = bool(os.environ.get("SMTP_HOST"))
    if mode in ("1", "2", "3") and not smtp_available:
        print("\n  ⚠ SMTP設定がありません。下書き保存のみ実行します。")
        print("  設定方法:")
        print("    export SMTP_HOST='smtp.gmail.com'")
        print("    export SMTP_PORT='587'")
        print("    export SMTP_USER='your-email@gmail.com'")
        print("    export SMTP_PASS='your-app-password'")
        mode = "4"

    # === 初回メール ===
    if mode in ("1", "3", "4"):
        csv_files = [f for f in os.listdir(LEADS_DIR) if f.endswith("_analyzed.csv")]
        if not csv_files:
            print("\n  分析済みCSVが見つかりません。")
        else:
            print(f"\n  --- 初回メール ---")
            print("  対象CSVファイル:")
            for i, f in enumerate(csv_files, 1):
                print(f"    {i}. {f}")
            if mode == "3":
                # 全自動: 全ファイル対象
                selected_files = csv_files
            else:
                choice = input("\n  選択 (番号): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(csv_files):
                    selected_files = [csv_files[int(choice) - 1]]
                else:
                    selected_files = []

            sent_count = 0
            draft_count = 0
            skip_count = 0

            # 送信済みリストを取得（重複防止）
            already_sent_emails, already_sent_names = get_already_sent()
            if already_sent_emails:
                print(f"  （送信済み: {len(already_sent_emails)}件をスキップ対象）")

            for csv_file in selected_files:
                filepath = os.path.join(LEADS_DIR, csv_file)
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    leads = [row for row in reader if row.get("priority") in ("high", "medium")]

                for lead in leads:
                    name = lead.get("name", "不明")
                    email = lead.get("email", "")

                    # 重複チェック（メールアドレス or 企業名で判定）
                    if email and email.strip().lower() in already_sent_emails:
                        print(f"    ⏭ {name} → 送信済み（スキップ）")
                        skip_count += 1
                        continue
                    if name.strip() in already_sent_names:
                        print(f"    ⏭ {name} → 送信済み（スキップ）")
                        skip_count += 1
                        continue

                    # Gemini APIで個別メール生成（なければテンプレにフォールバック）
                    subject, body = None, None
                    if GEMINI_API_KEY:
                        print(f"    🤖 Gemini で個別メール生成中...")
                        site_text = fetch_site_content(lead.get("website", ""))
                        subject, body = generate_email_with_gemini(lead, config, site_text)
                        if subject:
                            print(f"    ✓ 個別メール生成完了: {subject[:40]}...")
                        else:
                            print(f"    ⚠ Gemini生成失敗。テンプレートにフォールバック")

                    if not subject or not body:
                        subject, body = generate_initial_email(lead, config)

                    # 下書き保存
                    draft_path = save_email_draft(lead, subject, body, "initial")
                    draft_count += 1

                    # デモファイルを探す
                    demo_path = find_demo_file(name)
                    if demo_path:
                        print(f"    📎 デモ添付: {os.path.basename(demo_path)}")

                    # 送信
                    if mode in ("1", "3") and email:
                        success, msg = send_email(email, subject, body, config, attachment_path=demo_path)
                        if success:
                            log_sent(lead, "initial")
                            sent_count += 1
                            # 送信済みセットに追加（同バッチ内の重複も防止）
                            already_sent_emails.add(email.strip().lower())
                            already_sent_names.add(name.strip())
                            print(f"    ✓ {name} → 送信完了")
                        else:
                            print(f"    ✗ {name} → {msg}")
                        time.sleep(2)  # レート制限対策
                    else:
                        print(f"    📝 {name} → 下書き保存")

            print(f"\n  初回メール: 送信{sent_count}件 / 下書き{draft_count}件 / スキップ{skip_count}件")

    # === フォローアップ ===
    if mode in ("2", "3"):
        print(f"\n  --- フォローアップ ---")
        due_leads = get_followup_due()

        if not due_leads:
            print("  フォローアップ対象なし（3日経過した未返信リードがありません）")
        else:
            print(f"  対象: {len(due_leads)}件")
            fu_sent = 0

            for row in due_leads:
                lead = {"name": row.get("name", ""), "email": row.get("email", "")}

                # フォローアップもGeminiで個別化（可能なら）
                subject, body = None, None
                if GEMINI_API_KEY:
                    fu_prompt_result = generate_followup_with_gemini(lead, config)
                    if fu_prompt_result:
                        subject, body = fu_prompt_result

                if not subject or not body:
                    subject, body = generate_followup_email(lead, config)

                save_email_draft(lead, subject, body, "followup")

                if lead["email"]:
                    success, msg = send_email(lead["email"], subject, body, config)
                    if success:
                        log_sent(lead, "followup")
                        fu_sent += 1
                        print(f"    ✓ {lead['name']} → フォローアップ送信完了")
                    else:
                        print(f"    ✗ {lead['name']} → {msg}")
                    time.sleep(2)

            print(f"\n  フォローアップ: {fu_sent}件送信")

    print(f"\n{'=' * 60}")
    print("  完了！")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
