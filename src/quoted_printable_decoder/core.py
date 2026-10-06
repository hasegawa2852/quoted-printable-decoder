from __future__ import annotations


# Hard line limit from RFC 2045, section 6.7 (note 2).
_MAX_LINE_LEN = 76


def _is_printable(b: int) -> bool:
    """Return True for characters allowed literally in quoted-printable.

    Per RFC 2045 section 6.7, printable characters are the ASCII range
    33..126 excluding ``=``. Space and tab are also literal-eligible, but
    trailing whitespace on a line must be encoded; callers handle that.
    """
    return 33 <= b <= 126 and b != 61  # 61 == ord('=')


def _must_escape(b: int, is_trailing_ws: bool) -> bool:
    """Decide if byte ``b`` must be =HH-encoded.

    Trailing whitespace on a line must be encoded because the transport may
    strip trailing whitespace.
    """
    if is_trailing_ws:
        return True
    if b == 9 or b == 32:  # tab, space -- allowed when not trailing
        return False
    return not _is_printable(b)


def encode(data: bytes, *, max_line_len: int = _MAX_LINE_LEN) -> str:
    """Encode bytes to ASCII quoted-printable text.

    Long lines are broken with soft line breaks (``=`` at end of line),
    respecting ``max_line_len`` (default 76, the RFC limit).
    Lines are terminated with CRLF. The output never ends with a CRLF unless
    the input contained a trailing newline; soft-break wrapping does not add
    a real terminator after the last logical line.
    """
    if max_line_len < 3:
        raise ValueError("max_line_len must be >= 3")
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")

    # Split on \n so we preserve the caller's line structure. If input uses
    # bare \n we still output CRLF, which is the RFC wire form; callers who
    # want bare \n can split and rejoin.
    input_lines = bytes(data).split(b"\n")
    out_parts: list[str] = []
    n = len(input_lines)
    for idx, line in enumerate(input_lines):
        # Strip a trailing \r so "\r\n" is treated as one newline.
        if line.endswith(b"\r"):
            line = line[:-1]
            had_cr = True
        else:
            had_cr = idx < n - 1  # not last segment -> implied \n
        # Detect trailing tab/space to force-encode.
        stripped = line.rstrip(b" \t")
        trailing_ws_len = len(line) - len(stripped)

        encoded_chars: list[str] = []
        line_len = 0
        i = 0
        limit = len(line)
        # Build the encoded form of this logical line, inserting soft breaks.
        while i < limit:
            b = line[i]
            remaining = limit - i
            is_trail = (i >= limit - trailing_ws_len) if trailing_ws_len else False
            if _must_escape(b, is_trail):
                token = "={:02X}".format(b)
            else:
                token = chr(b)
            i += 1

            # Can we fit token on current output line?
            # Soft-break adds '='; need room for token and possible '='.
            # We are conservative: ensure room for token + '=' (unless this is
            # the very end of the logical line and no soft break needed).
            need = len(token) + (1 if i < limit else 0)
            if line_len + need > max_line_len and line_len > 0:
                out_parts.append("=\r\n")
                line_len = 0
            out_parts.append(token)
            line_len += len(token)

        # End of logical line: emit hard CRLF unless this is the final line
        # AND has no trailing newline in the input.
        is_last = idx == n - 1
        if not is_last or had_cr:
            out_parts.append("\r\n")

    return "".join(out_parts)


def decode(text: str | bytes) -> bytes:
    """Decode quoted-printable text to bytes.

    Accepts str or bytes. Accepts bare LF or CRLF line endings. Collapses
    soft line breaks (a line ending in ``=`` joined to the next). Malformed
    ``=XX`` sequences where XX is not two hex digits are passed through as
    the literal ``=`` followed by the offending characters (lenient decode).
    """
    if isinstance(text, (bytes, bytearray)):
        # Decode using latin-1 so every byte round-trips losslessly.
        s = bytes(text).decode("latin-1")
    elif isinstance(text, str):
        s = text
    else:
        raise TypeError("text must be str or bytes")

    # Normalize line endings to \n for uniform processing.
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = s.split("\n")
    out = bytearray()
    i = 0
    n = len(lines)
    first = True
    while i < n:
        line = lines[i]
        # Soft line break: line ends with '=' -> join with next line.
        while line.endswith("="):
            line = line[:-1]
            i += 1
            if i < n:
                line += lines[i]
            else:
                break
        i += 1

        # Hard line break between logical lines becomes \n.
        if not first:
            out.append(0x0A)
        first = False

        # Decode =XX escapes.
        j = 0
        L = len(line)
        while j < L:
            c = line[j]
            if c == "=":
                if j + 2 < L + 1 and j + 2 <= L - 1:
                    pass
                hexpart = line[j + 1 : j + 3]
                if len(hexpart) == 2 and _is_hex(hexpart):
                    out.append(int(hexpart, 16))
                    j += 3
                    continue
                # Lenient: pass through '=' and continue.
                out += b"="
                j += 1
            else:
                # Accept any ASCII char; also accept high bytes from latin-1.
                out.append(ord(c) & 0xFF)
                j += 1

    return bytes(out)


def _is_hex(s: str) -> bool:
    for ch in s:
        if not (
            "0" <= ch <= "9" or "A" <= ch <= "F" or "a" <= ch <= "f"
        ):
            return False
    return True
