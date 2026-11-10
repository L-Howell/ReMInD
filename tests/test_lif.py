import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_extractors.LIF_MetadataGUI import _image_elements, _image_metadata

# Two images in one project, in the layout LAS X writes, cut down to the
# parts the extractor reads.
PROJECT = """
<LMSDataContainerHeader><Element Name="Project"><Children>
  <Element Name="Overview"><Data><Image>
    <Attachment Name="HardwareSetting" SystemTypeName="STELLARIS 5" DataSourceTypeName="Confocal">
      <ATLConfocalSettingDefinition ObjectiveName="HC PL APO  20x/0.75 IMM" Immersion="IMM"
          NumericalAperture="0.75" Magnification="20" RefractionIndex="1.518">
        <DetectorList><Detector Name="HyD S 1" Channel="1" IsActive="1" DyeName="Leica/DAPI."/></DetectorList>
        <AotfList><Aotf><LaserLineSetting LaserLine="405" IntensityDev="2"/>
                        <LaserLineSetting LaserLine="488" IntensityDev="0"/></Aotf></AotfList>
      </ATLConfocalSettingDefinition>
    </Attachment>
    <ImageDescription>
      <Channels><ChannelDescription LUTName="Blue"/></Channels>
      <Dimensions>
        <DimensionDescription DimID="1" NumberOfElements="101" Length="1.0e-03"/>
        <DimensionDescription DimID="2" NumberOfElements="101" Length="1.0e-03"/>
      </Dimensions>
    </ImageDescription>
  </Image></Data></Element>
  <Element Name="Stack"><Data><Image>
    <Attachment Name="HardwareSetting" SystemTypeName="STELLARIS 5" DataSourceTypeName="Confocal">
      <ATLConfocalSettingDefinition ObjectiveName="HC PL APO  63x/1.40 OIL" Immersion="OIL"
          NumericalAperture="1.4" Magnification="63">
        <DetectorList><Detector Name="HyD S 1" Channel="1" IsActive="1" DyeName="Leica/DAPI."/>
                      <Detector Name="HyD S 2" Channel="2" IsActive="1" DyeName=""/>
                      <Detector Name="HyD S 3" Channel="3" IsActive="0" DyeName=""/></DetectorList>
        <AotfList><Aotf><LaserLineSetting LaserLine="405" IntensityDev="2"/>
                        <LaserLineSetting LaserLine="488" IntensityDev="5"/></Aotf></AotfList>
      </ATLConfocalSettingDefinition>
    </Attachment>
    <ImageDescription>
      <Channels><ChannelDescription LUTName="Blue"/><ChannelDescription LUTName="Green"/></Channels>
      <Dimensions>
        <DimensionDescription DimID="1" NumberOfElements="101" Length="1.0e-04"/>
        <DimensionDescription DimID="2" NumberOfElements="101" Length="1.0e-04"/>
        <DimensionDescription DimID="3" NumberOfElements="11" Length="5.0e-06"/>
      </Dimensions>
    </ImageDescription>
  </Image></Data></Element>
</Children></Element></LMSDataContainerHeader>
"""


class LifTest(unittest.TestCase):
    def test_each_image_reports_its_own_settings(self):
        # Values used to be looked up across the whole file, so every image
        # was given the first image's objective and all images' channels.
        overview, stack = [_image_metadata(e) for e in _image_elements(ET.fromstring(PROJECT))]

        self.assertEqual(overview["Objective Model"], "HC PL APO 20x/0.75 IMM")
        # The refractive index is not taken as proof of the medium used.
        self.assertEqual(overview["Objective Medium"], "Multi-immersion")
        self.assertEqual(overview["Dye Names"], ["DAPI"])
        self.assertEqual(overview["Excitation Wavelengths"], ["405"])
        self.assertEqual(overview["Size Z"], 1)
        self.assertEqual(overview["Pixel Size X (um)"], 10)

        self.assertEqual(stack["Objective Model"], "HC PL APO 63x/1.40 OIL")
        self.assertEqual(stack["Objective Medium"], "Oil")
        self.assertEqual(stack["Channel Names"], ["HyD S 1", "HyD S 2"])
        self.assertEqual(stack["Dye Names"], ["DAPI", "N/A"])
        # Two lasers in one scan: the file does not say which detector saw which.
        self.assertEqual(stack["Excitation Wavelengths"], ["N/A", "N/A"])
        self.assertEqual(stack["Laser Lines (nm)"], ["405", "488"])
        self.assertEqual(stack["Size Z"], 11)
        self.assertEqual(stack["Pixel Size Z (um)"], 0.5)


if __name__ == "__main__":
    unittest.main()
