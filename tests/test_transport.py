"""Public API compatibility and request routing without a network dependency."""

import json
from pathlib import Path

import pytest
import requests

import yt_transcript_fetcher as package
from yt_transcript_fetcher import Language, LanguageList, Transcript, YouTubeTranscriptFetcher
from yt_transcript_fetcher.exceptions import NoLanguageError, NoSegmentsError, NoTranscriptError, VideoNotFoundError, YouTubeAPIError
from yt_transcript_fetcher.protobuf import generate_params


VIDEO = "jNQXAC9IVRw"


def response(data, status=200):
    result = requests.Response()
    result.status_code = status
    result.headers["Content-Type"] = "application/json"
    result._content = json.dumps(data).encode()
    return result


class RecordingSession(requests.Session):
    def __init__(self, *responses):
        super().__init__()
        self.responses = iter(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def panel_response():
    return json.loads(Path(__file__).with_name("fixtures").joinpath("modern_panel.json").read_text())


@pytest.fixture
def player_response():
    return {
        "playabilityStatus": {"status": "OK"},
        "captions": {"playerCaptionsTracklistRenderer": {"captionTracks": [
            {"languageCode": "en", "name": {"simpleText": "English"}, "vssId": ".en"},
            {"languageCode": "en", "name": {"simpleText": "English (auto-generated)"}, "vssId": "a.en", "kind": "asr"},
        ], "audioTracks": [{"defaultCaptionTrackIndex": 0}], "defaultAudioTrackIndex": 0}},
    }


def test_public_calls_reuse_language_cache_and_injected_session(player_response, panel_response):
    session = RecordingSession(response(player_response), response(panel_response), response(panel_response))
    session.headers["User-Agent"] = "caller-agent"
    session.proxies["https"] = "http://caller-proxy.invalid:80"
    headers, adapters, proxies = dict(session.headers), dict(session.adapters), dict(session.proxies)
    fetcher = YouTubeTranscriptFetcher(session=session)
    languages = fetcher.list_languages(VIDEO)
    first = fetcher.get_transcript(VIDEO)
    second = fetcher.get_transcript(VIDEO, language="en")
    assert isinstance(languages, LanguageList)
    assert len(languages) == 2  # Duplicate codes retain manual/ASR ordering.
    assert first == second
    assert isinstance(first, Transcript)
    assert first.language is languages[0]
    assert fetcher.languages[VIDEO] is languages
    assert fetcher.session is session
    assert (dict(session.headers), dict(session.adapters), dict(session.proxies)) == (headers, adapters, proxies)
    assert len(session.calls) == 3
    discovery_url, discovery = session.calls[0]
    assert "/player?" in discovery_url
    assert discovery["json"]["context"]["client"]["clientVersion"] == "20.10.38"
    for url, kwargs in session.calls[1:]:
        assert "/get_panel?" in url
        assert kwargs["json"]["panelId"] == "PAmodern_transcript_view"
        assert kwargs["json"]["params"] == "qgkUCgtqTlFYQUM5SVZSdxgCMgMuZW4%3D"
        assert kwargs["json"]["context"]["client"]["clientName"] == "WEB"
        assert kwargs["timeout"] > 0


def test_exact_named_track_is_requested_and_silent_fallback_rejected(player_response, panel_response):
    player_response["captions"]["playerCaptionsTracklistRenderer"]["captionTracks"][0]["vssId"] = ".en.named"
    session = RecordingSession(response(player_response), response(panel_response))
    with pytest.raises(NoTranscriptError):
        YouTubeTranscriptFetcher(session).get_transcript(VIDEO)
    assert session.calls[1][1]["json"]["params"] == "qgkaCgtqTlFYQUM5SVZSdxgCMgkuZW4ubmFtZWQ%3D"


def test_caller_created_legacy_cached_language_still_works(panel_response):
    language = Language("en", "English", False, generate_params(VIDEO, "en", False))
    fetcher = YouTubeTranscriptFetcher(RecordingSession(response(panel_response)))
    fetcher.languages[VIDEO] = LanguageList([language])
    assert fetcher.get_transcript(VIDEO).language is language
    assert "/get_panel?" in fetcher.session.calls[0][0]


def test_unsupported_language_avoids_panel_request(player_response):
    session = RecordingSession(response(player_response))
    with pytest.raises(NoTranscriptError, match=f"No transcript available for video {VIDEO} in language xx."):
        YouTubeTranscriptFetcher(session).get_transcript(VIDEO, "xx")
    assert len(session.calls) == 1


@pytest.mark.parametrize("status", ["ERROR", "LOGIN_REQUIRED", "UNPLAYABLE"])
def test_unavailable_video_preserves_exception(status):
    session = RecordingSession(response({"playabilityStatus": {"status": status, "reason": "Unavailable"}}))
    with pytest.raises(VideoNotFoundError, match=VIDEO):
        YouTubeTranscriptFetcher(session).get_transcript(VIDEO)


def test_video_without_captions_preserves_exception():
    session = RecordingSession(response({"playabilityStatus": {"status": "OK"}}))
    with pytest.raises(NoLanguageError):
        YouTubeTranscriptFetcher(session).list_languages(VIDEO)


@pytest.mark.parametrize("method", ["list_languages", "get_transcript"])
@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_http_failures_preserve_legacy_exception_contract(method, status):
    session = RecordingSession(response({}, status))
    fetcher = YouTubeTranscriptFetcher(session)
    if method == "get_transcript":
        fetcher.languages[VIDEO] = LanguageList([Language("en", "English", False, generate_params(VIDEO, "en", False))])
    expected = VideoNotFoundError if method == "list_languages" else requests.HTTPError
    with pytest.raises(expected) as error:
        getattr(fetcher, method)(VIDEO)
    http_error = error.value.__cause__ if method == "list_languages" else error.value
    assert isinstance(http_error, requests.HTTPError)
    assert http_error.response.status_code == status


@pytest.mark.parametrize("method", ["list_languages", "get_transcript"])
def test_precondition_failures_preserve_endpoint_specific_exceptions(method):
    fetcher = YouTubeTranscriptFetcher(RecordingSession(response({"error": {"status": "FAILED_PRECONDITION"}}, 400)))
    if method == "get_transcript":
        fetcher.languages[VIDEO] = LanguageList([Language("en", "English", False, generate_params(VIDEO, "en", False))])
    expected = YouTubeAPIError if method == "list_languages" else requests.HTTPError
    with pytest.raises(expected):
        getattr(fetcher, method)(VIDEO)


def test_default_session_preserves_http_400_retries():
    fetcher = YouTubeTranscriptFetcher()
    retry = fetcher.session.get_adapter(fetcher.URL).max_retries
    assert retry.is_retry("POST", 400)
    assert retry.is_retry("POST", 429)
    assert retry.is_retry("POST", 503)


@pytest.mark.parametrize("data,expected", [
    ({}, VideoNotFoundError),
    ([], AttributeError),
    ({"error": {"message": "Unexpected API failure"}}, VideoNotFoundError),
])
def test_malformed_player_response_preserves_legacy_errors(data, expected):
    with pytest.raises(expected):
        YouTubeTranscriptFetcher(RecordingSession(response(data))).list_languages(VIDEO)


@pytest.mark.parametrize("method", ["list_languages", "get_transcript"])
@pytest.mark.parametrize("failure_type", [requests.Timeout, requests.ConnectionError])
def test_network_failures_preserve_legacy_wrapping(method, failure_type):
    failure = failure_type("Connection failed")
    fetcher = YouTubeTranscriptFetcher(RecordingSession(failure))
    if method == "get_transcript":
        fetcher.languages[VIDEO] = LanguageList([Language("en", "English", False, generate_params(VIDEO, "en", False))])
    with pytest.raises(Exception) as error:
        getattr(fetcher, method)(VIDEO)
    if method == "list_languages":
        assert type(error.value) is Exception
        assert error.value.__cause__ is failure
        assert f"Failed to fetch languages for video {VIDEO}" in str(error.value)
    else:
        assert error.value is failure


def test_uncached_transcript_preserves_discovery_error_contract():
    fetcher = YouTubeTranscriptFetcher(RecordingSession(response({}, 429)))
    with pytest.raises(VideoNotFoundError) as error:
        fetcher.get_transcript(VIDEO)
    assert error.value.__cause__.response.status_code == 429


@pytest.mark.parametrize("method", ["list_languages", "get_transcript"])
def test_invalid_json_preserves_requests_decode_error(method):
    invalid = response({})
    invalid._content = b"not JSON"
    fetcher = YouTubeTranscriptFetcher(RecordingSession(invalid))
    if method == "get_transcript":
        fetcher.languages[VIDEO] = LanguageList([Language("en", "English", False, generate_params(VIDEO, "en", False))])
    with pytest.raises(requests.exceptions.JSONDecodeError):
        getattr(fetcher, method)(VIDEO)


def test_missing_panel_preserves_no_segments_error():
    fetcher = YouTubeTranscriptFetcher(RecordingSession(response({})))
    fetcher.languages[VIDEO] = LanguageList([Language("en", "English", False, generate_params(VIDEO, "en", False))])
    with pytest.raises(NoSegmentsError):
        fetcher.get_transcript(VIDEO)


def test_module_helpers_keep_positional_and_keyword_arguments(monkeypatch, player_response, panel_response):
    fetcher = YouTubeTranscriptFetcher(RecordingSession(response(player_response), response(panel_response)))
    monkeypatch.setattr(package, "_default_fetcher", fetcher)
    assert isinstance(package.list_languages(VIDEO), LanguageList)
    assert package.get_transcript(VIDEO, language="en").language.code == "en"


@pytest.mark.parametrize("args,expected", [
    (["list-languages", VIDEO], "en: English"),
    (["download", "-l", "en", VIDEO], "[1.00 - 7.97] Sample text 1"),
])
def test_cli_existing_commands(monkeypatch, capsys, player_response, panel_response, args, expected):
    from yt_transcript_fetcher import cli
    fetcher = YouTubeTranscriptFetcher(RecordingSession(response(player_response), response(panel_response)))
    monkeypatch.setattr(package, "_default_fetcher", fetcher)
    monkeypatch.setattr("sys.argv", ["yt-transcript-fetcher"] + args)
    cli.main()
    assert expected in capsys.readouterr().out
