"""
Extract metadata from Leica LIF files using the liffile library.

A LIF file is a container: it can hold many images, each acquired with its
own objective, channels and scan settings. Every value is therefore read
from the XML of the image it belongs to, and one dict is returned per image.

Two layouts of the hardware settings are understood: the "HardwareSetting"
block written by LAS X, and the older "HardwareSettingList" block written by
LAS AF. Values that an image does not record are reported as "N/A".
"""

import datetime

from liffile import LifFile

try:
    from ._common import immersion_term, imaging_mode_term
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term


# DimID values used by Leica for the spatial and time axes.
_AXES = {"1": "X", "2": "Y", "3": "Z", "4": "T"}


def _number(text, decimals=3):
    """Return text as a rounded number (an int when it is whole), or "N/A"
    if it is not a number."""
    try:
        value = round(float(text), decimals)
    except (TypeError, ValueError):
        return "N/A"
    return int(value) if value.is_integer() else value


def _local_time(timestamps):
    """
    Return the first of an image's time stamps as "YYYY-MM-DD HH:MM:SS" in
    the time zone of this computer, or "N/A" if there are none.

    Args:
        timestamps: the numpy array of UTC times liffile gives for an image,
            or None.
    """
    if timestamps is None or len(timestamps) == 0:
        return "N/A"
    utc = timestamps[0].astype("datetime64[s]").item().replace(tzinfo=datetime.timezone.utc)
    return utc.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _dimensions(image):
    """Return {axis: (number of elements, length)} for the X, Y, Z and T
    axes the image has. Lengths are in metres, or seconds for T."""
    dimensions = {}
    for d in image.findall("./ImageDescription/Dimensions/DimensionDescription"):
        axis = _AXES.get(d.get("DimID"))
        if axis:
            dimensions[axis] = (int(d.get("NumberOfElements")), float(d.get("Length") or 0))
    return dimensions


def _clean_dye(name):
    """Turn a dye name such as "Leica/HOECHST 33258." into "HOECHST 33258"."""
    return name.split("/", 1)[-1].strip(" .")


def _las_x_settings(hardware):
    """Read a LAS X "HardwareSetting" block."""
    definition = next((child for child in hardware if child.tag.endswith("SettingDefinition")), None)
    if definition is None:
        return {}

    # A sequential scan stores one settings block per sequence; the detectors
    # and laser lines in use are the ones recorded there.
    scans = hardware.findall("./LDM_Block_Sequential/LDM_Block_Sequential_List/*") or [definition]
    detectors, lasers_by_scan, bands = [], [], []
    for scan in scans:
        # Every line the laser offers is listed; the ones in use have power.
        lasers = [line.get("LaserLine") for line in scan.findall("./AotfList/Aotf/LaserLineSetting")
                  if float(line.get("IntensityDev") or 0) > 0]
        lasers_by_scan.append(lasers)
        ranges = {b.get("Channel"): (b.get("LeftWorld"), b.get("RightWorld"))
                  for b in scan.findall("./Spectro/MultiBand")}
        for detector in scan.findall("./DetectorList/Detector"):
            if detector.get("IsActive") != "1":
                continue
            dye = _clean_dye(detector.get("DyeName") or "")
            detectors.append((detector.get("Name") or "N/A", dye, lasers))
            low, high = ranges.get(detector.get("Channel"), (None, None))
            if low and high:
                bands.append(f"{round(float(low))}-{round(float(high))}")

    return {
        "software": hardware.get("Software"),
        "system": hardware.get("SystemTypeName"),
        "mode": hardware.get("DataSourceTypeName"),
        "microscope": definition.get("MicroscopeModel"),
        "scan mode": definition.get("ScanMode"),
        "objective": definition.get("ObjectiveName"),
        "na": definition.get("NumericalAperture"),
        "magnification": definition.get("Magnification"),
        "refractive index": definition.get("RefractionIndex"),
        "immersion": definition.get("Immersion"),
        "pinhole airy": definition.get("PinholeAiry"),
        "pinhole m": definition.get("Pinhole"),
        "zoom": definition.get("Zoom"),
        "detectors": detectors,
        "lasers by scan": lasers_by_scan,
        "bands": bands,
    }


def _las_af_settings(hardware_list):
    """Read a LAS AF "HardwareSettingList" block."""
    scanner = {r.get("Identifier"): r.get("Variant")
               for r in hardware_list.findall(".//ScannerSettingRecord")}
    filters = {(r.get("ClassName"), r.get("Attribute")): r.get("Variant")
               for r in hardware_list.findall(".//FilterSettingRecord")}
    detectors = [(r.get("ObjectName"), "", [])
                 for r in hardware_list.findall(".//FilterSettingRecord")
                 if r.get("ClassName") == "CDetectionUnit" and r.get("Attribute") == "State"
                 and r.get("Variant") == "Active"]
    return {
        "system": scanner.get("SystemType"),
        "scan mode": scanner.get("csScanMode"),
        "objective": filters.get(("CTurret", "Objective")),
        "na": filters.get(("CTurret", "NumericalAperture")),
        "refractive index": filters.get(("CTurret", "RefractionIndex")),
        "pinhole airy": scanner.get("dblPinholeAiry"),
        "pinhole m": scanner.get("dblPinhole"),
        "zoom": scanner.get("dblZoom"),
        "detectors": detectors,
    }


def _objective_medium(objective_name):
    """Return the immersion medium given in a Leica objective name such as
    "HCX PL APO CS 63.0x1.40 OIL UV", or "N/A" if the name gives none."""
    for word in (objective_name or "").split():
        if immersion_term(word) != word:
            return immersion_term(word)
    return "N/A"


