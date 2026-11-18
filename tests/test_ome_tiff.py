import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors._common import parse_xml
from metadata_extractors.ome_tiff_metadata import _image_metadata

# OME-XML as stored in an OME-TIFF, cut down to the parts the extractor reads.
OME_XML = """
<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">
  <Instrument ID="Instrument:0">
    <Microscope Model="LSM 980"/>
    <Objective ID="Objective:0" Model="Plan-Apochromat" LensNA="1.4" NominalMagnification="63.0" Immersion="Oil"/>
    <Objective ID="Objective:1" Model="EC Plan-Neofluar" LensNA="0.3" NominalMagnification="10.0" Immersion="Air"/>
  </Instrument>
  <Image ID="Image:0" Name="Overview">
    <InstrumentRef ID="Instrument:0"/>
    <ObjectiveSettings ID="Objective:1"/>
    <Pixels SizeX="64" SizeY="48" SizeZ="1" SizeC="1" SizeT="1" Type="uint16"
            PhysicalSizeX="1300" PhysicalSizeXUnit="nm" PhysicalSizeY="1.3">
      <Channel ID="Channel:0:0" Name="Ch1" Fluor="DAPI" ExcitationWavelength="405.0"/>
    </Pixels>
  </Image>
</OME>
"""


class OmeTiffTest(unittest.TestCase):
    def setUp(self):
        root = parse_xml(OME_XML)
        self.metadata = _image_metadata(root, root.find("Image"))

    def test_objective_matches_image_reference(self):
        # The file's first objective is the 63x. This image refers to the 10x.
        self.assertEqual(self.metadata["Objective Model"], "EC Plan-Neofluar 10x NA 0.3")
        self.assertEqual(self.metadata["Objective Medium"], "Air")

    def test_pixel_sizes_converted_to_micrometres(self):
        # A pixel size is in the unit the file gives, micrometres by default.
        self.assertEqual(self.metadata["Pixel Size X (um)"], 1.3)
        self.assertEqual(self.metadata["Pixel Size Y (um)"], 1.3)


if __name__ == "__main__":
    unittest.main()
