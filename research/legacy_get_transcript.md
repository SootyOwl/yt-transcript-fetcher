# Legacy get_transcript investigation

These are the negative controls from before the regular-browser capture
identified the working `get_panel` route. The current result and prototype are
documented in [README.md](README.md). The unsuccessful legacy requests below
do not imply that a browser helper or attestation is needed for the modern route.

The first acceptance criterion is an HTTP 200 response from `get_transcript`
containing nonempty, timed transcript segments. As of the 2026-10-21 local
experiments, that criterion has **not passed**. Caption URL retrieval works in
the same environment, but it does not address the origin-dependent rate
limiting that made the Discord bot unusable.

## Confirmed findings

The live WEB client `2.20261020.01.00` issued exactly the same `params` bytes as
`generate_params("dQw4w9WgXcQ", "en", False)`. This is evidence for one manual
English track, not a complete schema validation across all tracks. The decoded
wire fields are:

| Outer field | Wire type | Observed value |
| --- | --- | --- |
| 1 | Length-delimited | Video ID |
| 2 | Length-delimited | URL-escaped base64 of the nested track selector |
| 3 | Varint | 1 |
| 5 | Length-delimited | `engagement-panel-searchable-transcript-search-panel` |
| 6, 7, 8 | Varint | 1 each |

The nested selector has field 1 empty for this manual track, field 2 `en`, and
field 3 empty. The semantic names of the integer flags remain unverified.

The current website adds a separate request layer around those parameters:

```text
watch bootstrap supplies context, session and transcript command
    -> initial or /att/get BotGuard challenge
    -> execute challenge with transcript engagement and video binding
    -> context.request.attestationResponseData = {challenge, webResponse}
    -> POST get_transcript with params and externalVideoId
```

BotGuard is YouTube's browser attestation mechanism. In the inspected website
code, the snapshot binding is `{c: challenge,
e: "ENGAGEMENT_TYPE_VIDEO_TRANSCRIPT_REQUEST", encryptedVideoId: videoId}`.
The challenge-fetch engagement is `ENGAGEMENT_TYPE_UNBOUND`; that is distinct
from the transcript engagement in the snapshot. This is a raw attestation
response, not simply a media playback PO token. The command handler also
copies `languageCode`, `kind`, and `name` from the player's selected caption
track when present.

The package currently omits this attestation and the top-level `externalVideoId`.
However, adding those fields has not been sufficient in these experiments.
The [YouTube.js maintainer's explanation](https://github.com/LuanRT/YouTube.js/issues/1102#issuecomment-3674268458)
independently identifies the challenge requirement, and
[BgUtils](https://github.com/LuanRT/BgUtils) provides a JavaScript challenge runner.

## Live experiment results

| Experiment | Observed result |
| --- | --- |
| Existing Android 19.09.37 package | `player` and `get_transcript` fail with 400 `FAILED_PRECONDITION` |
| Android 20.10.38 client version update | `player` works; `get_transcript` still fails |
| Transcript requests using Android 21.26.364, iOS 19.09.3 and 21.26.4, Android VR 1.65.10, visionOS 1.02 | All return 400 `FAILED_PRECONDITION` |
| WEB with canonical server-issued parameters and `externalVideoId` | 400 `FAILED_PRECONDITION` |
| Node, JSDOM and BgUtils with transcript-bound snapshot | Snapshot generated; transcript still returns 400 |
| Chromium with manually initialized challenge VM | Snapshot generated; transcript still returns 400 |
| Chromium using YouTube's native attestation service | Snapshot generated; transcript still returns 400 |
| Chromium using YouTube's complete native transport | Native context, headers, gzip body and attestation supplied; transcript still returns 400 |
| Native transport after accepting cookies and reloading | Normal `x-goog-visitor-id` replaces pre-consent `x-goog-eom-visitor-id`; transcript still returns 400 |

These were bounded functionality probes, not a throughput test. The attestation
experiments used a fresh, signed-out browser and `dQw4w9WgXcQ`. No successful
attested request has yet established which fields the server requires or what
it accepts. In particular, a generated `webResponse` does not prove successful
attestation. The server returns only a generic precondition error.

The negative native-transport control makes a browser/session/network acceptance
problem a credible hypothesis. It does **not** identify headless detection, IP
reputation, consent, or authentication as the cause. A successful regular-browser
request is the most useful next control. Independent
[Kaset experiments](https://github.com/sozercan/kaset/blob/main/docs/api-discovery.md)
also report failed guest and signed-in exact-parameter replays; signing in alone
should not be assumed to solve this.

## Helper tradeoffs

| Approach | Benefit | Cost and current evidence |
| --- | --- | --- |
| Python with updated client/parameters | Smallest operational footprint | Restores player discovery in a tested profile; no working transcript request |
| Small Node helper running BotGuard | Could retain Python API and avoid a browser per request | DOM/runtime fidelity, challenge lifecycle and session binding need maintenance; current prototype fails |
| Browser helper using native transport | Lets YouTube construct its own context and attestation | Browser memory/startup and session management; tested headless control also fails |
| Persistent browser bootstrap with Python requests | Could amortize browser cost if replay works | Token lifetime, reuse and same-session/IP requirements are unknown; requires a successful baseline before testing |

The next useful experiment is to compare an accepted regular-browser request
with the rejected native-browser request, then change one layer at a time:
same-browser replay, fresh attestation in that session, and finally transport
outside the browser. Only after repeated transcript success should a bounded
test on the Discord bot's actual host measure request volume, cooldown and
session longevity. Rate limits may apply to either endpoint.

## Reproduce the browser probe

The isolated probe invokes the native website transport, captures its transcript
request, and reports status, attestation presence and nonempty timed segment
count. It exits 0 only on a qualifying success, 1 on a failed probe, and 2 on a
harness error. It creates a fresh guest context; it does not load an existing
browser profile. The native minified bindings are specific to the inspected
website build and may need updating after a YouTube release.

```bash
npm install --prefix research --ignore-scripts --no-audit --no-fund
research/node_modules/.bin/playwright install chromium
node research/transcript_probe.mjs dQw4w9WgXcQ
node research/transcript_probe.mjs dQw4w9WgXcQ --headed --consent=accept
```

Use `YT_PROBE_CHROMIUM=/absolute/path/to/chrome` to select an existing Chromium.
Use `YT_PROBE_PLAYWRIGHT=/absolute/path/to/playwright/index.mjs` to use an
external Playwright installation. `--headed` requires a graphical session.
`--private-capture` saves raw requests, responses and guest cookies in a new
owner-only directory under the system temporary directory. Without that option,
the probe emits only a redacted JSON summary. Keep raw captures local.

The durable observations and source fingerprint are in `observations.json`.
Run `PYTHONPATH=. .venv/bin/python research/check_params.py` to compare the
frozen website parameter fixture with the package's encoder, without network
access. No production package code or dependencies are changed by this research.