def _channels(image, settings):
    """
    Describe the channels of an image.

    Returns:
        tuple: (names, dyes, excitation), each with one entry per channel.
          - names: the detector, or the display colour (e.g. "Green") when
            the detector is not known.
          - dyes: the dye set in LAS X, or "N/A".
          - excitation: the laser line in nm, or "N/A". The file lists the
            lasers used in each scan, not which laser goes with which
            detector, so a line is given only when its scan used one laser.
    """
    channels = image.findall("./ImageDescription/Channels/ChannelDescription")
    detectors = settings.get("detectors", [])
    lasers_by_scan = settings.get("lasers by scan", [])
    names, dyes, excitation = [], [], []
    for index, channel in enumerate(channels):
        properties = {p.findtext("Key"): p.findtext("Value") for p in channel.findall("ChannelProperty")}
        detector = properties.get("DetectorName") or ""
        dye = _clean_dye(properties.get("DyeName") or "")
        lasers = []
        if properties.get("SequentialSettingIndex", "").isdigit():
            scan = int(properties["SequentialSettingIndex"])
            lasers = lasers_by_scan[scan] if scan < len(lasers_by_scan) else []
        elif len(detectors) == len(channels):
            # Older files do not label the channels, but the active detectors
            # correspond to them when there are equally many of each.
            detector, dye, lasers = detectors[index]
        names.append(detector or channel.get("LUTName") or "N/A")
        dyes.append(dye or "N/A")
        excitation.append(lasers[0] if len(lasers) == 1 else "N/A")
    return names, dyes, excitation


def _image_metadata(element, name=None, timestamps=None):
    """
    Build the metadata dict for one image.

    Args:
        element: the image's XML element (liffile's LifImage.xml_element).
        name: the image's name, including any folders it is in. Defaults to
            the name in the XML.
        timestamps: the image's time stamps, for the acquisition date.
    """
    image = element.find("./Data/Image")
    attachments = {a.get("Name"): a for a in image.findall("Attachment")}
    if "HardwareSetting" in attachments:
        settings = _las_x_settings(attachments["HardwareSetting"])
    elif "HardwareSettingList" in attachments:
        settings = _las_af_settings(attachments["HardwareSettingList"])
    else:
        settings = {}

    def setting(key):
        value = settings.get(key)
        return " ".join(value.split()) if value and value.strip() else "N/A"

    medium = setting("immersion")
    if medium == "N/A":
        medium = _objective_medium(settings.get("objective"))

    names, dyes, excitation = _channels(image, settings)
    laser_lines = list(dict.fromkeys(line for lasers in settings.get("lasers by scan", []) for line in lasers))
    dimensions = _dimensions(image)
    metadata = {
        "Image Name": name or element.get("Name") or "N/A",
        "Document Creation Date": _local_time(timestamps),
        "Application Version": setting("software"),
        "System Name": setting("system"),
        "Microscope Model": setting("microscope"),
        "Acquisition Modes": imaging_mode_term(setting("mode")),
        "Scan Mode": setting("scan mode"),
        "Objective Model": setting("objective"),
        "Objective NA": _number(settings.get("na")),
        "Objective Magnification": _number(settings.get("magnification")),
        "Objective Refractive Index": _number(settings.get("refractive index")),
        "Objective Medium": immersion_term(medium),
        "Channel Names": names,
        "Dye Names": dyes,
        "Excitation Wavelengths": excitation,
        "Laser Lines (nm)": laser_lines or ["N/A"],
        "Emission Wavelength Range (nm)": settings.get("bands") or ["N/A"],
        "Pinhole Size (Airy Units)": _number(settings.get("pinhole airy")),
        "Pinhole Diameter (um)": _number(float(settings["pinhole m"]) * 1e6)
                                 if settings.get("pinhole m") else "N/A",
        "Zoom": _number(settings.get("zoom")),
    }

    for axis in "XYZT":
        metadata[f"Size {axis}"] = dimensions[axis][0] if axis in dimensions else 1
    metadata["Size C"] = len(metadata["Channel Names"])
    for axis in "XYZ":
        count, length = dimensions.get(axis, (1, 0))
        # The length spans the first to the last pixel centre.
        metadata[f"Pixel Size {axis} (um)"] = _number(length * 1e6 / (count - 1)) if count > 1 else "N/A"
        metadata[f"Image Size {axis} (um)"] = _number(length * 1e6) if axis in dimensions else "N/A"
    frames, duration = dimensions.get("T", (1, 0))
    metadata["Time Interval (s)"] = _number(duration / (frames - 1)) if frames > 1 else "N/A"
    return metadata


def extract_lif_metadata(lif_path):
    """
    Extract metadata from a Leica LIF file.

    Args:
        lif_path (str): path to the .lif file.

    Returns:
        list[dict]: one metadata dict per image, in the order the images
        appear in the LAS X project tree. Each dict has the same keys; a
        value the image does not record is "N/A", or ["N/A"] for the
        per-channel lists.

    Raises:
        ValueError: if the file contains no images.
        Exception: whatever liffile raises for a file it cannot read.
    """
    with LifFile(lif_path) as lif:
        per_image = [_image_metadata(image.xml_element, image.path, image.timestamps) for image in lif.images]
    if not per_image:
        raise ValueError("No images found in LIF file.")
    return per_image


# Optional: CLI usage for testing
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lif_metadata.py <file.lif>")
    else:
        print(json.dumps(extract_lif_metadata(sys.argv[1]), indent=2))
