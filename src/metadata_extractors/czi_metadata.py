"""
Extract metadata from Zeiss CZI files using the pylibCZIrw library.
Returns key image, instrument, and channel metadata as a dictionary using the
same vocabulary as the other ReMInD extractors.
"""

import os

from pylibCZIrw import czi as pyczi


def _get(mapping, *keys, default="N/A"):
    """Follow keys into nested dicts; return default if any step is missing
    or is not a dict."""
    for key in keys:
        if not isinstance(mapping, dict) or key not in mapping:
            return default
        mapping = mapping[key]
    return mapping


def _as_list(value):
    """Return value as a list. The metadata holds a single dict where there
    is one item and a list where there are several."""
    if isinstance(value, list):
        return value
    return [value] if isinstance(value, dict) else []


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


def _system_name(information, hardware):
    """Return the microscope system name, falling back to the name of the
    microscope device in the hardware configuration."""
    name = _get(information, "Instrument", "Microscopes", "Microscope", "System", default="")
    if name:
        return name
    devices = _as_list(_get(hardware, "Configuration", "Device", default=[]))
    named = [d for d in devices if d.get("@Name")]
    microscope = [d for d in named if d.get("@Id") == "Microscope"]
    return (microscope or named or [{"@Name": "N/A"}])[0]["@Name"]


def _detector_for(channel_name, detectors):
    """Return the detector that recorded a channel, or {} if none matches.
    Detector and channel names are not always identical (e.g. "ChA" and
    "ChA-T1"), so one containing the other counts as a match."""
    for detector in detectors:
        name = detector.get("ImageChannelName") or ""
        if name and (name in channel_name or channel_name in name):
            return detector
    return {}


def _detection_range(detector):
    """Return a detector's detection band as "start-end" in nm, or "N/A"."""
    # An Airyscan detector records the name of its filter set instead.
    if detector.get("@Name") == "Airyscan" and _get(detector, "Filtersets", "Filterset", default=None):
        return _get(detector, "Filtersets", "Filterset")
    band = _get(detector, "DetectorWavelengthRanges", "DetectorWavelengthRange", default={})
    start = _number(_get(band, "WavelengthStart"), 1e9, 0)
    end = _number(_get(band, "WavelengthEnd"), 1e9, 0)
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
        Exception: if pylibCZIrw cannot read the file.
    """
    with pyczi.open_czi(file_path) as document:
        metadata = _get(document.metadata, "ImageDocument", "Metadata", default={})

    information = _get(metadata, "Information", default={})
    image = _get(information, "Image", default={})
    channels = _as_list(_get(image, "Dimensions", "Channels", "Channel", default=[]))
    objective = _get(information, "Instrument", "Objectives", "Objective", default={})
    blocks = _as_list(_get(metadata, "Experiment", "ExperimentBlocks", "AcquisitionBlock", default=[]))
    first_block = blocks[0] if blocks else {}
    detectors = [detector
                 for block in blocks
                 for track in _as_list(_get(block, "MultiTrackSetup", "TrackSetup", default=[]))
                 for detector in _as_list(_get(track, "Detectors", "Detector", default=[]))]

    # Pixel sizes are stored in metres. A laser scanning system records them
    # with the acquisition settings; every file has them under Scaling.
    scaling = {d.get("@Id"): d.get("Value")
               for d in _as_list(_get(metadata, "Scaling", "Items", "Distance", default=[]))}
    sizes = {axis: _count(image.get(f"Size{axis}")) for axis in "XYZTSM"}
    pixel_size, image_size = {}, {}
    for axis in "XYZ":
        value = _number(_get(first_block, "AcquisitionModeSetup", f"Scaling{axis}"), 1e6)
        if value in ("N/A", 0):
            value = _number(scaling.get(axis), 1e6)
        if axis == "Z" and sizes["Z"] == 1:
            value = "N/A"  # the file gives a Z step even for a single plane
        pixel_size[axis] = value
        image_size[axis] = _number(sizes[axis] * value) if value != "N/A" else "N/A"

    names = [channel.get("@Name", "N/A") for channel in channels]
    channel_detectors = [_detector_for(name, detectors) for name in names]

    def per_channel(key, scale=1):
        return [_number(channel.get(key), scale) for channel in channels]

    return {
        "Document Name": _get(information, "Document", "Name",
                              default=os.path.splitext(os.path.basename(file_path))[0]),
        "Document Creation Date": _get(information, "Document", "CreationDate"),
        "Application Name": _get(information, "Application", "Name"),
        "Application Version": _get(information, "Application", "Version"),
        "System Name": _system_name(information, _get(metadata, "HardwareSetting", default={})),
        "Pixel Type": image.get("PixelType", "N/A"),
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
        "Time Interval (s)": _number(_get(first_block, "SubDimensionSetups", "TimeSeriesSetup",
                                          "Interval", "TimeSpan", "Value")),
        "Objective Model": _get(objective, "Manufacturer", "Model"),
        "Objective NA": _number(objective.get("LensNA")),
        "Objective Magnification": _number(objective.get("NominalMagnification")),
        "Objective Refractive Index": _number(_get(image, "ObjectiveSettings", "RefractiveIndex")),
        "Objective Medium": _get(image, "ObjectiveSettings", "Medium"),
        "Illumination Types": [channel.get("IlluminationType", "N/A") for channel in channels],
        "Contrast Methods": [channel.get("ContrastMethod", "N/A") for channel in channels],
        "Acquisition Modes": [channel.get("AcquisitionMode", "N/A") for channel in channels],
        "Channel Names": names,
        "Dye Names": [channel.get("Fluor", "N/A") for channel in channels],
        "Excitation Wavelengths": per_channel("ExcitationWavelength"),
        "Emission Wavelengths": per_channel("EmissionWavelength"),
        "Emission Wavelength Range (nm)": [_detection_range(d) for d in channel_detectors],
        "Pinhole Sizes (Airy Units)": per_channel("PinholeSizeAiry"),
        "Pinhole Diameters (um)": [_number(d.get("PinholeDiameter"), 1e6) for d in channel_detectors],
        "AiryScan Virtual Pinhole Size (um)": [
            _number(d.get("AiryScanVirtualPinholeSize"), 1e6) if d.get("@Name") == "Airyscan" else "N/A"
            for d in channel_detectors],
        "Zoom": [_number(_get(channel, "LaserScanInfo", "ZoomX")) for channel in channels],
        "Total Magnification": [_number(_get(channel, "CustomAttributes", "MM.TotalMagnification"))
                                for channel in channels],
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python czi_metadata.py <file.czi>")
    else:
        print(json.dumps(extract_czi_metadata(sys.argv[1]), indent=2))
