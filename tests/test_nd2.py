import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors.nd2_metadata import _acquisition_date, _lines_on

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

    def test_day_and_month_order_is_settled_by_the_julian_day(self):
        # NIS-Elements writes the date in the format of its computer, so the
        # same text is 6 March on one microscope and 3 June on another.
        march_6 = 2454897.16  # 2009-03-06 15:50 UTC
        self.assertEqual(_acquisition_date("06/03/2009 10:56:46 AM", march_6), "2009-03-06 10:56:46")
        self.assertEqual(_acquisition_date("3/6/2009 10:56:46 AM", march_6), "2009-03-06 10:56:46")
        self.assertEqual(_acquisition_date("29/12/2010 12:13:08", None), "2010-12-29 12:13:08")
        # Without the Julian day a guess would be wrong half the time.
        self.assertEqual(_acquisition_date("06/03/2009 10:56:46 AM", None), "06/03/2009 10:56:46 AM")


if __name__ == "__main__":
    unittest.main()
