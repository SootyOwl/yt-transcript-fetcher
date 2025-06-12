import base64
import urllib.parse


# region: protobuf encoding helpers
def _encode_protobuf_field(field_number, wire_type, data):
    """Encode a protobuf field with header and data"""
    field_header = (field_number << 3) | wire_type

    if wire_type == 2:  # Length-delimited (strings, bytes)
        return bytes([field_header, len(data)]) + data
    elif wire_type == 0:  # Varint (integers)
        return bytes([field_header, data])
    else:
        return b""


def _create_nested_protobuf(language, auto_generated=True):
    """Create the nested protobuf for Field 2"""
    result = b""

    # Field 1: "asr" (Automatic Speech Recognition)
    subtitle_type = "asr" if auto_generated else ""
    type_bytes = subtitle_type.encode("utf-8")
    result += _encode_protobuf_field(1, 2, type_bytes)

    # Field 2: language code
    lang_bytes = language.encode("utf-8")
    result += _encode_protobuf_field(2, 2, lang_bytes)

    # Field 3: empty string
    result += _encode_protobuf_field(3, 2, b"")

    return result


def _create_main_protobuf(
    video_id,
    language,
    auto_generated=True
):
    """Create the main protobuf with all required fields"""
    result = b""

    # Field 1: Video ID
    video_id_bytes = video_id.encode("utf-8")
    result += _encode_protobuf_field(1, 2, video_id_bytes)

    # Field 2: URL-encoded base64 of nested protobuf (KEY INSIGHT!)
    nested_protobuf = _create_nested_protobuf(language, auto_generated)
    nested_base64 = base64.b64encode(nested_protobuf).decode("ascii")
    nested_base64_url_encoded = urllib.parse.quote(nested_base64)
    nested_field2_bytes = nested_base64_url_encoded.encode("utf-8")
    result += _encode_protobuf_field(2, 2, nested_field2_bytes)

    # Field 3: Boolean flag (1)
    result += _encode_protobuf_field(3, 0, 1)

    # Field 5: Engagement panel string
    panel_string = "engagement-panel-searchable-transcript-search-panel"
    panel_bytes = panel_string.encode("utf-8")
    result += _encode_protobuf_field(5, 2, panel_bytes)

    # Fields 6, 7, 8: Boolean flags (all 1)
    result += _encode_protobuf_field(6, 0, 1)
    result += _encode_protobuf_field(7, 0, 1)
    result += _encode_protobuf_field(8, 0, 1)

    return result


def generate_params(video_id, language, auto_generated=True):
    """Generate the params string for the YouTube transcript API"""
    # Create the main protobuf
    protobuf_bytes = _create_main_protobuf(video_id, language, auto_generated)

    # Convert to base64
    base64_string = base64.b64encode(protobuf_bytes).decode("ascii")

    # URL encode
    params = urllib.parse.quote(base64_string)

    return params

# endregion: protobuf encoding helpers

# region: protobuf decoding helpers
def retrieve_language_code(continuation_token):
    """Extract language code from YouTube continuation token"""
    try:
        nested_bytes = _decode_nested_bytes(continuation_token)
        
        # Parse nested protobuf to get language (Field 2)
        i = 0
        while i < len(nested_bytes):
            field_header = nested_bytes[i]
            field_number = field_header >> 3
            
            if field_number == 2:  # Language field
                i += 1
                length = nested_bytes[i]
                i += 1
                language = ''.join(chr(nested_bytes[i + j]) for j in range(length))
                return language
            
            # Skip this field
            i += 1
            if i < len(nested_bytes):
                length = nested_bytes[i]
                i += 1 + length
        
        return None
        
    except Exception:
        return None

def is_asr_captions(continuation_token):
    """Check if continuation token represents auto-generated captions (asr)"""
    try:
        # URL decode and base64 decode the token
        nested_bytes = _decode_nested_bytes(continuation_token)
        
        # Parse nested protobuf to get Field 1 (subtitle type)
        if len(nested_bytes) >= 4 and nested_bytes[0] == 10:  # Field 1, wire type 2
            length = nested_bytes[1]
            if length == 3:  # "asr" is 3 characters
                asr_text = ''.join(chr(nested_bytes[2 + j]) for j in range(3))
                return asr_text == "asr"
            else:
                return False  # Empty string = manual
        
        return False
    
    except (ValueError, IndexError, TypeError):
        raise ValueError("Invalid continuation token format or content")
    
def get_video_id(continuation_token):
    """Extract video ID from YouTube continuation token"""
    try:
        # video ID is the first field in the main protobuf
        url_decoded = urllib.parse.unquote(continuation_token)
        token_bytes = list(base64.b64decode(url_decoded))
        # Parse the first field (video ID)
        i = 0
        while i < len(token_bytes):
            field_header = token_bytes[i]
            field_number = field_header >> 3
            
            if field_number == 1:  # Video ID field
                i += 1
                length = token_bytes[i]
                i += 1
                video_id = ''.join(chr(token_bytes[i + j]) for j in range(length))
                return video_id
            
            # Skip this field
            i += 1
            if i < len(token_bytes):
                length = token_bytes[i]
                i += 1 + length

        raise ValueError("Video ID not found in continuation token")
    except (ValueError, IndexError, TypeError):
        raise ValueError("Invalid continuation token format or content")

def _decode_nested_bytes(continuation_token):
    url_decoded = urllib.parse.unquote(continuation_token)
    token_bytes = list(base64.b64decode(url_decoded))
        
        # Extract Field 2 (nested protobuf)
    field2_length = token_bytes[14]
    field2_data = token_bytes[15:15 + field2_length]
    field2_string = ''.join(chr(b) for b in field2_data)
        
        # URL decode and base64 decode the nested protobuf
    nested_url_decoded = urllib.parse.unquote(field2_string)
    nested_bytes = list(base64.b64decode(nested_url_decoded))
    return nested_bytes