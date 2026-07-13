from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "post.schema.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "sample_posts.jsonl"


def load_fixture() -> list[dict]:
    return [json.loads(line) for line in FIXTURE_PATH.read_text().splitlines() if line.strip()]


class PostSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        cls.rows = load_fixture()

    def test_fixture_contains_exactly_twenty_valid_records(self) -> None:
        self.assertEqual(len(self.rows), 20)
        for row in self.rows:
            self.validator.validate(row)

    def test_fixture_ids_are_unique(self) -> None:
        ids = [row["post_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_fixture_covers_all_nine_labels(self) -> None:
        expected = set(self.schema["$defs"]["humanitarian_label"]["enum"])
        observed = {row["_lab2"]["reference_label"] for row in self.rows}
        self.assertEqual(observed, expected)

    def test_fixture_is_synthetic_and_has_no_raw_identifiers(self) -> None:
        long_number = re.compile(r"(?<!\d)\d{10,12}(?!\d)")
        for row in self.rows:
            self.assertEqual(row["source"], "synthetic_fixture")
            self.assertIsNone(row["time"])
            self.assertIsNone(row["location"])
            self.assertTrue(row["pii_redacted"])
            self.assertNotIn("@", row["text_clean"])
            self.assertIsNone(long_number.search(row["text_clean"]))

    def test_non_null_location_is_rejected(self) -> None:
        row = copy.deepcopy(self.rows[0])
        row["location"] = {"region": "invented"}
        with self.assertRaises(ValidationError):
            self.validator.validate(row)

    def test_numeric_post_id_is_rejected(self) -> None:
        row = copy.deepcopy(self.rows[0])
        row["post_id"] = 123
        with self.assertRaises(ValidationError):
            self.validator.validate(row)


if __name__ == "__main__":
    unittest.main()
