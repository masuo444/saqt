const { readFileSync } = require('fs');
const { join } = require('path');

const ALLOWED_ORIGINS = [
  'https://web.kanade-ai.com',
  'https://saqt.vercel.app',
];

function buildSystemPrompt(knowledge) {
  const knowledgeText = knowledge.map(e =>
    `【${e.category || ''}】\nQ: ${(e.questions || []).join(' / ')}\nA: ${e.answer}`
  ).join('\n\n');

  return `あなたは「KANADE WEB」のWebサイトに設置されたサポートチャットボットです。KANADE WEBの営業担当として、お客様が「相談してみよう」「デモを見てみよう」と感じるよう自然に誘導してください。

【絶対ルール】
- 丁寧だが簡潔に（200文字以内）
- ナレッジベースの情報のみ使用する。ない情報は推測せず「詳しくはご相談ください（contact@kanade-ai.com）」と案内する
- 「AI」「人工知能」という言葉は使わない
- 下手に出ない。プロフェッショナルで自信あるトーンで

【営業スタンス】
- 回答の末尾に、自然な流れで「無料相談」への誘導を1文添える（デモという言葉は使わない）
- ユーザーが「人手不足」「24時間対応」「自動化」に言及したら、KANADE AIのチャットボット（月額制オプション）を自然に紹介する
- 「サイトを作る＋KANADE AIで24時間自動運用」という組み合わせを、押し売りにならない範囲で提案する
- 補助金の話題が出たら、コスト負担が大幅に下がる点を強調する
- 競合他社の悪口は言わない。KANADE WEBの強み（速さ・コスト・ワンストップ）で差別化する

【KANADE AIとは】
サイトに設置する24時間対応の自動応答サービス。月額制。KANADE WEBのどのプランにも追加可能。深夜・休日の問い合わせ取りこぼし防止、スタッフの受付負担削減に効果的。

ナレッジベース:
${knowledgeText}`;
}

module.exports = async function handler(req, res) {
  const origin = req.headers.origin || '';
  if (ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { message, history } = req.body || {};

  if (!message || typeof message !== 'string' || message.trim().length === 0) {
    return res.status(400).json({ error: 'Invalid message' });
  }

  const safeMessage = message.slice(0, 500);

  const safeHistory = (Array.isArray(history) ? history : [])
    .slice(-10)
    .filter(m => (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
    .map(m => ({ role: m.role, content: m.content.slice(0, 500) }));

  let knowledge = [];
  try {
    const data = JSON.parse(readFileSync(join(process.cwd(), 'knowledge.json'), 'utf-8'));
    knowledge = data.entries || [];
  } catch (_) {}

  // Gemini API形式に変換（user/model、parts配列）
  const geminiHistory = safeHistory.map(m => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: m.content }],
  }));

  geminiHistory.push({
    role: 'user',
    parts: [{ text: safeMessage }],
  });

  const systemPrompt = buildSystemPrompt(knowledge);
  const apiKey = process.env.GEMINI_API_KEY;

  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_instruction: { parts: [{ text: systemPrompt }] },
          contents: geminiHistory,
          generationConfig: {
            maxOutputTokens: 300,
            temperature: 0.3,
          },
        }),
      }
    );

    if (!response.ok) return res.status(502).json({ error: 'AI unavailable' });

    const data = await response.json();
    const reply = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
    return res.status(200).json({ reply });
  } catch (_) {
    return res.status(500).json({ error: 'Server error' });
  }
};
