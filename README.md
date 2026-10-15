# quoted-printable-decoder

A small, zero-dependency Python library that encodes bytes to and decodes bytes from the MIME quoted-printable format defined by RFC 2045.

## Usage

```python
from quoted_printable_decoder import encode, decode

encoded = encode(b"Hello = World\xff")
# 'Hello =3D World=FF'
assert decode(encoded) == b"Hello = World\xff"
```

`encode(data: bytes, *, max_line_len: int = 76) -> str` returns ASCII text with CRLF line endings and soft line breaks (a trailing `=` on long lines) so no line exceeds 76 characters.

`decode(text: str | bytes) -> bytes` accepts either a `str` or `bytes` input, tolerates both CRLF and bare LF, collapses soft line breaks, and returns the original bytes.

## Why

Standard library `quopri` already exists, but its API mixes encoding and line-wrapping concerns in ways that surprise callers (for example, `quopri.encodestring` adds a trailing newline unconditionally). This library gives you two functions with clear contracts: `encode` never adds a spurious final newline, and `decode` is lenient about malformed `=XX` sequences rather than raising.

The deliberate trade-off is leniency on decode. A malformed escape such as `=GG` is passed through as the literal characters `=GG` instead of raising an error. This matches what most mail readers actually do and makes the decoder safe for partially-corrupted input, but it means you cannot use a decode error to detect damaged data.

## Edge cases

- Trailing whitespace on an encoded line (space or tab before the line break) is always escaped as `=20` or `=09`, because transports may strip trailing whitespace.
- The `=` character itself is encoded as `=3D`.
- Bare `=` at the end of a line is treated as a soft line break and removed during decode.
- `decode` accepts `bytes` input by interpreting it as latin-1 so every byte round-trips; this is convenient when the quoted-printable text arrived as bytes.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

