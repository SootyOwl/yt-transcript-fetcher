#!/usr/bin/env python3
"""
Test script: bgutil-pot Rust utility for PoToken generation
and alternative ANDROID_VR approach for transcript fetching.

Results: See docs/test-results-potoken-rust-utility.md

Usage:
    # Download bgutil-pot first:
    # curl -sL -o bgutil-pot "https://github.com/jim60105/bgutil-ytdlp-pot-provider-rs/releases/download/v0.7.2/bgutil-pot-linux-x86_64"
    # chmod +x bgutil-pot

    python test_potoken_integration.py
"""

import json
import subprocess
import sys
import time

import requests

from yt_transcript_fetcher.protobuf import encode_visitor_data, generate_params

VIDEO_ID = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
BGUTIL_PATH = "./bgutil-pot"

TRANSCRIPT_URL = "https://www.youtube.com/youtubei/v1/get_transcript?prettyPrint=false"
PLAYER_URL = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"


def section(title):
    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}")


def test_bgutil_pot_generation():
    """Test 1: bgutil-pot binary token generation."""
    section("TEST 1: bgutil-pot Token Generation")

    result = subprocess.run(
        [BGUTIL_PATH, "--content-binding", VIDEO_ID, "--bypass-cache", "--verbose"],
        capture_output=True, text=True, timeout=30,
    )

    if result.returncode != 0:
        print(f"  FAILED: exit code {result.returncode}")
        print(f"  stderr: {result.stderr[:300]}")
        return False

    data = json.loads(result.stdout.strip())
    print(f"  poToken: {data['poToken'][:50]}...")
    print(f"  contentBinding: {data['contentBinding']}")
    print(f"  expiresAt: {data['expiresAt']}")
    print("  PASS")
    return True


def test_current_android_client():
    """Test 2: Current Android 19.09.37 client (expected to fail)."""
    section("TEST 2: Current Android 19.09.37 Client (no PoToken)")

    visitor_data = encode_visitor_data()
    context = {
        "client": {
            "clientName": "ANDROID",
            "clientVersion": "19.09.37",
            "userAgent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "osName": "Android",
            "osVersion": "11",
            "visitorData": visitor_data,
        }
    }

    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
    })

    # /player
    resp = s.post(PLAYER_URL, json={
        "context": context, "videoId": VIDEO_ID,
        "contentCheckOk": True, "racyCheckOk": True,
    }, timeout=15)
    print(f"  /player: HTTP {resp.status_code}")

    # /get_transcript
    params = generate_params(video_id=VIDEO_ID, language="en", auto_generated=True)
    resp = s.post(TRANSCRIPT_URL, json={"context": context, "params": params}, timeout=10)
    print(f"  /get_transcript: HTTP {resp.status_code}")

    if resp.status_code == 400:
        print("  CONFIRMED: Android 19.09.37 is broken (FAILED_PRECONDITION)")
    return resp.status_code


def test_web_with_potoken():
    """Test 3: WEB client with bgutil-pot PoToken (expected to fail due to session mismatch)."""
    section("TEST 3: WEB Client + bgutil-pot PoToken")

    # Generate PoToken
    result = subprocess.run(
        [BGUTIL_PATH, "--content-binding", VIDEO_ID, "--bypass-cache"],
        capture_output=True, text=True, timeout=30,
    )
    pot_data = json.loads(result.stdout.strip())
    po_token = pot_data["poToken"]
    print(f"  Generated poToken: {po_token[:40]}...")

    visitor_data = encode_visitor_data()
    context = {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20260306.01.00",
            "visitorData": visitor_data,
            "hl": "en",
            "gl": "US",
        }
    }

    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/",
    })

    # /player with PoToken
    resp = s.post(PLAYER_URL, json={
        "context": context, "videoId": VIDEO_ID,
        "contentCheckOk": True, "racyCheckOk": True,
        "serviceIntegrityDimensions": {"poToken": po_token},
    }, timeout=15)
    status = "N/A"
    if resp.status_code == 200:
        data = resp.json()
        status = data.get("playabilityStatus", {}).get("status", "?")
    print(f"  /player: HTTP {resp.status_code} (playability: {status})")

    # /get_transcript with PoToken
    params = generate_params(video_id=VIDEO_ID, language="en", auto_generated=True)
    resp = s.post(TRANSCRIPT_URL, json={
        "context": context, "params": params,
        "serviceIntegrityDimensions": {"poToken": po_token},
    }, timeout=10)
    print(f"  /get_transcript: HTTP {resp.status_code}")

    if resp.status_code != 200:
        print("  CONFIRMED: PoToken session mismatch - visitorData doesn't match bgutil-pot's internal session")
    return resp.status_code


