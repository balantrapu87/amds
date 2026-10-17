#!/usr/bin/env node
/**
 * Ingests, sanitizes, and caches SVG vector assets for Remotion/GSAP runtime.
 * Implements XXE prevention, script stripping, and SVGO optimization while preserving IDs.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { optimize } from 'svgo';
import svgoConfig from '../svgo.config.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const RAW_DIR = path.resolve(__dirname, '../../assets/raw-svgs');
const DEST_DIR = path.resolve(__dirname, '../public/assets/svg');
const MANIFEST_FILE = path.resolve(__dirname, '../src/generated/svg-manifest.json');

// Ensure target directories exist
fs.mkdirSync(RAW_DIR, { recursive: true });
fs.mkdirSync(DEST_DIR, { recursive: true });
fs.mkdirSync(path.dirname(MANIFEST_FILE), { recursive: true });

function validateSecurity(svgContent, filename) {
  // Guard against Script tags, inline javascript:, and event handlers
  const scriptRegex = /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi;
  const jsUriRegex = /javascript:/gi;
  const eventHandlerRegex = /\son[a-zA-Z]+\s*=/gi;
  const xxeEntityRegex = /<!ENTITY\b/gi;
  const xxeDocTypeRegex = /<!DOCTYPE\b[^>]*\[/gi;

  if (scriptRegex.test(svgContent)) {
    throw new Error(`Security validation failed: <script> tag detected in ${filename}`);
  }
  if (jsUriRegex.test(svgContent)) {
    throw new Error(`Security validation failed: javascript: URI detected in ${filename}`);
  }
  if (eventHandlerRegex.test(svgContent)) {
    throw new Error(`Security validation failed: inline event handler detected in ${filename}`);
  }
  if (xxeEntityRegex.test(svgContent) || xxeDocTypeRegex.test(svgContent)) {
    throw new Error(`Security validation failed: XXE Entity/DOCTYPE definition detected in ${filename}`);
  }
}

async function ingest() {
  console.log(`[SVG Ingestion] Scanning ${RAW_DIR} ...`);
  const files = fs.readdirSync(RAW_DIR).filter((f) => f.endsWith('.svg'));

  if (files.length === 0) {
    console.log('[SVG Ingestion] No raw SVG files found in raw directory. Generating sample asset...');
    const sampleSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="500" height="500">
      <defs>
        <linearGradient id="gradient-accent" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#6366F1" />
          <stop offset="100%" stop-color="#06B6D4" />
        </linearGradient>
      </defs>
      <rect id="layer-backdrop" width="500" height="500" rx="32" fill="#1E293B" />
      <circle id="layer-circle" cx="250" cy="250" r="140" fill="none" stroke="url(#gradient-accent)" stroke-width="12" />
      <polygon id="layer-poly" points="250,150 330,310 170,310" fill="#8B5CF6" opacity="0.85" />
    </svg>`;
    fs.writeFileSync(path.join(RAW_DIR, 'sample-geometry.svg'), sampleSvg, 'utf-8');
    files.push('sample-geometry.svg');
  }

  const manifest = {};

  for (const file of files) {
    const rawPath = path.join(RAW_DIR, file);
    const destPath = path.join(DEST_DIR, file);
    const content = fs.readFileSync(rawPath, 'utf-8');

    try {
      validateSecurity(content, file);
      const result = optimize(content, {
        path: rawPath,
        ...svgoConfig,
      });

      fs.writeFileSync(destPath, result.data, 'utf-8');
      const assetKey = path.basename(file, '.svg');
      manifest[assetKey] = {
        name: file,
        path: `assets/svg/${file}`,
        size: Buffer.byteLength(result.data, 'utf-8'),
      };
      console.log(`✓ Ingested & sanitized: ${file} (${manifest[assetKey].size} bytes)`);
    } catch (err) {
      console.error(`✗ Failed processing ${file}: ${err.message}`);
    }
  }

  fs.writeFileSync(MANIFEST_FILE, JSON.stringify(manifest, null, 2), 'utf-8');
  console.log(`[SVG Ingestion] Manifest written to ${MANIFEST_FILE}`);
}

ingest().catch((err) => {
  console.error('[SVG Ingestion] Fatal error:', err);
  process.exit(1);
});
