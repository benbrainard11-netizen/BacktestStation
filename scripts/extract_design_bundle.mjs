// Extracts a Claude Artifacts "__bundler" HTML to a folder of source files.
// Usage: node extract_design_bundle.mjs <input.html> <out_dir>

import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const [, , inPath, outDir] = process.argv;
if (!inPath || !outDir) {
  console.error('usage: node extract_design_bundle.mjs <input.html> <out_dir>');
  process.exit(1);
}

const html = fs.readFileSync(inPath, 'utf8');

function extractScript(type) {
  const re = new RegExp(`<script[^>]+type=["']${type}["'][^>]*>([\\s\\S]*?)<\\/script>`);
  const m = html.match(re);
  if (!m) throw new Error(`missing <script type="${type}">`);
  return m[1];
}

const manifest = JSON.parse(extractScript('__bundler/manifest'));
const template = JSON.parse(extractScript('__bundler/template'));

fs.mkdirSync(outDir, { recursive: true });

const uuidToPath = {};
for (const [uuid, entry] of Object.entries(manifest)) {
  uuidToPath[uuid] = entry.path || uuid;
}

let written = 0;
for (const [uuid, entry] of Object.entries(manifest)) {
  const buf = Buffer.from(entry.data, 'base64');
  const bytes = entry.compressed ? zlib.gunzipSync(buf) : buf;
  const rel = entry.path || uuid;
  const dst = path.join(outDir, rel);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.writeFileSync(dst, bytes);
  written++;
}

fs.writeFileSync(path.join(outDir, '__template.html.json'), JSON.stringify(template, null, 2));
fs.writeFileSync(
  path.join(outDir, '__manifest_index.json'),
  JSON.stringify(
    Object.fromEntries(
      Object.entries(manifest).map(([uuid, e]) => [uuid, { path: e.path, compressed: !!e.compressed, size: e.data.length }]),
    ),
    null,
    2,
  ),
);

console.log(`wrote ${written} files to ${outDir}`);
console.log(`template type: ${typeof template}, keys: ${typeof template === 'object' ? Object.keys(template).slice(0, 10).join(',') : 'n/a'}`);