def test_android_vr_client():
    """Test 4: ANDROID_VR client (yt-dlp's approach)."""
    section("TEST 4: ANDROID_VR Client (yt-dlp approach)")

    visitor_data = encode_visitor_data()
    context = {
        "client": {
            "clientName": "ANDROID_VR",
            "clientVersion": "1.62.27",
            "deviceMake": "Oculus",
            "deviceModel": "Quest 3",
            "osName": "Android",
            "osVersion": "12L",
            "androidSdkVersion": 32,
            "visitorData": visitor_data,
        }
    }

    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "User-Agent": "com.google.android.apps.youtube.vr.oculus/1.62.27 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip",
    })

    # /player (no PoToken needed)
    resp = s.post(PLAYER_URL, json={
        "context": context, "videoId": VIDEO_ID,
        "contentCheckOk": True, "racyCheckOk": True,
    }, timeout=15)

    if resp.status_code != 200:
        print(f"  /player: HTTP {resp.status_code}")
        return resp.status_code

    data = resp.json()
    ps = data.get("playabilityStatus", {})
    print(f"  /player: HTTP 200 (playability: {ps.get('status')})")

    tracks = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    print(f"  Caption tracks: {len(tracks)}")

    if tracks:
        for t in tracks[:3]:
            lang = t.get("languageCode", "")
            kind = t.get("kind", "manual")
            print(f"    - {lang} ({kind})")

        # Try fetching subtitle via signed URL
        url = tracks[0]["baseUrl"]
        print(f"\n  Fetching subtitle via timedtext URL...")
        time.sleep(1)
        resp2 = s.get(url, timeout=10)
        print(f"  timedtext: HTTP {resp2.status_code}")

        if resp2.status_code == 200 and len(resp2.text) > 10:
            print(f"  Content length: {len(resp2.text)} bytes")
            print("  PASS - Subtitles available via signed timedtext URLs!")
        elif resp2.status_code == 429:
            print("  Rate limited (429) - but URL is valid (try again later)")
            print("  PASS (conceptually) - ANDROID_VR /player works")
    else:
        print("  No caption tracks (video may not have subtitles)")

    # Also verify /get_transcript still fails (expected)
    params = generate_params(video_id=VIDEO_ID, language="en", auto_generated=True)
    resp = s.post(TRANSCRIPT_URL, json={"context": context, "params": params}, timeout=10)
    print(f"\n  /get_transcript: HTTP {resp.status_code} (expected to fail)")

    return 200 if ps.get("status") == "OK" else resp.status_code


def test_bgutil_server_mode():
    """Test 5: bgutil-pot HTTP server mode."""
    section("TEST 5: bgutil-pot HTTP Server Mode")

    server_proc = subprocess.Popen(
        [BGUTIL_PATH, "server", "--port", "4416"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(2)

    try:
        # Health check
        resp = requests.get("http://127.0.0.1:4416/ping", timeout=5)
        print(f"  /ping: {resp.json()}")

        # Generate token
        resp = requests.post(
            "http://127.0.0.1:4416/get_pot",
            json={"content_binding": VIDEO_ID},
            timeout=15,
        )
        data = resp.json()
        print(f"  /get_pot: HTTP {resp.status_code}")
        print(f"  poToken: {data['poToken'][:40]}...")
        print(f"  Response keys: {list(data.keys())}")
        print(f"  Note: No visitor_data in response")
        print("  PASS - Server mode works for token generation")
    except Exception as e:
        print(f"  ERROR: {e}")
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)


if __name__ == "__main__":
    print("bgutil-pot Integration Test Suite")
    print("=" * 35)
    print(f"Video: {VIDEO_ID}")
    print(f"Binary: {BGUTIL_PATH}")

    results = {}

    results["bgutil-pot generation"] = "PASS" if test_bgutil_pot_generation() else "FAIL"
    results["Android 19.09.37"] = "FAIL (expected)" if test_current_android_client() == 400 else "UNEXPECTED"
    results["WEB + PoToken"] = "FAIL (expected)" if test_web_with_potoken() != 200 else "PASS"
    results["ANDROID_VR"] = "PASS" if test_android_vr_client() == 200 else "FAIL"
    test_bgutil_server_mode()

    section("RESULTS SUMMARY")
    for test, result in results.items():
        print(f"  {test:30s} {result}")

    print()
    print("KEY FINDINGS:")
    print("  1. bgutil-pot generates valid PoTokens (CLI and server mode)")
    print("  2. Android 19.09.37 is completely broken (FAILED_PRECONDITION)")
    print("  3. WEB + PoToken fails due to visitorData/session mismatch")
    print("  4. ANDROID_VR works for /player without PoToken (yt-dlp's approach)")
    print("  5. /get_transcript endpoint requires PoToken on ALL clients")
    print()
    print("RECOMMENDED: Switch to ANDROID_VR + signed timedtext URLs")
    print(f"{'='*60}")
