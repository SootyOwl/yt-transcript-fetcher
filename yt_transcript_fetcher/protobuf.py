import base64
import random
import string
import time
import urllib.parse


def _encode_varint(value):
    """Encode an integer as a protobuf varint (variable-length integer)."""
    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def generate_visitor_id(length=11):
    """Generate a random visitor ID string (11 characters like YouTube.js uses)."""
    # YouTube.js uses alphanumeric characters for visitor IDs
    chars = string.ascii_letters + string.digits + "-_"
    return "".join(random.choice(chars) for _ in range(length))


def encode_visitor_data(visitor_id=None, timestamp=None):
    """
    Encode visitor data as a protobuf message, matching YouTube.js VisitorData format.
    
    The VisitorData protobuf message has:
    - Field 1 (string): id - An 11-character random string
    - Field 5 (int64): timestamp - Unix timestamp in seconds
    
    This is then base64url encoded (with URL-safe characters) and URL-encoded.
    
    Args:
        visitor_id: Optional visitor ID string. If not provided, generates a random one.
        timestamp: Optional Unix timestamp. If not provided, uses current time.
    
    Returns:
        URL-encoded base64url string of the protobuf message.
    
    Reference: https://github.com/LuanRT/YouTube.js/blob/main/src/utils/ProtoUtils.ts
    """
    if visitor_id is None:
        visitor_id = generate_visitor_id()
    if timestamp is None:
        timestamp = int(time.time())
    
    result = b""
    
    # Field 1: visitor ID string (wire type 2 = length-delimited)
    # Format: (field_number << 3) | wire_type = (1 << 3) | 2 = 10
    id_bytes = visitor_id.encode("utf-8")
    result += bytes([10])  # field header
    result += _encode_varint(len(id_bytes))
    result += id_bytes
    
    # Field 5: timestamp as int64 (wire type 0 = varint)
    # Format: (field_number << 3) | wire_type = (5 << 3) | 0 = 40
    result += bytes([40])  # field header
    result += _encode_varint(timestamp)
    
    # Base64 encode with URL-safe characters
    base64_string = base64.b64encode(result).decode("ascii")
    # Replace +/ with -_ for URL-safe base64url format
    base64url_string = base64_string.replace("+", "-").replace("/", "_")
    # URL encode
    return urllib.parse.quote(base64url_string)


def decode_visitor_data(encoded_visitor_data):
    """
    Decode an encoded visitor data string back to (visitor_id, timestamp).
    
    This is the inverse of encode_visitor_data().
    
    Args:
        encoded_visitor_data: URL-encoded base64url string of the protobuf message.
    
    Returns:
        Tuple of (visitor_id: str, timestamp: int)
    """
    # URL decode
    base64url_string = urllib.parse.unquote(encoded_visitor_data)
    # Replace URL-safe chars back to standard base64
    base64_string = base64url_string.replace("-", "+").replace("_", "/")
    # Add padding if needed
    padding = 4 - (len(base64_string) % 4)
    if padding != 4:
        base64_string += "=" * padding
    # Base64 decode
    protobuf_bytes = base64.b64decode(base64_string)
    
    visitor_id = None
    timestamp = None
    i = 0
    
    while i < len(protobuf_bytes):
        if i >= len(protobuf_bytes):
            break
        field_header = protobuf_bytes[i]
        field_number = field_header >> 3
        wire_type = field_header & 0x07
        i += 1
        
        if wire_type == 2:  # Length-delimited (string)
            length, bytes_read = _decode_varint(protobuf_bytes, i)
            i += bytes_read
            value = protobuf_bytes[i:i + length].decode("utf-8")
            i += length
            if field_number == 1:
                visitor_id = value
        elif wire_type == 0:  # Varint
            value, bytes_read = _decode_varint(protobuf_bytes, i)
            i += bytes_read
            if field_number == 5:
                timestamp = value
    
    return visitor_id, timestamp


def _decode_varint(data, offset):
    """Decode a protobuf varint starting at offset. Returns (value, bytes_read)."""
    result = 0
    shift = 0
    bytes_read = 0
    while offset + bytes_read < len(data):
        byte = data[offset + bytes_read]
        result |= (byte & 0x7F) << shift
        bytes_read += 1
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, bytes_read


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