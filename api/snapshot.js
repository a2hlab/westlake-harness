// 南海+ 全景状态台 · hub 采集器快照
// POST /api/snapshot?env=prod|rehearsal   hub 采集器推送（需要 x-panorama-key），整份覆盖
// GET  /api/snapshot?env=prod|rehearsal   状态台读取（公开）；集群页、任务页只读这份快照
import { put, list } from '@vercel/blob';

const ORIGINS = (process.env.ALLOWED_ORIGINS || 'https://a2hlab.github.io').split(',');
const ENV_RE = /^[a-z0-9-]{1,32}$/;
const MAX = 2 * 1024 * 1024;

function cors(req, res) {
  const o = req.headers.origin;
  if (o && (ORIGINS.includes(o) || o.startsWith('http://localhost') || o === 'null')) res.setHeader('Access-Control-Allow-Origin', o);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type,x-panorama-key');
}

async function readBody(req) {
  if (req.body !== undefined) return typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
  let s = ''; for await (const c of req) { s += c; if (s.length > MAX) break; } return s;
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  const env = String(req.query.env || 'prod');
  if (!ENV_RE.test(env)) return res.status(400).json({ error: 'env 不合法' });
  const path = `snapshots/${env}.json`;
  if (req.method === 'GET') {
    const r = await list({ prefix: path, limit: 1 });
    res.setHeader('Cache-Control', 'no-store');
    if (!r.blobs.length) return res.status(404).json({ error: '还没有快照', env });
    const data = await fetch(r.blobs[0].url + '?t=' + Date.now(), { cache: 'no-store' }).then(x => x.text());
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.status(200).send(data);
  }
  if (req.method !== 'POST') return res.status(405).json({ error: 'method' });
  if (!process.env.PANORAMA_WRITE_KEY || req.headers['x-panorama-key'] !== process.env.PANORAMA_WRITE_KEY)
    return res.status(401).json({ error: '提交口令不对' });
  const raw = await readBody(req);
  if (raw.length > MAX) return res.status(413).json({ error: '太大' });
  let snap; try { snap = JSON.parse(raw); } catch { return res.status(400).json({ error: '不是 JSON' }); }
  if (!snap || !Array.isArray(snap.units) || !Array.isArray(snap.devices)) return res.status(400).json({ error: '缺少 units / devices' });
  snap.received_at = new Date().toISOString();
  await put(path, JSON.stringify(snap), { access: 'public', addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json', cacheControlMaxAge: 0 });
  return res.status(200).json({ ok: true, env, units: snap.units.length, devices: snap.devices.length, tasks: (snap.tasks || []).length });
}
