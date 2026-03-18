# SAQT 画像生成プロンプト（Gemini用）

すべて以下の共通指示を先頭に付けてください:
> Style: Clean, modern, professional. Minimal and sleek. Color palette: dark navy (#0f172a), orange (#f97316), white. No text overlay unless specified. High resolution, suitable for web use.

---

## 1. ヒーロー画像（最重要）

### hero-laptop.png（PC画面に表示されたモダンサイト）
```
A sleek silver laptop on a dark navy desk, screen showing a beautiful modern Japanese business website with orange accent colors. Clean minimal workspace. Dramatic lighting from the left. Shallow depth of field. Dark moody atmosphere. No text on screen should be readable. The website on screen should look professional and modern with a hero section, navigation, and cards layout. Photorealistic.
```

### hero-phone.png（スマホ画面）
```
A modern smartphone held at a slight angle, displaying a mobile-responsive Japanese website with orange (#f97316) accent buttons. Dark background. The phone has thin bezels. Clean, minimal. The website on screen shows a clean mobile layout with a navigation menu and call-to-action button. Photorealistic, product photography style.
```

---

## 2. OGP画像（SNSシェア用）1200x630px

### saqt-ogp.png
```
A wide banner image (1200x630 aspect ratio) for a web development service called "SAQT". Dark navy (#0f172a) background with a subtle grid pattern. On the left side, large bold text "SAQT" in white with "サクッと" in smaller text below in orange (#f97316). On the right side, a laptop and phone mockup showing modern websites. Minimal, professional, tech-forward aesthetic.
```

---

## 3. デモファーストセクション（3枚）

### demo-step1.png（ヒアリング）
```
A minimalist illustration of a video call interface on a laptop screen. Two people in a virtual meeting, one speaking and one listening. Clean flat design style. Orange and navy color scheme. Professional but friendly atmosphere. No faces need to be detailed - silhouette or minimal style is fine.
```

### demo-step2.png（デモ提示）
```
A laptop screen showing a website design mockup/wireframe being presented. The screen shows a before (gray, old-looking) on the left and after (colorful, modern with orange accents) on the right with an arrow between them. Clean flat illustration style. Dark navy and orange color palette.
```

### demo-step3.png（納品・GO）
```
A rocket launching upward from a laptop screen, symbolizing website launch. Minimal flat illustration style. Orange (#f97316) rocket with a trail. Dark navy background. Clean, modern, celebration feel. Confetti particles in orange and white.
```

---

## 4. サービスカード画像（8枚）

### service-01-renewal.png（リニューアル）
```
Split screen illustration: left side shows an old, gray, dated website design (table layout, small text), right side shows a modern, clean website with orange accents (responsive, card-based). An arrow transforms from old to new. Flat design style, dark navy and orange palette.
```

### service-02-chatbot.png（チャットボット）
```
A smartphone screen showing a chat interface with message bubbles. The bot messages are in orange, user messages in gray. A friendly chat bot icon (simple circle face) at the top. Clean UI design, minimal. Dark navy background behind the phone. Flat illustration style.
```

### service-03-meo.png（MEO対策）
```
A Google Maps-style interface showing a business listing card popping up from a map. The card has 5 orange stars, a business name, photos, and a "directions" button. Pin markers on the map in orange. Clean flat illustration, bird's eye view perspective.
```

### service-04-multilang.png（多言語対応）
```
A globe icon in the center surrounded by floating language labels: "日本語", "English", "中文", "한국어". Connected by thin lines to a central website icon. Clean flat illustration. Orange and navy color scheme. Minimal and modern.
```

### service-05-recruit.png（採用ページ）
```
A laptop showing a modern job recruitment page with a "Join Our Team" hero section. Next to it, icons of people/candidates with check marks, suggesting successful hiring. Clean flat illustration. Orange and navy tones. Professional and welcoming feel.
```

### service-06-server.png（サーバー管理）
```
A simple illustration of a server/cloud icon with a shield and checkmark, symbolizing secure hosting management. Transfer arrows showing migration from old server to new server. Clean flat design, orange and navy palette. Minimal and technical but approachable.
```

### service-07-photo.png（写真撮影）
```
A professional camera with a lens, next to a laptop showing a website with beautiful photography. The photos on the website are vibrant and high-quality (restaurant interior, office space). Clean flat illustration style. Orange highlight on the camera shutter button. Dark navy and orange palette.
```

### service-08-system.png（業務システム）
```
A dashboard UI design showing charts, graphs, calendar, and task lists. Clean modern SaaS-style interface with orange accent colors. Cards with metrics, a pie chart, and a line graph. Dark navy sidebar. Flat illustration style, looks like a real software interface but illustrated.
```

---

## 5. 自治体ページ用

### govt-hero.png
```
A modern Japanese city hall building (市役所) exterior, clean and bright. In the foreground, a person is browsing the city's website on their smartphone. The website on the phone screen looks modern and accessible. Daylight, clean atmosphere. Photorealistic style with a slight warm tone.
```

### govt-before-after.png
```
Split screen comparison. Left side labeled "Before": an old government website with tiny text, gray colors, fixed width layout, cluttered navigation, PDF download links everywhere. Right side labeled "After": a modern, clean government website with orange accents, large readable text, card-based layout, mobile responsive, accessibility features visible (font size toggle). Flat UI illustration style.
```

### govt-accessibility.png
```
A website accessibility toolbar illustration showing: font size increase/decrease buttons (A- A A+), high contrast toggle (black/white icon), and a language selector dropdown showing Japanese, English, Chinese, Korean. Clean flat UI design. Orange and navy color scheme. Looks like a real website toolbar component.
```

---

## 6. ロゴ・ファビコン

### saqt-logo.png
```
A minimal modern logo for "SAQT" (a web development service). The text "SAQT" in bold sans-serif font (similar to Inter Black). The "S" has a subtle orange (#f97316) gradient. Below in small text: "サクッと". Background: transparent. Clean, minimal, tech-forward. No icons, just typography.
```

### saqt-favicon.png（512x512）
```
A minimal square icon for "SAQT". Just the letter "S" in white on a rounded square background with an orange (#f97316) to deep orange (#ea580c) gradient. Bold, geometric, modern. Like an app icon. 512x512 pixels.
```

---

## 7. キャンペーンセクション

### campaign-chatbot.png
```
A festive promotional banner style illustration. A chat bubble icon with a gift bow on it, surrounded by celebration confetti. Text area left blank for overlay. Background: gradient from deep orange to bright orange. Festive but professional. Flat illustration style.
```

---

## 生成順序（優先度）

1. **saqt-favicon.png** — すぐ必要
2. **saqt-logo.png** — ブランドの顔
3. **hero-laptop.png** — ファーストインパクト
4. **hero-phone.png** — ヒーロー右側
5. **saqt-ogp.png** — SNSシェア
6. **service-01〜08** — サービスセクション
7. **demo-step1〜3** — デモファースト
8. **govt-hero.png** — 自治体ページ
9. **govt-before-after.png** — 自治体 Before/After
10. **campaign-chatbot.png** — キャンペーン

## 画像サイズ目安

| 用途 | 推奨サイズ |
|------|-----------|
| ヒーロー（PC） | 600x400px |
| ヒーロー（スマホ） | 200x360px |
| OGP | 1200x630px |
| サービスカード | 400x300px |
| デモステップ | 400x300px |
| ファビコン | 512x512px |
| ロゴ | 200x60px |
| 自治体ヒーロー | 800x500px |
