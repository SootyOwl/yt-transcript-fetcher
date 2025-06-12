import pytest
from yt_transcript.protobuf import (
    _encode_protobuf_field,
    _create_nested_protobuf,
    _create_main_protobuf,
    generate_params,
    _decode_nested_bytes,
    retrieve_language_code,
    is_asr_captions,
    get_video_id
)




@pytest.mark.parametrize(
    "field_number, field_type, value, result",
    [
        (1, 0, 1, b"\x08\x01"),
        (2, 0, 1, b"\x10\x01"),
        (3, 0, 1, b"\x18\x01"),
        (4, 0, 1, b"\x20\x01"),
        (5, 2, b"test", b"\x2a\x04test"),
    ],
)
def test_encode_protobuf_field(field_number, field_type, value, result):
    """Test encoding of protobuf fields"""
    assert _encode_protobuf_field(field_number, field_type, value) == result


def test_create_nested_protobuf():
    """Test creation of nested protobuf structure"""
    assert _create_nested_protobuf("en", False) == b"\n\x00\x12\x02en\x1a\x00"
    assert _create_nested_protobuf("fr", True) == b"\n\x03asr\x12\x02fr\x1a\x00"


def test_create_main_protobuf():
    """Test creation of main protobuf structure"""
    video_id = "test_video_id"
    language = "en"
    result = _create_main_protobuf(video_id, language)

    assert (
        result
        == b"\n\rtest_video_id\x12\x12CgNhc3ISAmVuGgA%3D\x18\x01*3engagement-panel-searchable-transcript-search-panel0\x018\x01@\x01"
    )


def test_generate_params():
    """Test generation of params string for YouTube transcript API"""
    video_id = "test_video_id"
    language = "en"
    params = generate_params(video_id, language)

    expected_params = "Cg10ZXN0X3ZpZGVvX2lkEhJDZ05oYzNJU0FtVnVHZ0ElM0QYASozZW5nYWdlbWVudC1wYW5lbC1zZWFyY2hhYmxlLXRyYW5zY3JpcHQtc2VhcmNoLXBhbmVsMAE4AUAB"

    assert params == expected_params

def test_decode_nested_bytes(continuation_token):
    """Test decoding of nested bytes from continuation token"""
    expected_bytes = [10, 0, 18, 2, 101, 110, 26, 0]
    assert _decode_nested_bytes(continuation_token) == expected_bytes

def test_retrieve_language_code(continuation_token):
    """Test retrieval of language code from continuation token"""
    assert retrieve_language_code(continuation_token) == "en"

def test_is_asr_captions():
    """Test detection of ASR captions"""
    assert is_asr_captions("CgtybkNWbFZTRTVwSRISQ2dOaGMzSVNBbVJsR2dBJTNEGAEqM2VuZ2FnZW1lbnQtcGFuZWwtc2VhcmNoYWJsZS10cmFuc2NyaXB0LXNlYXJjaC1wYW5lbDABOAFAAQ==") is True
    assert is_asr_captions("CgtybkNWbFZTRTVwSRIOQ2dBU0FtUmxHZ0ElM0QYASozZW5nYWdlbWVudC1wYW5lbC1zZWFyY2hhYmxlLXRyYW5zY3JpcHQtc2VhcmNoLXBhbmVsMAE4AUAB") is False

def test_is_asr_captions_invalid():
    """Test detection of ASR captions with invalid input"""
    with pytest.raises(ValueError):
        is_asr_captions("invalid_base64_string")
    with pytest.raises(ValueError):
        is_asr_captions("")
    with pytest.raises(ValueError):
        is_asr_captions(None)

def test_get_video_id(continuation_token):
    """Test extraction of video ID from continuation token"""
    expected_video_id = "dQw4w9WgXcQ"
    assert get_video_id(continuation_token) == expected_video_id

    # Test with an invalid continuation token
    with pytest.raises(ValueError):
        get_video_id("invalid_continuation_token")