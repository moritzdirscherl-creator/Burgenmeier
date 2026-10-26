#!/usr/bin/env node
// Schaubild (HTML vom Burgenmaler) ohne Bildschirm in Chromium abfotografieren.
//
//   node render.mjs burg_schaubild.html --out bilder/ --views vogelschau,sued,umgebung
//   node render.mjs burg_schaubild.html --out bilder/ --cam "vedute:az=230,el=14,dist=260,fov=30" --licht abend
//   node render.mjs burg_schaubild.html --out bilder/ --width 3000 --height 2000 --befund
//
// Benötigt Playwright mit Chromium (require('playwright')). Ist das CDN für three.js nicht
// erreichbar, wird eine lokale Kopie verwendet (--three oder node_modules/three).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import url from 'url';
import { execSync } from 'child_process';

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
const opt = { views: 'vogelschau,sued,umgebung', width: 2400, height: 1600, scale: 1, out: '.', licht: 'zeichnung', cams: [] };
const files = [];
for (let k = 0; k < args.length; k++) {
  const a = args[k];
  if (a === '--befund' || a === '--ohne-umgebung') opt[a.slice(2)] = true;
  else if (a === '--cam') opt.cams.push(args[++k]);
  else if (a.startsWith('--')) opt[a.slice(2)] = args[++k];
  else files.push(a);
}
if (!files.length) {
  console.error('Aufruf: node render.mjs schaubild.html [--out DIR] [--views a,b] [--cam "name:az=..,el=..,dist=..,fov=..,x=..,y=..,z=.."] [--licht morgen|mittag|abend] [--width W --height H --scale S] [--befund] [--ohne-umgebung]');
  process.exit(1);
}

function findThree() {
  const tries = [opt.three, process.env.THREE_JS];
  try { tries.push(require.resolve('three/build/three.min.js', { paths: [process.cwd(), path.dirname(files[0])] })); } catch (e) { /* fehlt */ }
  return tries.find(p => p && fs.existsSync(p));
}

function parseCam(s) {
  const [name, rest] = s.includes(':') ? s.split(/:(.*)/s) : ['ansicht', s];
  const c = { name };
  for (const kv of rest.split(',')) {
    const [k, v] = kv.split('=');
    if (v !== undefined) c[k.trim()] = parseFloat(v);
  }
  if (c.x != null && c.y != null) c.target = [c.x, c.y, c.z];
  return c;
}

function loadPlaywright() {
  const roots = [process.cwd()];
  try { roots.push(execSync('npm root -g', { encoding: 'utf8' }).trim()); } catch (e) { /* kein npm */ }
  for (const r of roots) {
    try { return require(require.resolve('playwright', { paths: [r] })); } catch (e) { /* weiter */ }
  }
  console.error('Playwright fehlt: npm i -g playwright (Chromium wird mitgebracht oder ist vorinstalliert).');
  process.exit(2);
}
const { chromium } = loadPlaywright();
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const W = parseInt(opt.width, 10), H = parseInt(opt.height, 10), scale = parseFloat(opt.scale);
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
page.on('pageerror', e => console.error('Seitenfehler:', e.message));
const local = findThree();
await page.route(/three(\.min)?\.js$/, async route => {
  try {
    const r = await route.fetch({ timeout: 8000 });
    if (r.ok()) return route.fulfill({ response: r });
  } catch (e) { /* offline */ }
  if (!local) return route.abort();
  route.fulfill({ status: 200, contentType: 'application/javascript', body: fs.readFileSync(local) });
});
fs.mkdirSync(opt.out, { recursive: true });
const src = files[0];
await page.goto(url.pathToFileURL(path.resolve(src)).href + '?clean=1&licht=' + encodeURIComponent(opt.licht));
await page.waitForFunction(() => window.__burgenmaler && window.__burgenmaler.ready, null, { timeout: 300000 });
await page.evaluate(o => {
  const B = window.__burgenmaler;
  if (o.befund) B.setBefund(true);
  if (o['ohne-umgebung']) B.setEnv(false);
}, opt);

const stem = path.basename(src).replace(/\.html?$/, '');
const shots = opt.views.split(',').filter(Boolean).map(v => ({ name: v, view: v })).concat(opt.cams.map(parseCam));
for (const s of shots) {
  const t0 = Date.now();
  const data = await page.evaluate(s => {
    const B = window.__burgenmaler;
    if (s.view) B.setView(s.view); else B.setCamera(s);
    return B.snapshot();
  }, s);
  const file = path.join(opt.out, `${stem}_${s.name}.png`);
  fs.writeFileSync(file, Buffer.from(data.split(',')[1], 'base64'));
  console.log(file, `(${((Date.now() - t0) / 1000).toFixed(1)} s)`);
}
await browser.close();
