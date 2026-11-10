// 南海+ 全景状态台 · 共享声明接口
// GET  /api/claims          → 所有共享声明（JSON 数组，按提交时间排序）
// POST /api/claims          → 提交声明（body: JSONL 或 JSON 数组），需要 header x-panorama-key
// 声明永远是待核验：服务器强制 accepted:false，不允许自填 verified；正式状态只来自板采认快照。
import { put, list } from '@vercel/blob';

const ORIGINS = (process.env.ALLOWED_ORIGINS || 'https://a2hlab.github.io').split(',');
const TYPES = ['observation','wall','task','fix','verification','decision','knowledge','claim','device'];
const ID_RE = /^(m(0[1-9]|10)|hub|b\d{2})-[a-z]+[a-z0-9]*-\d{8}-\d{4,}$/;
const BAD = new Set(['__proto__','constructor','prototype']);
const MAX_BODY = 256 * 1024, MAX_ITEMS = 200;

function cors(req, res) {
  const o = req.headers.origin;
  if (o && (ORIGINS.includes(o) || o.startsWith('http://localhost') || o === 'null')) res.setHeader('Access-Control-Allow-Origin', o);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type,x-panorama-key');
}

function check(e, i) {
  const at = `第 ${i} 行`;
  if (!e || typeof e !== 'object' || Array.isArray(e)) return `${at}：不是 JSON 对象`;
  for (const k of Object.keys(e)) if (BAD.has(k)) return `${at}：不允许的键 ${k}`;
  if (typeof e.id !== 'string' || !ID_RE.test(e.id)) return `${at}：id 应为 <单元>-<角色>-<日期>-<序号>`;
  if (!TYPES.includes(e.type)) return `${at}：type 不合法`;
  if (typeof e.actor !== 'string' || !e.actor.trim()) return `${at}：缺少 actor`;
  if (e.status === 'verified') return `${at}：verified 只能由板采认快照产生`;
  return null;
}

async function readBody(req) {
  if (req.body !== undefined) return typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
  let s = ''; for await (const c of req) { s += c; if (s.length > MAX_BODY) break; } return s;
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') {
    const out = []; let cursor;
    do {
      const r = await list({ prefix: 'claims/', cursor, limit: 1000 });
      for (const b of r.blobs) out.push(b);
      cursor = r.hasMore ? r.cursor : undefined;
    } while (cursor);
    const docs = await Promise.all(out.map(b => fetch(b.url).then(x => x.json()).catch(() => null)));
    const claims = docs.filter(Boolean).sort((a, b) => String(a.submitted_at).localeCompare(String(b.submitted_at)));
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json(claims);
  }
  if (req.method !== 'POST') return res.status(405).json({ error: 'method' });
  if (!process.env.PANORAMA_WRITE_KEY || req.headers['x-panorama-key'] !== process.env.PANORAMA_WRITE_KEY)
    return res.status(401).json({ error: '提交口令不对' });
  const raw = await readBody(req);
  if (raw.length > MAX_BODY) return res.status(413).json({ error: '太大' });
  let items;
  try { const t = raw.trim(); items = t.startsWith('[') ? JSON.parse(t) : t.split('\n').filter(l => l.trim()).map(l => JSON.parse(l)); }
  catch { return res.status(400).json({ error: '不是合法的 JSON / JSONL' }); }
  if (!Array.isArray(items) || !items.length || items.length > MAX_ITEMS) return res.status(400).json({ error: `每次 1–${MAX_ITEMS} 条` });
  const errs = items.map((e, i) => check(e, i + 1)).filter(Boolean);
  if (errs.length) return res.status(400).json({ error: '校验失败', details: errs });
  const now = new Date().toISOString(), saved = [], dup = [];
  for (const e of items) {
    const o = {}; for (const k of Object.keys(e)) if (!BAD.has(k)) o[k] = e[k];
    o.accepted = false; o.review = '待核验'; o.submitted_at = now;
    try { await put(`claims/${e.id}.json`, JSON.stringify(o), { access: 'public', addRandomSuffix: false, allowOverwrite: false, contentType: 'application/json' }); saved.push(e.id); }
    catch (err) { dup.push(e.id); }
  }
  return res.status(200).json({ saved, duplicate: dup });
}
