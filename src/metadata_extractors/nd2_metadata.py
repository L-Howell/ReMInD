"""
Read the metadata of Nikon ND2 files.

remind.py calls extract_nd2_metadata when the user loads a .nd2 file. The
result uses the same keys as the other extractors, so field_mapping can fill
the form from it. The file is read with the nd2 library. Some values are
only in the acquisition settings text that NIS-Elements writes, so they are
parsed from that text.
"""

import datetime
import os
import re

from nd2 import ND2File

try:
    from ._common import immersion_from_refractive_index
except ImportError:  # allow running as a standalone script
    from _common import immersion_from_refractive_index


# nd2 modality flag -> the form's term, most specific first, because a channel
# usually has several flags, e.g. "fluorescence" and "laserScanConfocal".
_MODALITY_TERMS = [
    ("sora", "SoRa"),
    ("TIRF", "TIRF"),
    ("multiphoton", "2Photon"),
    ("spinningDiskConfocal", "Spinning Disc Confocal"),
    ("laserScanConfocal", "Confocal"),
    ("sweptFieldConfocalSlit", "Confocal"),
    ("sweptFieldConfocalPinhole", "Confocal"),
    ("dsdConfocal", "Confocal"),
    ("camera", "Widefield"),
    ("fluorescence", "Widefield"),
    ("brightfield", "Widefield"),
]

# Words in a Nikon objective name that give the immersion medium.
_NAME_MEDIA = [(r"\bOil\b", "Oil"), (r"\bWI\b", "Water"), (r"\bSil\b", "Silicone"), (r"\bGlyc?\b", "Glycerol")]


def extract_nd2_metadata(file_path):
    """
    Extract metadata from a Nikon ND2 file.

    Args:
        file_path (str): path to the .nd2 file.

    Returns:
        dict: the metadata. A value the file does not record is "N/A", or
        ["N/A"] for the per-channel lists. "Document Creation Date" is
        "YYYY-MM-DD HH:MM:SS" in the acquisition computer's local time, when
        the order of day and month can be worked out. Otherwise it is the
        date text from the file. "System Name" is the microscope named in the
        acquisition settings, which most ND2 files leave out. The file does
        not name the immersion medium, so "Objective Medium" comes from the
        objective name (e.g. "Oil", "WI") or else the refractive index.
        "Size Z" and "Size T" are 1 when the file has no such axis.

    Raises:
        Exception: if the nd2 library cannot read the file.
    """
    with ND2File(file_path) as nd2_file:
        text = nd2_file.text_info or {}
        description = text.get("description") or ""
        channels = getattr(nd2_file.metadata, "channels", None) or []
        scope = channels[0].microscope if channels else None
        sizes = nd2_file.sizes
        voxel = nd2_file.voxel_size()

        microscope = re.search(r"^\s*Microscope:\s*(.+)$", description, re.MULTILINE)
        camera = re.search(r"^\s*Camera Name:\s*(.+)$", description, re.MULTILINE)
        refractive_index = getattr(scope, "immersionRefractiveIndex", None)

        def pixel_size(axis, size):
            return round(size, 3) if axis in sizes and size else "N/A"

        return {
            "File Name": os.path.basename(file_path),
            "Document Creation Date": _acquisition_date(" ".join((text.get("date") or "N/A").split()),
                                                        _julian_day(nd2_file)),
            "System Name": microscope.group(1).strip() if microscope else "N/A",
            "Camera Name": camera.group(1).strip() if camera else "N/A",
            "Objective Model": _known(getattr(scope, "objectiveName", None)),
            "Objective NA": _known(getattr(scope, "objectiveNumericalAperture", None)),
            "Objective Magnification": _known(getattr(scope, "objectiveMagnification", None)),
            "Objective Refractive Index": _known(refractive_index),
            "Objective Medium": _immersion(getattr(scope, "objectiveName", None), refractive_index),
            "Acquisition Modes": [_imaging_mode(c.microscope.modalityFlags) for c in channels] or ["N/A"],
            "Channel Names": [c.channel.name for c in channels] or ["N/A"],
            "Excitation Wavelengths": _excitation(channels, description) or ["N/A"],
            "Emission Wavelengths": [_known(c.channel.emissionLambdaNm) for c in channels] or ["N/A"],
            "Pinhole Diameters (um)": [_known(c.microscope.pinholeDiameterUm, 3) for c in channels] or ["N/A"],
            "Zoom": _known(getattr(scope, "zoomMagnification", None)),
            "Size X": sizes.get("X", "N/A"),
            "Size Y": sizes.get("Y", "N/A"),
            "Size Z": sizes.get("Z", 1),
            "Size T": sizes.get("T", 1),
            "Size C": sizes.get("C", 1),
            "Size P": sizes.get("P", 1),
            "Pixel Size X (um)": pixel_size("X", voxel.x),
            "Pixel Size Y (um)": pixel_size("Y", voxel.y),
            "Pixel Size Z (um)": pixel_size("Z", voxel.z),
            "Pixel Type": str(nd2_file.dtype),
        }


