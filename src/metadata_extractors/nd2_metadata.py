"""
Extract metadata from Nikon ND2 files using the nd2 library.
Returns key image, instrument, and channel metadata as a dictionary using the
same vocabulary as the other ReMInD extractors.
"""

import datetime
import os
import re

from nd2 import ND2File

try:
    from ._common import immersion_from_refractive_index
except ImportError:  # allow running as a standalone script
    from _common import immersion_from_refractive_index


# nd2 modality flag -> the ReMInD form's term, most specific first. A channel
# usually carries several flags, e.g. "fluorescence" and "laserScanConfocal".
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


def _immersion(objective_name, refractive_index):
    """Return the immersion medium, or "N/A" if it cannot be told."""
    # The name is checked first: NIS-Elements leaves the refractive index at
    # 1.0 unless the user sets it, which would make a water objective "Air".
    for pattern, medium in _NAME_MEDIA:
        if re.search(pattern, objective_name or ""):
            return medium
    return immersion_from_refractive_index(refractive_index) or "N/A"


def _lines_on(description):
    """
    Return, for each channel in the acquisition settings text, the list of
    laser or LED lines that were switched on, as wavelength strings.

    The text has one block per channel, starting at its "Name:" line, with
    the light sources listed as e.g. "Line:2; ExW:488; Power: 5.0; On".
    """
    blocks = re.split(r"^\s*Name:.*$", description, flags=re.MULTILINE)[1:]
    return [re.findall(r"Line:\d+;\s*ExW:(\d+);[^\n]*?\bOn\b", block) for block in blocks]


def _excitation(channels, description):
    """
    Return the excitation wavelength of each channel, or "N/A".

    A single line switched on is the most direct record, so it is used when
    there is one. Otherwise the wavelength the nd2 library derives from the
    filter set is used, and failing that all the lines that were on, joined
    with "/" (a white-light source shows as several lines).
    """
    lines_on = _lines_on(description)
    if len(lines_on) != len(channels):
        lines_on = [[] for _ in channels]
    wavelengths = []
    for channel, lines in zip(channels, lines_on):
        if len(lines) == 1:
            wavelengths.append(int(lines[0]))
        elif channel.channel.excitationLambdaNm is not None:
            wavelengths.append(channel.channel.excitationLambdaNm)
        else:
            wavelengths.append("/".join(lines) or "N/A")
    return wavelengths


def _acquisition_date(text, julian_day):
    """
    Return the acquisition date as "YYYY-MM-DD HH:MM:SS".

    Args:
        text (str): the date as NIS-Elements wrote it, in the date format of
            the acquisition computer: "10/4/2019 10:35:36 AM" on one set to
            month/day and "04/10/2019 10:35:36" on one set to day/month.
        julian_day (float | None): the Julian day number of the first frame,
            which is in UTC.

    The text gives the local time but not the order of day and month; the
    Julian day settles the order. The text is returned unchanged when it is
    in neither form, or when both orders are possible dates and the Julian
    day is missing or matches neither.
    """
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
        # Local time is within a day of UTC; the two readings of the text
        # are at least a month apart.
        dates = {date for date in dates if abs(date - utc) < datetime.timedelta(days=1)}
    return dates.pop().strftime("%Y-%m-%d %H:%M:%S") if len(dates) == 1 else text


def _julian_day(nd2_file):
    """Return the Julian day number of the first frame, or None."""
    try:
        return nd2_file.frame_metadata(0).channels[0].time.absoluteJulianDayNumber
    except Exception:  # older files have no such record, and fail in various ways
        return None


def _known(value, decimals=None):
    """Return value, rounded if decimals is given, or "N/A" if it is None or empty."""
    if value is None or value == "":
        return "N/A"
    return round(value, decimals) if decimals is not None else value


def _imaging_mode(flags):
    return next((term for flag, term in _MODALITY_TERMS if flag in (flags or [])), "N/A")


def extract_nd2_metadata(file_path):
    """
    Extract metadata from a Nikon ND2 file.

    Args:
        file_path (str): path to the .nd2 file.

    Returns:
        dict: the metadata. A value the file does not record is "N/A", or
        ["N/A"] for the per-channel lists. Notes on particular keys:
          - "Document Creation Date" is "YYYY-MM-DD HH:MM:SS" in the local
            time of the acquisition computer where that can be worked out;
            see _acquisition_date.
          - "System Name" is the microscope named in the acquisition
            settings. Most ND2 files do not name one.
          - "Objective Medium" is taken from the objective name where it
            says (e.g. "Oil", "WI"), and otherwise derived from the
            refractive index, as the file does not name the medium.
          - "Size Z" and "Size T" are 1 when the file has no such axis.

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


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nd2_metadata.py <file.nd2>")
    else:
        print(json.dumps(extract_nd2_metadata(sys.argv[1]), indent=2))
