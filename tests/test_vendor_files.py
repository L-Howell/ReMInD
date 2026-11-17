"""
Each extractor read against real files from the vendor's own software.

tests/data/vendor_formats holds one folder per software version, each with a
single plane (2d), a time series (2d_t), a Z-stack (3d) and both (3d_t).
"""

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors.field_mapping import metadata_to_form_fields

DATA = os.path.join(os.path.dirname(__file__), "data", "vendor_formats")
SHAPES = {"2d": ("No", "No"), "2d_t": ("No", "Yes"), "3d": ("Yes", "No"), "3d_t": ("Yes", "Yes")}
LIBRARIES = {"CZI": "czifile", "LIF": "liffile", "ND2": "nd2", "OIR": "oirfile"}

# The form fields every file of a version fills, apart from Date and time,
# Z-stack and Time series.
VERSIONS = {
    "CZI/zen-2.6.76": {
        "Microscope name": "LSM 800", "Objective": "Plan-Apochromat 10x/0.45 M27",
        "Immersion": "Air", "Imaging mode": "Confocal",
        "Channel info": "488 (Alexa Fluor 488), 405 (DAPI)"},
    "LIF/lasx-4.9.2.31016": {
        "Microscope name": "STELLARIS 8", "Objective": "HC PL APO CS2 10x/0.40 DRY",
        "Immersion": "Air", "Imaging mode": "Confocal",
        "Channel info": "405 (DAPI), 499 (ALEXA 488)"},
    "ND2/nis-elements-5.30.07": {
        "Objective": "Plan Apo 10x DIC N1", "Immersion": "Air", "Imaging mode": "Widefield",
        "Channel info": "475 (Spectra-GFP), 390 (Spectra-DAPI)"},
    "OIR/fv4000-fv5000-4.1.1.137": {
        "Microscope name": "FV4000/FV5000", "Objective": "UPLXAPO20X 20x NA 0.8",
        "Immersion": "Air", "Imaging mode": "Confocal",
        "Channel info": "405 (CH1), 488 (CH2), 640 (CH3)"},
}


def installed(fmt):
    return importlib.util.find_spec(LIBRARIES[fmt]) is not None


def extract(version, shape):
    from metadata_extractors import czi_metadata, lif_metadata, nd2_metadata, oir_metadata
    fmt = version.split("/")[0]
    path = os.path.join(DATA, version, f"{shape}.{fmt.lower()}")
    if fmt == "LIF":
        return lif_metadata.extract_lif_metadata(path)[0]
    return {"CZI": czi_metadata.extract_czi_metadata, "ND2": nd2_metadata.extract_nd2_metadata,
            "OIR": oir_metadata.extract_oir_metadata}[fmt](path)


class VendorFileTest(unittest.TestCase):
    def test_form_fields(self):
        for version, expected in VERSIONS.items():
            if not installed(version.split("/")[0]):
                continue
            for shape, (z_stack, time_series) in SHAPES.items():
                with self.subTest(file=f"{version}/{shape}"):
                    fields = metadata_to_form_fields(extract(version, shape))
                    self.assertEqual({key: fields.get(key) for key in expected}, expected)
                    self.assertEqual(fields["Z-stack"], z_stack)
                    self.assertEqual(fields["Time series"], time_series)

    @unittest.skipUnless(installed("CZI"), "czifile is not installed")
    def test_czi_channel_settings_without_acquisition_block_detectors(self):
        metadata = extract("CZI/zen-2.6.76", "2d")
        self.assertEqual(metadata["Emission Wavelength Range (nm)"], ["510-700", "400-510"])
        self.assertEqual(metadata["Pinhole Diameters (um)"], [159.99, 159.99])

    @unittest.skipUnless(installed("LIF"), "liffile is not installed")
    def test_lif_detection_bands_in_a_sequential_scan(self):
        self.assertEqual(extract("LIF/lasx-4.9.2.31016", "2d")["Emission Wavelength Range (nm)"],
                         ["430-469", "506-575"])


if __name__ == "__main__":
    unittest.main()
