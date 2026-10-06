"""Quoted-printable encoder and decoder per RFC 2045.

Exports:
    encode -- encode bytes to ASCII quoted-printable text
    decode -- decode quoted-printable text to bytes
"""

from quoted_printable_decoder.core import decode, encode

__all__ = ["encode", "decode"]
