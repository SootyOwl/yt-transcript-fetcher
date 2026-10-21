// Experimental native transport bindings observed on 2026-10-21.
// These minified names are version-dependent. This is not a supported backend.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { gunzipSync } from 'node:zlib';

let argumentsParsed;
try {
argumentsParsed = parseArgs({
  allowPositionals: true,
  options: {
    headed: { type: 'boolean', default: false },
    consent: { type: 'string', default: 'reject' },
    'private-capture': { type: 'boolean', default: false },
    help: { type: 'boolean', default: false },
  },
});
} catch {
  console.error('Invalid arguments. Use --help for usage.');
  process.exit(2);
}
const { values, positionals } = argumentsParsed;
if (values.help) {
  console.log('node research/transcript_probe.mjs [VIDEO_ID] [--headed] [--consent=reject|accept] [--private-capture]');
  process.exit(0);
}
const videoId = positionals[0] || 'dQw4w9WgXcQ';
if (positionals.length > 1 || !/^[A-Za-z0-9_-]{11}$/.test(videoId) || !['reject', 'accept'].includes(values.consent)) {
  console.error('Expected one 11-character video ID and consent=reject or accept.');
  process.exit(2);
}

// An external install can be used without adding dependencies to this package.
const playwrightModule = process.env.YT_PROBE_PLAYWRIGHT
  ? pathToFileURL(path.resolve(process.env.YT_PROBE_PLAYWRIGHT)).href : 'playwright';
const summary = {
  date: new Date().toISOString(), videoId, headed: values.headed,
  consent: values.consent, requests: [], success: false,
};
const privateDir = values['private-capture']
  ? fs.mkdtempSync(path.join(os.tmpdir(), 'yt-transcript-private-')) : null;
if (privateDir) {
  fs.chmodSync(privateDir, 0o700);
  summary.privateCaptureDirectory = privateDir;
}
const writePrivate = (name, data) => {
  if (privateDir) fs.writeFileSync(path.join(privateDir, name), JSON.stringify(data, null, 2), { mode: 0o600 });
};

function segmentsIn(value, found = []) {
  if (!value || typeof value !== 'object') return found;
  const segment = value.transcriptSegmentRenderer;
  if (segment) {
    const text = segment.snippet?.simpleText || segment.snippet?.runs?.map(run => run.text || '').join('') || '';
    const start = Number(segment.startMs), end = Number(segment.endMs);
    if (text.trim() && Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end >= start) found.push(segment);
  }
  for (const child of Object.values(value)) segmentsIn(child, found);
  return found;
}

let browser;
const captures = [];
try {
  const { chromium } = await import(playwrightModule);
  browser = await chromium.launch({
    executablePath: process.env.YT_PROBE_CHROMIUM || undefined,
    headless: !values.headed,
  });
  const context = await browser.newContext({ locale: 'en-GB' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('response', response => {
    if (new URL(response.url()).pathname !== '/youtubei/v1/get_transcript') return;
    captures.push((async () => {
      const request = response.request();
      const headers = await request.allHeaders();
      let bytes = request.postDataBuffer();
      if (bytes?.[0] === 0x1f && bytes?.[1] === 0x8b) bytes = gunzipSync(bytes);
      const body = JSON.parse(bytes.toString());
      const text = await response.text();
      let result;
      try { result = JSON.parse(text); } catch { result = null; }
      const attestation = body.context?.request?.attestationResponseData || {};
      summary.requests.push({
        status: response.status(), error: result?.error?.status || null,
        clientVersion: body.context?.client?.clientVersion,
        bodyKeys: Object.keys(body), contextKeys: Object.keys(body.context || {}),
        headerNames: Object.keys(headers), attestationKeys: Object.keys(attestation),
        webResponseLength: attestation.webResponse?.length || 0,
        externalVideoIdMatches: body.externalVideoId === videoId,
        nonemptyTimedSegments: segmentsIn(result).length,
      });
      writePrivate(`request-${summary.requests.length}.json`, {
        url: response.url(), status: response.status(), headers, request: body, response: result ?? text,
      });
    })().catch(error => ({ captureError: error.name })));
  });

  const url = `https://www.youtube.com/watch?v=${videoId}&hl=en&autoplay=0`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForFunction(() => Boolean(window.ytcfg?.data_?.INNERTUBE_CONTEXT && window.ytInitialData));
  let consentClicked = false;
  try {
    await page.getByText(values.consent === 'accept' ? 'Accept all' : 'Reject all', { exact: true }).first().click({ timeout: 7000 });
    consentClicked = true;
  } catch (error) {
    if (error.name !== 'TimeoutError') throw error;
  }
  summary.consentClicked = consentClicked;
  if (consentClicked) {
    await page.waitForTimeout(1000);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForFunction(() => Boolean(window.ytcfg?.data_?.INNERTUBE_CONTEXT && window.ytInitialData));
  }
  await page.waitForFunction(() => typeof window.default_kevlar_base?.ex === 'function');
  const native = await page.evaluate(async videoId => {
    const api = window.default_kevlar_base;
    if (!api.Hj || !api.JE) return { error: 'Native transport bindings changed' };
    const panel = window.ytInitialData.engagementPanels?.find(item =>
      item.engagementPanelSectionListRenderer?.panelIdentifier === 'engagement-panel-searchable-transcript');
    const command = structuredClone(panel?.engagementPanelSectionListRenderer?.content?.continuationItemRenderer?.continuationEndpoint);
    if (!command?.getTranscriptEndpoint?.params) return { error: 'No transcript command in watch bootstrap' };
    const player = document.querySelector('#movie_player');
    const track = player?.getOption?.('captions', 'track');
    command.getTranscriptEndpoint.externalVideoId = videoId;
    for (const key of ['languageCode', 'kind', 'name']) {
      if (track?.[key]) command.getTranscriptEndpoint[key] = track[key];
    }
    document.querySelector('video')?.pause();
    const result = await Promise.race([
      Promise.resolve(api.ex(api.Hj().resolve(api.JE), command)).then(
        value => ({ responseKeys: Object.keys(value || {}) }),
        () => ({ error: 'Native transport rejected its promise' }),
      ),
      new Promise(resolve => setTimeout(() => resolve({ error: 'Native transport timed out' }), 30000)),
    ]);
    return { clientVersion: window.ytcfg.data_.INNERTUBE_CONTEXT.client.clientVersion, ...result };
  }, videoId);
  summary.native = native;
  const settled = await Promise.allSettled(captures);
  summary.captureErrors = settled.filter(result => result.status === 'rejected' || result.value?.captureError).length;
  summary.success = !native.error && !summary.captureErrors && summary.requests.some(request =>
    request.status === 200 && !request.error && request.externalVideoIdMatches && request.nonemptyTimedSegments > 0);
  writePrivate('cookies.json', await context.cookies());
  process.exitCode = summary.success ? 0 : 1;
} catch (error) {
  // Full browser errors can embed URLs or request data. Keep diagnostics bounded.
  summary.harnessError = error.name;
  process.exitCode = 2;
} finally {
  await browser?.close();
  console.log(JSON.stringify(summary, null, 2));
}
