# SAQT（サクッと）- 営業自動化システム

運営: 合同会社FOMUS

## セットアップ

### 必要環境
- Python 3.8以上（macOSにプリインストール済み）
- ブラウザ（デモサイト確認用）

### オプション設定

#### Google Maps API（リード自動収集に必要）
```bash
export GOOGLE_MAPS_API_KEY='your-api-key'
```
※ APIキーなしでも手動CSV入力で動作します

#### SMTP設定（メール自動送信に必要）
```bash
export SMTP_HOST='smtp.gmail.com'
export SMTP_PORT='587'
export SMTP_USER='your-email@gmail.com'
export SMTP_PASS='your-app-password'
```

## 使い方

### メインランチャーから実行
```bash
cd ~/Desktop/web制作
python3 run.py
```

### 個別スクリプト実行
```bash
python3 scripts/01_collect_leads.py    # リード収集
python3 scripts/02_analyze_sites.py    # サイト診断
python3 scripts/03_generate_demo.py    # デモサイト生成
python3 scripts/04_send_outreach.py    # 営業メール作成
python3 scripts/05_pipeline.py         # パイプライン管理
```

## ワークフロー

```
Step 1: リード収集
  Google Maps → CSV（名前・住所・URL・電話番号）
  対応業種: 美容クリニック, 歯科, 飲食, 美容室, 不動産, 士業, ジム 他
  ↓
Step 2: サイト診断
  CSV → サイトスコアリング → 優先度判定
  ↓
Step 3: デモサイト生成
  高優先度リード → テンプレート + 情報 → HTML/CSS
  ↓
Step 4: 営業メール
  パーソナライズメール → 下書き保存 or 送信
  キャンペーン訴求: 4月末まで AIチャットボット無料導入
  ↓
Step 5: パイプライン管理
  案件追跡 → ステージ更新 → 受注管理
```

## ディレクトリ構成

```
web制作/
├── run.py                    # メインランチャー
├── SETUP.md                  # このファイル
├── config/
│   └── settings.json         # 設定（ターゲット業界・エリア・料金プラン）
├── scripts/
│   ├── 01_collect_leads.py   # リード収集
│   ├── 02_analyze_sites.py   # サイト診断
│   ├── 03_generate_demo.py   # デモサイト生成
│   ├── 04_send_outreach.py   # 営業メール作成
│   └── 05_pipeline.py        # パイプライン管理
├── fomus-hp/                 # SAQT サービスHP
│   ├── index.html
│   └── style.css
├── chatbot/                  # AIチャットボットシステム
│   ├── widget/               # 埋め込みウィジェット
│   │   ├── chatbot.js
│   │   └── chatbot.css
│   ├── admin/                # クライアント管理画面
│   │   ├── index.html
│   │   └── style.css
│   └── demo/                 # デモ用ナレッジベース
│       └── knowledge.json
├── templates/                # 業種別テンプレート
│   ├── beauty-clinic/
│   ├── dental/
│   └── （今後追加: restaurant, salon, realestate...）
└── output/
    ├── leads/                # 収集したリード（CSV）
    ├── demos/                # 生成したデモサイト
    ├── emails/               # 営業メール下書き
    └── pipeline.csv          # 案件管理
```

## 料金プラン（成果ベース）

| プラン | 価格 | 内容 |
|--------|------|------|
| スタンダード | 50万円〜 | HP制作 + SEO + 集客導線設計 |
| プロ | 100万円〜 | + AIチャットボット + 予約自動化 |
| フルサポート | 150万円〜 | + MEO + SNS + 月次改善 |

月額保守: 3万〜10万円/月
システム開発: 別途見積もり

## 月100万円達成ロードマップ

### Phase 1: 検証（1-2週目）
- [ ] 全業種からリードを10件収集
- [ ] デモサイトを5件作成
- [ ] 営業メールを5件送信（キャンペーン訴求）
- [ ] 目標: 1件面談獲得

### Phase 2: 最適化（3-4週目）
- [ ] 反応率の高いメール文面を特定
- [ ] デモサイトのクオリティ向上
- [ ] Google Maps API導入で収集自動化
- [ ] 目標: 2件受注（プロプラン以上）

### Phase 3: スケール（2ヶ月目〜）
- [ ] 日次30件の営業メール送信
- [ ] 面談→受注のトークスクリプト完成（成果ベース提案）
- [ ] 保守月額契約の積み上げ開始
- [ ] 業種別テンプレート追加
- [ ] 目標: 月100万円達成
