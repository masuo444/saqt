# SAQT AIチャットボット

クライアントのWebサイトに簡単に導入できるチャットボットシステムです。
クライアント自身がFAQ・ナレッジを自由に管理できます。

## クライアントへの導入手順

### 1. ファイルを配置

以下のファイルをクライアントのサーバーにアップロードします：

```
chatbot/
├── chatbot.js        （widget/chatbot.js）
├── chatbot.css       （widget/chatbot.css）
└── knowledge.json    （demo/knowledge.json をベースにカスタマイズ）
```

### 2. HTMLにスクリプトタグを追加

クライアントサイトの `</body>` の直前に以下を追加：

```html
<script src="chatbot.js" data-knowledge="knowledge.json"></script>
```

これだけで、サイト右下にチャットボタンが表示されます。

### 3. カスタマイズ（オプション）

```html
<script
    src="chatbot.js"
    data-knowledge="knowledge.json"
    data-primary-color="#e11d48"
    data-greeting="○○クリニックへようこそ！ご質問をどうぞ。"
></script>
```

| 属性 | 説明 | デフォルト |
|------|------|-----------|
| `data-knowledge` | knowledge.json のパス | `./knowledge.json` |
| `data-primary-color` | メインカラー | `#3b82f6`（青） |
| `data-greeting` | 挨拶メッセージ（JSONの設定を上書き） | JSONの設定値 |

## ナレッジ管理（クライアント用）

### 管理画面を使う場合

1. `admin/index.html` をブラウザで開く
2. Q&Aエントリを追加・編集・削除
3. 「エクスポート」ボタンで `knowledge.json` をダウンロード
4. ダウンロードしたファイルをサーバーにアップロード

### knowledge.json を直接編集する場合

```json
{
  "settings": {
    "bot_name": "サポートアシスタント",
    "greeting": "こんにちは！",
    "fallback": "申し訳ございません。お問い合わせフォームからご連絡ください。",
    "quick_replies": ["営業時間について", "料金について"]
  },
  "entries": [
    {
      "id": "1",
      "category": "基本情報",
      "keywords": ["営業時間", "何時"],
      "questions": ["営業時間を教えてください"],
      "answer": "営業時間は9:00〜18:00です。"
    }
  ]
}
```

## 運用フロー

```
SAQT が初期設定 → knowledge.json を納品
    ↓
クライアントが管理画面で Q&A を追加・編集
    ↓
エクスポート → サーバーにアップロード
    ↓
チャットボットに即反映
```
