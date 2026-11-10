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

    def test_oil_is_not_given_a_temperature_grade(self):
        # The form offers Oil-23 and Oil-37, but no image file says which was
        # used, so filling either would record a guess.
        self.assertEqual(metadata_to_form_fields(COMMON_METADATA)["Immersion"], "Oil")

    def test_specialist_modes_fill_specialist_modality(self):
        mapped = metadata_to_form_fields({"Acquisition Modes": ["TotalInternalReflection"]})
        self.assertEqual(mapped, {"Specialist modality": "TIRF"})

    def test_images_with_different_settings_are_all_reported(self):
        # A LIF project often holds an overview and the real images, taken
        # with different objectives. Neither may be dropped from the record.
        overview = {"Image Name": "Overview", "Objective Model": "10x", "Size Z": 1, "System Name": "SP8"}
        stack = {"Image Name": "Stack", "Objective Model": "63x", "Size Z": 20, "System Name": "SP8"}
        images = [overview, dict(stack, **{"Image Name": "Stack 1"}), dict(stack, **{"Image Name": "Stack 2"})]

        combined = combine_image_metadata(images)
        self.assertEqual(combined["System Name"], "SP8")
        self.assertEqual(combined["Objective Model"], "63x [Stack 1, Stack 2]; 10x [Overview]")
        self.assertEqual(combined["Image Count"], 3)

        merged = merge_form_fields([metadata_to_form_fields(image) for image in images])
        self.assertEqual(merged, {"Microscope name": "SP8", "Objective": "63x; 10x", "Z-stack": "Both"})


if __name__ == "__main__":
    unittest.main()
