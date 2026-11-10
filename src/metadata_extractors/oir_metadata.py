"""
Extract metadata from Olympus/Evident OIR files using the oirfile library.
Returns key image, instrument, and channel metadata as a dictionary using the
same vocabulary as the other ReMInD extractors.

An OIR file stores its settings as many separate XML blocks. A value is taken
from the first block that has it.
"""

import os
import re
import xml.etree.ElementTree as ET

from oirfile import OirFile

try:
    from ._common import immersion_term, imaging_mode_term, parse_xml
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term, parse_xml


def _number(value, decimals=3):
    """Return value as a rounded float, or "N/A" if it is missing or not a number."""
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return "N/A"


def _parse_blocks(xml_metadata):
    """Return the root element of every XML block, skipping any that is not
    well-formed XML."""
    roots = []
    for block in xml_metadata.values():
        for text in block:
            try:
                roots.append(parse_xml(text))
            except ET.ParseError:
                continue
    return roots


def _find_text(roots, *paths):
    """Return the text of the first non-empty element at any of the paths,
    anywhere below the roots, or "N/A"."""
    for root in roots:
        for path in paths:
            text = (root.findtext(f".//{path}") or "").strip()
            if text:
                return text
    return "N/A"


def _channel_settings(root):
    """
    Return the settings of each channel described in one XML block, in file
    order, as dicts with the keys "name", "excitation", "emission" and
    "pinhole". The list is empty for a block that describes no channels.
    """
    settings = []
    seen = set()
    for channel in root.findall(".//phase/group/channel"):
        # Each channel is described twice, the second time without its
        # detection band.
        if channel.get("id") in seen:
            continue
        seen.add(channel.get("id"))

        # A lambda scan has no fixed detection band.
        band = channel.find(".//wavelengthRange")
        start = _number(band.findtext("startWavelength"), 0) if band is not None else "N/A"
        end = _number(band.findtext("endWavelength"), 0) if band is not None else "N/A"

        # The laser is named in e.g. "LD405_65792Imaging_main_phase_1". A
        # channel can use several lasers.
        lasers = [match.group(1) for match in
                  (re.search(r"LD(\d+)", laser.text or "") for laser in channel.findall("laserDataId")) if match]

        settings.append({
            "name": channel.findtext("name") or "N/A",
            "excitation": int(lasers[0]) if len(lasers) == 1 else "/".join(lasers) or "N/A",
            "emission": f"{int(start)}-{int(end)}" if "N/A" not in (start, end) else "N/A",
            "pinhole": _number(channel.findtext(".//pinholeDiameter")),
        })
    return settings


def extract_oir_metadata(file_path):
    """
    Extract metadata from an Olympus/Evident OIR file.

    Args:
        file_path (str): path to the .oir file.

    Returns:
        dict: the metadata. A value the file does not record is "N/A". The
        per-channel values are lists with one entry per channel, in the
        order of the image data. Lengths are in micrometres and wavelengths
        in nanometres; a channel excited by several lasers gives them joined
        with "/", e.g. "405/488". "Size Z", "Size T" and "Size C" are 1 when
        the file has no such axis.

    Raises:
        Exception: whatever oirfile raises for a file it cannot read.
    """
    with OirFile(file_path) as oir:
        sizes = oir.sizes
        channel_axis = oir.coords.get("C")
        acquisition_date = oir.datetime or "N/A"
        roots = _parse_blocks(oir.xml_metadata)
        bits = (oir.attrs or {}).get("bitspersample", "N/A")

    # A file with a single channel has no channel axis. Its name is taken
    # from the channel settings below.
    channel_names = [str(name) for name in channel_axis] if channel_axis is not None else ["N/A"]
    count = len(channel_names)

    # Micrometres, as the pixelUnit elements beside these values say.
    length = next((root.find(".//length") for root in roots if root.find(".//length") is not None), None)
    pixel_size = {axis: _number(length.findtext(axis.lower())) if length is not None else "N/A" for axis in "XYZ"}
    if "Z" not in sizes:
        pixel_size["Z"] = "N/A"  # the file gives a Z step even for a single plane
    image_size = {axis: _number(sizes[axis] * pixel_size[axis]) if axis in sizes and pixel_size[axis] != "N/A"
                  else "N/A" for axis in "XYZ"}

    name = _find_text(roots, "objectiveLens/displayName", "objectiveLens/name")
    magnification = _number(_find_text(roots, "objectiveLens/magnification"), 1)
    numerical_aperture = _number(_find_text(roots, "objectiveLens/naValue"))
    parts = [name if name != "N/A" else "",
             f"{int(magnification)}x" if magnification != "N/A" else "",
             f"NA {numerical_aperture}" if numerical_aperture != "N/A" else ""]

    excitation = emission = pinholes = ["N/A"] * count
    settings = next((s for s in map(_channel_settings, roots) if s), [])
    # When one channel was saved but several are described, the file does not
    # say which one it is, so nothing is reported for it.
    if settings and (channel_axis is not None or len(settings) == 1):
        if channel_axis is None:
            channel_names = [settings[0]["name"]]
        excitation = [s["excitation"] for s in settings[:count]]
        emission = [s["emission"] for s in settings[:count]]
        pinholes = [s["pinhole"] for s in settings[:count]]

    dyes = {root.findtext("name"): root.findtext("dyeName") for root in roots if root.tag == "lsmChannel"}

    return {
        "Document Creation Date": acquisition_date,
        "System Name": _find_text(roots, "systemName"),
        "Objective Model": " ".join(part for part in parts if part) or "N/A",
        "Objective NA": numerical_aperture,
        "Objective Magnification": magnification,
        "Objective Medium": immersion_term(_find_text(roots, "objectiveLens/immersion")),
        # The device name, e.g. "LSM".
        "Acquisition Modes": imaging_mode_term(_find_text(roots, "deviceName", "acquisitionMode", "modality")),
        "Channel Names": channel_names,
        "Dye Names": [dyes.get(name) or "N/A" for name in channel_names],
        "Excitation Wavelengths": excitation,
        "Emission Wavelength Range (nm)": emission,
        "Pinhole Diameters (um)": pinholes,
        "Size X": sizes.get("X", "N/A"),
        "Size Y": sizes.get("Y", "N/A"),
        "Size Z": sizes.get("Z", 1),
        "Size T": sizes.get("T", 1),
        "Size C": sizes.get("C", 1),
        "Pixel Size X (um)": pixel_size["X"],
        "Pixel Size Y (um)": pixel_size["Y"],
        "Pixel Size Z (um)": pixel_size["Z"],
        "Image Size X (um)": image_size["X"],
        "Image Size Y (um)": image_size["Y"],
        "Image Size Z (um)": image_size["Z"],
        "Bits Per Sample": bits,
        "File Name": os.path.basename(file_path),
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python oir_metadata.py <file.oir>")
    else:
        print(json.dumps(extract_oir_metadata(sys.argv[1]), indent=2, default=str))
