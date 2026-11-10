"""
Extract metadata from Zeiss CZI files using the czifile library.
Returns key image, instrument, and channel metadata as a dictionary using the
same vocabulary as the other ReMInD extractors.
"""

import os

from czifile import CziFile


def _text(element, path, default="N/A"):
    """Return the text of the element at path below element, or default if
    there is no such element or it is empty."""
    found = element.findtext(path) if element is not None else None
    return found.strip() if found and found.strip() else default


def _number(value, scale=1, decimals=3):
    """Return value times scale as a rounded number, or "N/A" if it is not
    a number."""
    try:
        return round(float(value) * scale, decimals)
    except (TypeError, ValueError):
        return "N/A"


def _count(value):
    """Return a dimension size as an int. CZI leaves a dimension out when it
    has a single plane, time point, scene or tile, so a missing size is 1."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 1


def _system_name(information, metadata):
    """Return the microscope system name, falling back to the name of the
    microscope device in the hardware configuration."""
    name = _text(information, "Instrument/Microscopes/Microscope/System", default="")
    if name:
        return name
    named = [d for d in metadata.findall("HardwareSetting/Configuration/Device") if d.get("Name")]
    microscope = [d for d in named if d.get("Id") == "Microscope"]
    return (microscope or named)[0].get("Name") if named else "N/A"


def _detector_for(channel_name, detectors):
    """Return the detector that recorded a channel, or None if none matches.
    Detector and channel names are not always identical (e.g. "ChA" and
    "ChA-T1"), so one containing the other counts as a match."""
    for detector in detectors:
        name = _text(detector, "ImageChannelName", default="")
        if name and (name in channel_name or channel_name in name):
            return detector
    return None


def _detection_range(detector):
    """Return a detector's detection band as "start-end" in nm, or "N/A"."""
    if detector is None:
        return "N/A"
    # An Airyscan detector records the name of its filter set instead.
    filter_set = _text(detector, "Filtersets/Filterset", default="")
    if detector.get("Name") == "Airyscan" and filter_set:
        return filter_set
    band = "DetectorWavelengthRanges/DetectorWavelengthRange/"
    start = _number(_text(detector, band + "WavelengthStart"), 1e9, 0)
    end = _number(_text(detector, band + "WavelengthEnd"), 1e9, 0)
    return f"{int(start)}-{int(end)}" if "N/A" not in (start, end) else "N/A"


def extract_czi_metadata(file_path):
    """
    Extract metadata from a Zeiss CZI file.

    Args:
        file_path (str): path to the .czi file.

    Returns:
        dict: the metadata. A value the file does not record is "N/A". The
        per-channel values are lists with one entry per channel, in file
        order; they are empty lists if the file describes no channels.
        Lengths are in micrometres and wavelengths in nanometres. "Size Z",
        "Size T", "Size S" and "Size M" are 1 when the file has no such
        dimension.

    Raises:
        Exception: if czifile cannot read the file.
    """
    with CziFile(file_path) as czi:
        metadata = czi.xml_element.find("Metadata")

    information = metadata.find("Information")
    image = information.find("Image") if information is not None else None
    channels = image.findall("Dimensions/Channels/Channel") if image is not None else []
    objective = information.find("Instrument/Objectives/Objective") if information is not None else None
    blocks = metadata.findall("Experiment/ExperimentBlocks/AcquisitionBlock")
    first_block = blocks[0] if blocks else None
    detectors = [detector for block in blocks
                 for detector in block.findall("MultiTrackSetup/TrackSetup/Detectors/Detector")]

    # Pixel sizes are stored in metres. A laser scanning system records them
    # with the acquisition settings; every file has them under Scaling.
    scaling = {d.get("Id"): _text(d, "Value") for d in metadata.findall("Scaling/Items/Distance")}
    sizes = {axis: _count(_text(image, f"Size{axis}")) for axis in "XYZTSM"}
    pixel_size, image_size = {}, {}
    for axis in "XYZ":
        value = _number(_text(first_block, f"AcquisitionModeSetup/Scaling{axis}"), 1e6)
        if value in ("N/A", 0):
            value = _number(scaling.get(axis), 1e6)
        if axis == "Z" and sizes["Z"] == 1:
            value = "N/A"  # the file gives a Z step even for a single plane
        pixel_size[axis] = value
        image_size[axis] = _number(sizes[axis] * value) if value != "N/A" else "N/A"

    names = [channel.get("Name", "N/A") for channel in channels]
    channel_detectors = [_detector_for(name, detectors) for name in names]

    def per_channel(path, scale=1):
        return [_number(_text(channel, path), scale) for channel in channels]

    return {
        "Document Name": _text(information, "Document/Name",
                               default=os.path.splitext(os.path.basename(file_path))[0]),
        "Document Creation Date": _text(information, "Document/CreationDate"),
        "Application Name": _text(information, "Application/Name"),
        "Application Version": _text(information, "Application/Version"),
        "System Name": _system_name(information, metadata),
        "Pixel Type": _text(image, "PixelType"),
        "Size X": sizes["X"],
        "Size Y": sizes["Y"],
        "Size Z": sizes["Z"],
        "Size M": sizes["M"],
        "Size T": sizes["T"],
        "Size C": len(channels),
        "Size S": sizes["S"],
        "Pixel Size X (um)": pixel_size["X"],
        "Pixel Size Y (um)": pixel_size["Y"],
        "Pixel Size Z (um)": pixel_size["Z"],
        "Image Size X (um)": image_size["X"],
        "Image Size Y (um)": image_size["Y"],
        "Image Size Z (um)": image_size["Z"],
        "Time Interval (s)": _number(_text(
            first_block, "SubDimensionSetups/TimeSeriesSetup/Interval/TimeSpan/Value")),
        "Objective Model": _text(objective, "Manufacturer/Model"),
        "Objective NA": _number(_text(objective, "LensNA")),
        "Objective Magnification": _number(_text(objective, "NominalMagnification")),
        "Objective Refractive Index": _number(_text(image, "ObjectiveSettings/RefractiveIndex")),
        "Objective Medium": _text(image, "ObjectiveSettings/Medium"),
        "Illumination Types": [_text(channel, "IlluminationType") for channel in channels],
        "Contrast Methods": [_text(channel, "ContrastMethod") for channel in channels],
        "Acquisition Modes": [_text(channel, "AcquisitionMode") for channel in channels],
        "Channel Names": names,
        "Dye Names": [_text(channel, "Fluor") for channel in channels],
        "Excitation Wavelengths": per_channel("ExcitationWavelength"),
        "Emission Wavelengths": per_channel("EmissionWavelength"),
        "Emission Wavelength Range (nm)": [_detection_range(d) for d in channel_detectors],
        "Pinhole Sizes (Airy Units)": per_channel("PinholeSizeAiry"),
        "Pinhole Diameters (um)": [_number(_text(d, "PinholeDiameter"), 1e6) for d in channel_detectors],
        "AiryScan Virtual Pinhole Size (um)": [
            _number(_text(d, "AiryScanVirtualPinholeSize"), 1e6)
            if d is not None and d.get("Name") == "Airyscan" else "N/A"
            for d in channel_detectors],
        "Zoom": per_channel("LaserScanInfo/ZoomX"),
        "Total Magnification": per_channel("CustomAttributes/MM.TotalMagnification"),
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python czi_metadata.py <file.czi>")
    else:
        print(json.dumps(extract_czi_metadata(sys.argv[1]), indent=2))
