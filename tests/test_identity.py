import unittest

from identity import _meaningful_name, _resolve_display_name


def name_claim(value):
    return {"typ": "name", "val": value}


def given_claim(value):
    return {"typ": "given_name", "val": value}


class MeaningfulNameTests(unittest.TestCase):
    def test_real_name_is_kept(self):
        self.assertEqual(_meaningful_name("Danielle Carter"), "Danielle Carter")

    def test_whitespace_is_trimmed(self):
        self.assertEqual(_meaningful_name("  Pete  "), "Pete")

    def test_blank_is_none(self):
        self.assertIsNone(_meaningful_name(""))
        self.assertIsNone(_meaningful_name("   "))
        self.assertIsNone(_meaningful_name(None))

    def test_placeholders_are_none_any_case(self):
        for placeholder in [
            "unknown",
            "Unknown",
            "UNKNOWN",
            "unknownuser",
            "Unknown User",
        ]:
            self.assertIsNone(_meaningful_name(placeholder))


class ResolveDisplayNameTests(unittest.TestCase):
    def test_prefers_real_name_claim(self):
        claims = [name_claim("Danielle Carter"), given_claim("Danielle")]
        self.assertEqual(
            _resolve_display_name(claims, "danielle@example.com"),
            "Danielle Carter",
        )

    def test_unknown_name_falls_back_to_given_name(self):
        claims = [name_claim("unknown"), given_claim("Danielle")]
        self.assertEqual(
            _resolve_display_name(claims, "danielle@example.com"),
            "Danielle",
        )

    def test_falls_back_to_email_local_part(self):
        claims = [name_claim("unknownuser")]
        self.assertEqual(
            _resolve_display_name(claims, "pete.carter@example.com"),
            "pete.carter",
        )

    def test_returns_none_when_nothing_usable(self):
        claims = [name_claim("unknown")]
        self.assertIsNone(_resolve_display_name(claims, None))

    def test_no_name_claims_at_all_uses_email(self):
        self.assertEqual(
            _resolve_display_name([], "member@example.com"),
            "member",
        )


if __name__ == "__main__":
    unittest.main()
