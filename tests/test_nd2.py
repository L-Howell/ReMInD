import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors.Nd2_v2a import _lines_on

# Acquisition settings text as NIS-Elements writes it for two channels.
DESCRIPTION = """Metadata:
Dimensions: λ(2)
Plane #1:
 Name: Confocal Green BP
 Modality: Widefield Fluorescence
 Microscope Settings:   Microscope: Ti Microscope
  NIDAQ, MultiLaser(AOTF):
     Line:1; ExW:405; Off
     Line:2; ExW:488; Power: 12.0; On
     Line:3; ExW:561; Off
Plane #2:
 Name: Confocal Red BP
 Modality: Widefield Fluorescence
  NIDAQ, MultiLaser(AOTF):
     Line:1; ExW:405; Off
     Line:2; ExW:488; Power: 12.0; Off
     Line:3; ExW:561; Power: 30.0; On; ND:0
"""


class Nd2Test(unittest.TestCase):
    def test_laser_lines_switched_on_are_read_per_channel(self):
        # The nd2 library reports no excitation wavelength for laser systems;
        # this text is the only place the file records which line was used.
        self.assertEqual(_lines_on(DESCRIPTION), [["488"], ["561"]])


if __name__ == "__main__":
    unittest.main()
