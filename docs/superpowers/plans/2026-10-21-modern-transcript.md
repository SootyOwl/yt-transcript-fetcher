# Modern Transcript Production Migration Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. The user has explicitly authorized production integration of the researched method.

**Goal:** Fetch modern panel transcripts through the existing package interfaces.

**Architecture:** Keep existing models, constructors, helpers, legacy protobuf functions and response parsing. Add a private panel protocol module, retain discovered track identity as private metadata, and route the existing fetcher through updated player discovery and WEB panel retrieval.

**Tech Stack:** Python >=3.9,<4.0, existing requests dependency, pytest.

**Spec:** research/README.md and the user's instruction to integrate the method with full API backwards compatibility. Compatibility means existing calls, constructors, model types, helpers, language ordering/cache, session injection and named errors; it cannot mean identical upstream transcript segmentation.

## Global Constraints

- No browser, Node or new runtime dependency; no caption URL fallback.
- Keep get_transcript(video_id, language="en"), list_languages(video_id), and YouTubeTranscriptFetcher(session=None).
- Preserve the four Language constructor fields and existing dataclass serialization; retain vssId through private non-dataclass metadata.
- Keep legacy generate_params and continuation decoding operational.
- Use proper protobuf varints for field 149; verify selected video and track before exposing a transcript.
- Keep caller-supplied session configuration. The fix release retains the old exception and retry behavior, including HTTP 400 retries.
- Commit the transcript fix and revised error behavior on separate stacked branches, as subsequently requested by the user. Publishing and pushing are not requested.

## Review Focus

- ASR-only response omits selected-track field 6: resolve only using unambiguous player default metadata, never blindly accept the requested track.
- Chapter headings consume timing indices: join against the referenced entity's complete timing list.
- Unknown tracks silently fall back: reject mismatched selection with NoTranscriptError.
- Empty/error/malformed responses: preserve meaningful errors, never fabricate zero-time segments or expose partial transcripts.
- Legacy models and caller-created cached languages: retain old constructors/tokens and sensible track derivation when private metadata is absent.

## Task 1: Protocol and model compatibility

**Files:** add yt_transcript_fetcher/_panel.py and tests/test_panel.py; extend models.py only at discovery/parser boundaries.

**Interfaces:** panel encode_params(video_id, track_id); selection(response) -> (video_id, optional track_id); segments(response) -> normalized Segment constructor dictionaries. Models keep existing factories.

- [x] Add failing wire-fixture, chapter timing, missing/reversed timing, wrong-video, track-fallback and legacy parser regression tests.
- [x] Implement bounded protobuf parsing and panel selection/segment normalization; preserve exact vssId and unambiguous default track privately during player discovery.
- [x] Run new tests and original model/protobuf tests; also parse frozen live responses.

## Task 2: Fetcher integration

**Files:** api.py, tests/test_transport.py; retain existing tests/test_api.py live checks.

**Interfaces:** existing fetcher and module functions; separate Android player and WEB panel contexts.

- [x] Add failing injected-session tests for discovery/cache, default/language selection, unsupported language, unavailable video, no captions, HTTP failures and legacy cached Language objects.
- [x] Update discovery client and request routing; validate selection and construct the same Transcript/SegmentList/Segment objects.
- [x] Run deterministic tests and bounded live API/CLI checks on public, ASR-only, multilingual and unavailable videos.

## Task 3: Documentation and verification

**Files:** README.md and a small migration note in research/README.md.

- [x] Correct existing README invocation examples and describe new backend, compatibility and upstream segment differences.
- [x] Run the full suite with network access, Python 3.9 syntax checks, and CLI/module-wrapper checks.
- [x] Independently review the production diff; reproduce and fix any behavior-affecting findings before reporting completion.

## Execution notes

Initial live discovery confirms Android 20.10.38 returns six tracks for dQw4w9WgXcQ, one ASR Filipino track for Rt6hGvzHR-o, and an ERROR playability response for 11111111111. The prototype rejects the ASR-only response because selected-track field 6 is absent; production must handle this explicitly rather than claiming the prototype already covered all compatibility cases.

Completed 2026-10-21 in the shared working tree. Task 1's model/codec regressions
and Task 2's request/error regressions were observed failing before implementation.
An independent read-only review found unordered panel views, mixed unknown
content, and invalid optional audio metadata. Regression tests reproduced these
failures; all were fixed in one pass. No review findings remain deferred.

Final verification:

- Python 3.13: `python -m pytest -o addopts='' tests research/test_panel_probe.py -q`
  passed 91 tests, including all five original live integration tests.
- Built a wheel and installed it in an isolated Python 3.9 environment. From the
  repo fixture directory, isolated imports with `python -I -m pytest
  --import-mode=importlib -o addopts='' tests -q` passed all 84 package tests.
  An earlier invocation from /tmp could not find two existing relative-path
  fixtures; rerunning with the expected fixture working directory resolved that.
- Fresh production requests succeeded on four public videos, including manual
  English, automatic English, Japanese, Filipino ASR, and chaptered transcripts.
- Both installed CLI commands passed live checks; the final parser accepted all
  seven frozen live response cases; Python 3.9 syntax and diff whitespace checks
  passed.

Optional invalid audio metadata does not prevent language discovery or establish
an unsupported default. Incomplete or unknown modern response shapes fail
explicitly. Upstream cue parity, translation/pagination, authenticated content
and host-specific rate limits remain outside the verified behavior.

## Release separation

The user subsequently requested separate commits and branches for the compatible
transcript repair and the breaking exception/retry changes:

- `fix/modern-transcript-panel`: `fix(api): restore transcripts using modern YouTube panels`.
  Retains the original discovery exception mapping, transcript HTTP/JSON errors,
  network-error wrapping and HTTP 400 retries. The original discovery and session
  initialization methods are structurally identical to the base revision.
- `feat/transcript-error-contract`: branches from the fix commit and adds the
  revised error contract and retry policy with a Conventional Commit marked
  `!` and an explicit `BREAKING CHANGE:` footer.

Merge and release the fix on main before merging the breaking change. The
workflow runs after successful tests on main; merging both before the first
release would produce a single major release. Keep the Conventional Commit
subject and footer if squash-merging. Leave version and changelog updates to
semantic-release rather than manually changing them on these branches.

Compatibility regression tests were observed failing against the combined
implementation before restoring legacy behavior. The same cases exercise
the new contract on the dependent branch; the protocol/model implementation and
research artifacts are retained on both branches.

The compatible fix passes 110 tests on Python 3.13, including live checks, and
105 offline tests on Python 3.9. The workflow's exact python-semantic-release
10.3.1 parser with this repository's options classifies the planned fix commit
as PATCH and the explicit breaking-change commit as MAJOR.

The fix is committed as `a1087e6`. The dependent breaking branch also passes all
110 tests on Python 3.13 and 105 offline tests on Python 3.9. Its production code,
protocol tests and research artifacts match the preserved pre-split snapshot
byte-for-byte; only release documentation and expanded transport tests differ.
Both behavior sets remain available on their respective branches.
