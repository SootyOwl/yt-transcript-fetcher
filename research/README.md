# Modern transcript protobuf investigation

**A pure Python request to the current transcript panel works.** On 2026-10-21,
`POST /youtubei/v1/get_panel` returned HTTP 200 with nonempty, timed transcripts
on four public videos. It used generated protobuf parameters, a minimal WEB
context, and no cookies, attestation, browser bootstrap, or caption URL fetch.
The production backend now uses this route through the existing public API.
The scripts in this directory remain isolated research tools.

## Protocol change

The user's regular-browser HAR revealed `panelId` equal to
`PAmodern_transcript_view`. Its request contained `context`, `panelId`, and
`params`, without `attestationResponseData`. A fresh Python request reproduced
the result without reusing the captured session or credentials.

The downloaded watch bootstrap independently contains the same parameters in
the description's Show transcript command, under
`showEngagementPanelEndpoint.globalConfiguration.params`. An older
`getTranscriptEndpoint` command also remains in that bootstrap. Following only
that older command led to the failing legacy route. The website source gates
the new panel with `web_video_companion_modern_transcript`.

The new `params` value is URL-escaped base64 of this protobuf structure. Field
names below describe observed behavior; they are not an official schema:

```protobuf
message PanelParams {
  ModernTranscriptParams transcript = 149;
}
message ModernTranscriptParams {
  string video_id = 1;
  int32 mode = 3;       // observed value 2; other enum values unverified
  string track_id = 6;  // optional caption vssId, e.g. .en, a.en, .ja
}
```

The browser request used only fields 1 and 3 inside field 149. The server's
search continuation supplied field 6, revealing the selected track. Explicit
`.en`, `a.en`, and `.ja` requests then returned distinct transcripts. Preserve
caption `vssId` values from discovery when integrating; language codes alone
do not identify every possible track.

A minimal successful request was:

```json
{
  "context": {
    "client": {
      "clientName": "WEB",
      "clientVersion": "2.20261020.01.00",
      "hl": "en",
      "gl": "GB"
    }
  },
  "panelId": "PAmodern_transcript_view",
  "params": "qgkPCgtkUXc0dzlXZ1hjURgC"
}
```

The old encoder's single-byte field-tag helper cannot encode field 149. The
prototype uses proper varints for tags and lengths. The client version is the
observed version, not a permanent constant; the CLI accepts an override.

## Live results

Each row returned HTTP 200, nonempty text, and validated start/end times through
anonymous Python requests. These are functionality checks, not a throughput test.

| Video | Requested track | Segments |
| --- | --- | ---: |
| `dQw4w9WgXcQ` | Default | 24 |
| `Rt6hGvzHR-o` | Default | 199 |
| `jNQXAC9IVRw` | Default | 3 |
| `aircAruvnKk` | Default | 129 |
| `dQw4w9WgXcQ` | `.en`, manual English | 24 |
| `dQw4w9WgXcQ` | `a.en`, automatic English | 26 |
| `dQw4w9WgXcQ` | `.ja`, Japanese | 23 |

An independently executed CLI run reproduced the Japanese result and text hash.
The longer samples extend to about 18 and 25 minutes and exercise multiple
sections and chapter headings. The response groups text differently from the
older caption API, so segment counts and boundaries differ. Exact full-text
parity against every original caption cue has not been established.

## Parsing and track selection

Text lives under `transcriptSegmentViewModel.simpleText`, nested inside
`macroMarkersPanelItemViewModel`. Millisecond start/end times live separately in
`frameworkUpdates.entityBatchUpdate.mutations[].payload.timedMarkersListSyncEntity`.

Select the entity referenced by the panel's `onShowCommands`, flatten its timing
sections, and index that list using each item's global `index`. Chapter headings
consume indices too. Zipping transcript-only items with all timings assigns
incorrect times. The prototype checks each matched start against the item's
seek command and rejects missing or invalid times.

An invalid track ID returned HTTP 200 with the default English transcript. The
prototype therefore decodes the selected track from the server's continuation
and rejects mismatches for explicit track requests. In the captured continuation,
outer field 377091426 contains panel ID in field 2 and encoded panel parameters
in field 3. Those parameters contain the selected track in nested field 6.
One default-track response (`Rt6hGvzHR-o`) omitted field 6, so default language
identification is not guaranteed by this continuation alone.

## Reproduce

From the repository root, using its existing Python environment:

```bash
.venv/bin/python research/panel_probe.py dQw4w9WgXcQ
.venv/bin/python research/panel_probe.py dQw4w9WgXcQ --track .ja
.venv/bin/python research/panel_probe.py aircAruvnKk
.venv/bin/python -m pytest -o addopts='' research/test_panel_probe.py -q
```

The CLI prints status, segment count, time bounds, and a text hash. It exits
nonzero on HTTP, parsing, or track-selection failure. For Python experiments,
`fetch_panel(video_id, track_id=None)` returns dictionaries with `start_ms`,
`end_ms`, and `text`. It makes one request with a 20-second timeout and no retry,
using the package's existing `requests` dependency.

Seven focused prototype tests cover captured protobuf bytes, chapter-index
timing, missing timestamps, empty responses, and selected-track verification.
The prototype also parsed all seven live captures. At the research stage, the
five original live API tests still failed against the old Android player
profile. After production integration they pass with Android `20.10.38`
discovery and WEB `2.20261020.01.00` panel retrieval. Production tests also cover
public models, session injection, cache behavior, named tracks, silent fallback,
ASR default resolution, incomplete panels, malformed responses, and CLI commands.

Initial combined migration verification passed 91 tests on Python 3.13 (84 package tests
and seven prototype tests). All 84 package tests also passed against the built
wheel on Python 3.9, including the five original live API tests. Both installed
CLI commands passed live checks. The final production parser accepted all seven
saved response cases, and fresh production requests reproduced manual English,
automatic English, Japanese, Filipino ASR, and chaptered transcript results.

## Integration and Discord viability

The initial precondition hurdle is cleared for the new route. A browser or Node
helper would add operational cost without an observed benefit here. The
[legacy investigation](legacy_get_transcript.md) records why client updates,
BotGuard helpers and native browser requests did not repair `get_transcript`.

The production implementation lives in `yt_transcript_fetcher/_panel.py`, with
integration at the existing fetcher and model factory boundaries. It preserves
caption `vssId` privately without changing the `Language` dataclass constructor
or serialized fields, retains legacy protobuf helpers, and rejects silent
language fallback. When the server omits field 6, it accepts only a default track
unambiguously established by player metadata; this covers the ASR-only video.
It checks all caption timing slots have matching views, and rejects unknown
response shapes rather than exposing partial results. Translation and paginated
transcript retrieval have not been established by this investigation. Private,
authenticated, and restricted-content behavior has not been validated live.

The existing public API remains unchanged, including its first matching
language-code selection. Upstream segment grouping differs. The transcript fix
retains the previous exception behavior and HTTP 400 retries. Transport error
corrections and the retry-policy change are separated onto a dependent branch
for a later breaking release. No package release has been published as part of
this work.

The remaining operational question is rate limiting on the actual Discord host.
The next gate is a bounded run at its expected volume, with per-video caching,
duplicate-request coalescing, limited concurrency, and backoff on 429/transient
failures. This protocol success does not establish exemption from rate limits.

`observations.json` contains redacted results and a fingerprint of the inspected
website source. Browser HARs, cookies and raw responses remain outside the
repository. The optional `transcript_probe.mjs` and `package.json` reproduce the
legacy browser control; they are not dependencies of the working Python route.
