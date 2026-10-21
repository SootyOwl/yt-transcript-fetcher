"""Compare the encoder against a frozen live website observation, without HTTP."""

import json
from pathlib import Path

from yt_transcript_fetcher.protobuf import generate_params


observation = json.loads(Path(__file__).with_name("observations.json").read_text())
fixture = observation["params_fixture"]
actual = generate_params(fixture["video_id"], fixture["language"], fixture["auto_generated"])
if actual != fixture["website_params"]:
    raise SystemExit("FAIL: generated params differ from the frozen website observation")
print("PASS: generated params exactly match the captured manual English track")
