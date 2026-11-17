"""
Read the metadata of Leica LIF files.

remind.py calls extract_lif_metadata when the user loads a .lif file. The
results use the same keys as the other extractors, so field_mapping can fill
the form from them. The file is read with the liffile library.

A LIF file is a project that can hold many images. Each image can have its
own objective, channels and scan settings. So every value is read from the
XML of its own image, and the result has one dict per image. Both layouts of
the hardware settings are read: the "HardwareSetting" block that LAS X
writes, and the older "HardwareSettingList" block that LAS AF writes.
"""

import datetime

from liffile import LifFile

try:
    from ._common import immersion_term, imaging_mode_term
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term


# The DimID that Leica gives each spatial axis and the time axis.
_AXES = {"1": "X", "2": "Y", "3": "Z", "4": "T"}


def extract_lif_metadata(lif_path):
    """
    Extract metadata from a Leica LIF file.

    Args:
        lif_path (str): path to the .lif file.

    Returns:
        list[dict]: one metadata dict per image, in the order of the LAS X
        project tree. Each image's name includes the folders it is in. Every
        dict has the same keys. A value the image does not record is "N/A",
        or ["N/A"] for the per-channel lists.

    Raises:
        ValueError: if the file contains no images.
        Exception: if liffile cannot read the file.
    """
    with LifFile(lif_path) as lif:
        per_image = [_image_metadata(image.xml_element, image.path, image.timestamps) for image in lif.images]
    if not per_image:
        raise ValueError("No images found in LIF file.")
    return per_image


def _image_metadata(element, name=None, timestamps=None):
    """Build the metadata dict of one image from its XML element."""
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


def _las_x_settings(hardware):
    """Read a LAS X "HardwareSetting" block."""
    definition = next((child for child in hardware if child.tag.endswith("SettingDefinition")), None)
    if definition is None:
        return {}

    # A sequential scan stores one settings block per sequence. The detectors
    # and laser lines in use are the ones recorded there.
    scans = hardware.findall("./LDM_Block_Sequential/LDM_Block_Sequential_List/*") or [definition]
    detectors, lasers_by_scan, bands = [], [], []
    for scan in scans:
        # Every line the laser offers is listed. The ones in use have power.
        lasers = [line.get("LaserLine") for line in scan.findall("./AotfList/Aotf/LaserLineSetting")
                  if float(line.get("IntensityDev") or 0) > 0]
        lasers_by_scan.append(lasers)
        # A sequential scan block has no Spectro of its own. The bands of all
        # its detectors are in the definition's.
        multibands = scan.findall("./Spectro/MultiBand") or definition.findall("./Spectro/MultiBand")
        ranges = {b.get("Channel"): (b.get("LeftWorld"), b.get("RightWorld")) for b in multibands}
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


def _channels(image, settings):
    """Return the (names, dyes, excitation wavelengths) of an image's channels."""
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
        # Without a detector name, the display colour (e.g. "Green") names the channel.
        names.append(detector or channel.get("LUTName") or "N/A")
        dyes.append(dye or "N/A")
        # The file lists the lasers of each scan, not which laser goes with
        # which detector. So a line is given only when its scan used one laser.
        excitation.append(lasers[0] if len(lasers) == 1 else "N/A")
    return names, dyes, excitation


def _objective_medium(objective_name):
    """Return the medium in an objective name such as "HCX PL APO CS 63.0x1.40 OIL UV", or "N/A"."""
    for word in (objective_name or "").split():
        if immersion_term(word) != word:
            return immersion_term(word)
    return "N/A"


def _dimensions(image):
    """Return {axis: (size, length)} for the image's X, Y, Z and T axes, in metres or seconds."""
    dimensions = {}
    for d in image.findall("./ImageDescription/Dimensions/DimensionDescription"):
        axis = _AXES.get(d.get("DimID"))
        if axis:
            dimensions[axis] = (int(d.get("NumberOfElements")), float(d.get("Length") or 0))
    return dimensions


def _local_time(timestamps):
    """Return an image's first UTC time stamp as "YYYY-MM-DD HH:MM:SS" local time, or "N/A"."""
    if timestamps is None or len(timestamps) == 0:
        return "N/A"
    utc = timestamps[0].astype("datetime64[s]").item().replace(tzinfo=datetime.timezone.utc)
    return utc.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _clean_dye(name):
    """Turn a dye name such as "Leica/HOECHST 33258." into "HOECHST 33258"."""
    return name.split("/", 1)[-1].strip(" .")


def _number(text, decimals=3):
    """Return text as a rounded number, an int when it is whole, or "N/A"."""
    try:
        value = round(float(text), decimals)
    except (TypeError, ValueError):
        return "N/A"
    return int(value) if value.is_integer() else value


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lif_metadata.py <file.lif>")
    else:
        print(json.dumps(extract_lif_metadata(sys.argv[1]), indent=2))
