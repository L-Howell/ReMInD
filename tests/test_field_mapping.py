import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors._common import combine_image_metadata
from metadata_extractors.field_mapping import merge_form_fields, metadata_to_form_fields

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

class FieldMappingTest(unittest.TestCase):
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

    def test_channels_are_written_as_excitation_and_target(self):
        metadata = {
            "Channel Names": ["CH1", "CH2", "T PMT"],
            "Dye Names": ["DAPI", "N/A", "N/A"],
            "Excitation Wavelengths": [405.0, 561.4, "N/A"],
        }
        self.assertEqual(metadata_to_form_fields(metadata),
                         {"Channel info": "405 (DAPI), 561 (CH2), T PMT"})

    def test_images_with_different_settings_are_all_reported(self):
        # A LIF project often holds an overview and the real images, taken
        # with different objectives. Neither may be dropped from the record.
        overview = {"Image Name": "Overview", "Objective Model": "10x", "Size Z": 1, "System Name": "SP8"}
        stack = {"Image Name": "Stack", "Objective Model": "63x", "Size Z": 20, "System Name": "SP8"}
        images = [overview, dict(stack, **{"Image Name": "Stack 1"}), dict(stack, **{"Image Name": "Stack 2"})]

        combined = combine_image_metadata(images)
        self.assertEqual(combined["System Name"], "SP8")
        for text in ("63x", "10x", "Stack 1", "Stack 2", "Overview"):
            self.assertIn(text, combined["Objective Model"])

        merged = merge_form_fields([metadata_to_form_fields(image) for image in images])
        self.assertEqual(merged["Microscope name"], "SP8")
        self.assertIn("63x", merged["Objective"])
        self.assertIn("10x", merged["Objective"])
        self.assertEqual(merged["Z-stack"], "Both")


if __name__ == "__main__":
    unittest.main()
