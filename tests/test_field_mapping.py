import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors._common import most_common_metadata
from metadata_extractors.field_mapping import metadata_to_form_fields
from metadata_extractors.Nd2_v2a import map_nd2_to_remind_fields
from remind import FORM_FIELDS

# One value for every key the mappers read.
COMMON_METADATA = {
    "Document Creation Date": "2026-06-02T10:00:00",
    "System Name": "LSM 980",
    "Objective Model": "Plan-Apochromat 63x/1.4",
    "Objective Medium": "OIL",
    "Acquisition Modes": ["LaserScanningConfocalMicroscopy", "LaserScanningConfocalMicroscopy"],
    "Channel Names": ["DAPI", "GFP"],
    "Size Z": 12,
    "Size T": 1,
}
ND2_METADATA = {
    "Document Creation Date": "2/06/2026 10:00:00 AM",
    "System Name": "Ti2",
    "Objective Model": "Plan Apo",
    "Objective Magnification": "60.0",
    "Objective NA": "1.4",
    "Objective Medium": "1.515",
    "Modality": "Widefield",
    "Channel Names": ["DAPI", "GFP"],
    "Z Slices": "12",
    "Time Points": "1",
}


class FieldMappingTest(unittest.TestCase):
    def test_mappers_only_return_fields_the_form_has(self):
        # The form silently ignores labels it does not have, so a label that
        # drifts from the form's (e.g. "Z stack" for "Z-stack") would stop a
        # field being filled without any error.
        options = {label: choices for label, choices, _ in FORM_FIELDS}
        for mapped in (metadata_to_form_fields(COMMON_METADATA),
                       map_nd2_to_remind_fields(ND2_METADATA)):
            self.assertEqual(len(mapped), 8, mapped)
            self.assertLessEqual(set(mapped), set(options))
            for label in ("Z-stack", "Time series"):
                self.assertIn(mapped[label], options[label])

    def test_missing_values_are_left_out(self):
        # A returned field overwrites what the user typed, so "no value" must
        # never come back as text such as "N/A".
        metadata = {
            "Document Creation Date": "N/A",
            "System Name": None,
            "Objective Model": "",
            "Objective Medium": "N/A",
            "Acquisition Modes": ["N/A"],
            "Channel Names": ["N/A"],
        }
        self.assertEqual(metadata_to_form_fields(metadata), {})
        self.assertEqual(
            map_nd2_to_remind_fields({"Objective Medium": "N/A", "Channel Names": ["N/A"],
                                      "Z Slices": "3", "Time Points": "1"}),
            {"Z-stack": "Yes", "Time series": "No"},
        )

    def test_oil_is_not_given_a_temperature_grade(self):
        # The form offers Oil-23 and Oil-37, but no image file says which was
        # used, so filling either would record a guess.
        self.assertEqual(metadata_to_form_fields(COMMON_METADATA)["Immersion"], "Oil")
        self.assertEqual(map_nd2_to_remind_fields(ND2_METADATA)["Immersion"], "Oil")

    def test_most_common_value_wins_over_first_image(self):
        overview = {"Objective Model": "10x", "Channel Names": ["BF"]}
        image = {"Objective Model": "63x", "Channel Names": ["DAPI", "GFP"]}
        self.assertEqual(most_common_metadata([overview, image, image]), image)


if __name__ == "__main__":
    unittest.main()
