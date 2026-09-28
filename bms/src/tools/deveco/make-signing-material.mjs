#!/usr/bin/env node
/**
 * make-signing-material.mjs — generate DevEco-style encrypted signing material
 * for headless/CLI hvigor builds (task #30).
 *
 * DevEco Studio's "auto-sign" never stores keystore passwords in plaintext:
 * build-profile.json5 holds AES-128-GCM ciphertexts (hex), and the keys are
 * derived from a `material/` directory next to the keystore:
 *
 *   <keystoreDir>/material/
 *     fd/<a>/<file>  fd/<b>/<file>  fd/<c>/<file>   # 3 x 16-byte components
 *     ac/<file>                                     # PBKDF2 salt
 *     ce/<file>                                     # work key, encrypted with root key
 *
 *   rootKey = PBKDF2( Buffer(xor(fd0,fd1,fd2,COMPONENT)).toString('utf8'),
 *                     salt=ac, 10000 iters, 16 bytes, sha256 )
 *   blob(key, plain) = [int32BE(ctLen+16)][iv][ciphertext][16-byte GCM tag]
 *   ce      = blob(rootKey, workKey)
 *   password hex in build-profile.json5 = blob(workKey, password).toString('hex')
 *
 * This mirrors DevEco's DecipherUtil so hvigor SignHap can decrypt it.
 *
 * Usage:
 *   node make-signing-material.mjs --dir <keystoreDir> --password <pwd> [--key-password <pwd>]
 * Prints JSON: { "storePassword": "<hex>", "keyPassword": "<hex>" }
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

// Constant copied from DevEco hvigor-ohos-plugin DecipherUtil.component
const COMPONENT = new Int8Array([49, 243, 9, 115, 214, 175, 91, 184, 211, 190, 177, 88, 101, 131, 192, 119]);

function blob(key, plain) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-128-gcm', Buffer.from(key), iv);
  const ct = Buffer.concat([cipher.update(Buffer.from(plain)), cipher.final()]);
  const tag = cipher.getAuthTag();
  const head = Buffer.alloc(4);
  head.writeInt32BE(ct.length + 16, 0);
  return Buffer.concat([head, iv, ct, tag]);
}

function xorAll(arrays) {
  const len = arrays[0].length;
  const out = Buffer.alloc(len);
  for (const a of arrays) {
    if (a.length !== len) throw new Error('component length mismatch');
    for (let i = 0; i < len; i++) out[i] ^= a[i];
  }
  return out;
}

function writeOneFileDir(parent, name, data) {
  const dir = path.join(parent, name);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'data.bin'), data);
}

function main() {
  const args = process.argv.slice(2);
  const opt = {};
  for (let i = 0; i < args.length; i += 2) opt[args[i].replace(/^--/, '')] = args[i + 1];
  if (!opt.dir || !opt.password) {
    console.error('usage: node make-signing-material.mjs --dir <keystoreDir> --password <pwd> [--key-password <pwd>]');
    process.exit(1);
  }
  const keyPassword = opt['key-password'] ?? opt.password;

  const fd = [crypto.randomBytes(16), crypto.randomBytes(16), crypto.randomBytes(16)];
  const salt = crypto.randomBytes(16);
  const workKey = crypto.randomBytes(16);

  const xored = xorAll([...fd, Buffer.from(COMPONENT)]);
  const rootKey = new Int8Array(crypto.pbkdf2Sync(xored.toString('utf8'), salt, 10000, 16, 'sha256'));

  const materialDir = path.join(opt.dir, 'material');
  fs.rmSync(materialDir, { recursive: true, force: true });
  // fd: three sub-directories, each holding one 16-byte component file
  writeOneFileDir(path.join(materialDir, 'fd'), 'c1', fd[0]);
  writeOneFileDir(path.join(materialDir, 'fd'), 'c2', fd[1]);
  writeOneFileDir(path.join(materialDir, 'fd'), 'c3', fd[2]);
  // ac / ce: a single file directly inside the directory
  fs.mkdirSync(path.join(materialDir, 'ac'), { recursive: true });
  fs.writeFileSync(path.join(materialDir, 'ac', 'salt.bin'), salt);
  fs.mkdirSync(path.join(materialDir, 'ce'), { recursive: true });
  fs.writeFileSync(path.join(materialDir, 'ce', 'work.bin'), blob(rootKey, workKey));

  console.log(JSON.stringify({
    storePassword: blob(workKey, Buffer.from(opt.password, 'utf8')).toString('hex'),
    keyPassword: blob(workKey, Buffer.from(keyPassword, 'utf8')).toString('hex'),
  }, null, 2));
}

main();
