import unittest

from quoted_printable_decoder import decode, encode


class TestEncode(unittest.TestCase):
    def test_ascii_printable_passes_through(self):
        self.assertEqual(encode(b"Hello, World!"), "Hello, World!")

    def test_equals_is_encoded(self):
        self.assertEqual(encode(b"a=b"), "a=3Db")

    def test_high_bytes_encoded(self):
        self.assertEqual(encode(bytes([0xFF, 0x00, 0x7F])), "=FF=00=7F")

    def test_trailing_space_encoded(self):
        self.assertEqual(encode(b"hi "), "hi=20")
        self.assertEqual(encode(b"hi\t"), "hi=09")

    def test_soft_line_break_long_line(self):
        # 80 printable chars -> must wrap. Each line <= 76.
        data = b"A" * 80
        out = encode(data)
        self.assertEqual(out, "A" * 75 + "=\r\n" + "A" * 5)

    def test_newline_becomes_crlf(self):
        self.assertEqual(encode(b"line1\nline2"), "line1\r\nline2")

    def test_crlf_preserved_as_one_newline(self):
        self.assertEqual(encode(b"line1\r\nline2"), "line1\r\nline2")

    def test_empty(self):
        self.assertEqual(encode(b""), "")


class TestDecode(unittest.TestCase):
    def test_plain_ascii(self):
        self.assertEqual(decode("Hello, World!"), b"Hello, World!")

    def test_decode_equals(self):
        self.assertEqual(decode("a=3Db"), b"a=b")

    def test_decode_high_bytes(self):
        self.assertEqual(decode("=FF=00=7F"), bytes([0xFF, 0x00, 0x7F]))

    def test_decode_lowercase_hex(self):
        self.assertEqual(decode("=ff=3d"), bytes([0xFF, 0x3D]))

    def test_soft_line_break_collapsed(self):
        self.assertEqual(decode("foo=\r\nbar"), b"foobar")

    def test_soft_break_bare_lf(self):
        self.assertEqual(decode("foo=\nbar"), b"foobar")

    def test_malformed_escape_passed_through(self):
        # '=G' is not hex; lenient decode yields literal '='.
        self.assertEqual(decode("a=GZ"), b"a=GZ")

    def test_lone_equals_at_end(self):
        self.assertEqual(decode("abc="), b"abc")

    def test_decode_bytes_input(self):
        self.assertEqual(decode(b"a=3Db"), b"a=b")

    def test_round_trip(self):
        for data in [b"", b"hello", b"=test", b"\xff\x00\x7f", b"line1\nline2"]:
            self.assertEqual(decode(encode(data)), data)

    def test_trailing_space_round_trip(self):
        self.assertEqual(decode(encode(b"hi ")), b"hi ")


if __name__ == "__main__":
    unittest.main()