def _acquisition_date(text, julian_day):
    """Return the date text as "YYYY-MM-DD HH:MM:SS", or unchanged if its day and month are unclear."""
    # NIS-Elements writes the local time in the acquisition computer's date
    # format: "10/4/2019 10:35:36 AM" with the month first, or "04/10/2019
    # 10:35:36" with the day first. The text does not show which. The Julian
    # day of the first frame, in UTC, settles it.
    dates = set()
    for date_format in ("%m/%d/%Y", "%d/%m/%Y"):
        for time_format in ("%I:%M:%S %p", "%H:%M:%S"):
            try:
                dates.add(datetime.datetime.strptime(text, f"{date_format} {time_format}"))
            except ValueError:
                pass
    if len(dates) > 1:
        try:
            utc = datetime.datetime(1970, 1, 1) + datetime.timedelta(days=julian_day - 2440587.5)
        except (TypeError, OverflowError):
            return text
        # Local time is within a day of UTC, and the two readings of the text
        # are at least a month apart.
        dates = {date for date in dates if abs(date - utc) < datetime.timedelta(days=1)}
    return dates.pop().strftime("%Y-%m-%d %H:%M:%S") if len(dates) == 1 else text


def _julian_day(nd2_file):
    """Return the Julian day number of the first frame, or None."""
    try:
        return nd2_file.frame_metadata(0).channels[0].time.absoluteJulianDayNumber
    except Exception:  # older files have no such record, and fail in different ways
        return None


def _excitation(channels, description):
    """Return the excitation wavelength of each channel, or "N/A"."""
    lines_on = _lines_on(description)
    if len(lines_on) != len(channels):
        lines_on = [[] for _ in channels]
    wavelengths = []
    for channel, lines in zip(channels, lines_on):
        # A single line switched on is the most direct record. Next best is the
        # wavelength the nd2 library works out from the filter set. Last come
        # all the lines that were on, as a white-light source shows several.
        if len(lines) == 1:
            wavelengths.append(int(lines[0]))
        elif channel.channel.excitationLambdaNm is not None:
            wavelengths.append(channel.channel.excitationLambdaNm)
        else:
            wavelengths.append("/".join(lines) or "N/A")
    return wavelengths


def _lines_on(description):
    """Return the wavelengths of the lines switched on in each channel of the settings text."""
    # The text has one block per channel, starting at its "Name:" line. Each
    # light source line reads e.g. "Line:2; ExW:488; Power: 5.0; On".
    blocks = re.split(r"^\s*Name:.*$", description, flags=re.MULTILINE)[1:]
    return [re.findall(r"Line:\d+;\s*ExW:(\d+);[^\n]*?\bOn\b", block) for block in blocks]


def _imaging_mode(flags):
    """Return the form's term for the most specific of a channel's modality flags, or "N/A"."""
    return next((term for flag, term in _MODALITY_TERMS if flag in (flags or [])), "N/A")


def _immersion(objective_name, refractive_index):
    """Return the immersion medium, or "N/A" if it cannot be determined."""
    # The name is checked first: NIS-Elements leaves the refractive index at
    # 1.0 unless the user sets it, which would make a water objective "Air".
    for pattern, medium in _NAME_MEDIA:
        if re.search(pattern, objective_name or ""):
            return medium
    return immersion_from_refractive_index(refractive_index) or "N/A"


def _known(value, decimals=None):
    """Return value, rounded if decimals is given, or "N/A" if it is None or empty."""
    if value is None or value == "":
        return "N/A"
    return round(value, decimals) if decimals is not None else value


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nd2_metadata.py <file.nd2>")
    else:
        print(json.dumps(extract_nd2_metadata(sys.argv[1]), indent=2))
