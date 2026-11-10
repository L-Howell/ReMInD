"""
Extract metadata from OME-TIFF files using the tifffile library.
Returns key image, instrument, and channel metadata as one dictionary per
image, using the same vocabulary as the other ReMInD extractors.

tifffile hands over the OME-XML text stored in the file; the values are read
from that XML here.
"""

import os
from collections import Counter

from tifffile import TiffFile

try:
    from ._common import immersion_term, imaging_mode_term, parse_xml
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term, parse_xml


# Factor from each length unit OME allows for pixel sizes to micrometres.
# OME-XML uses micrometres when no unit is given.
_TO_MICROMETRES = {"nm": 1e-3, "µm": 1, "um": 1, "mm": 1e3, "cm": 1e4, "m": 1e6, "Å": 1e-4}


def _number(value, decimals=3):
    """Return value as a rounded float, or "N/A" if it is missing or not a number."""
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return "N/A"


def _pixel_size(pixels, axis):
    """Return the pixel size along an axis in micrometres, or "N/A"."""
    size = _number(pixels.get(f"PhysicalSize{axis}"), 9)
    factor = _TO_MICROMETRES.get(pixels.get(f"PhysicalSize{axis}Unit", "µm"))
    return round(size * factor, 3) if size != "N/A" and factor else "N/A"


def _instrument_and_objective(root, image):
    """
    Return the (Instrument, Objective) elements an image refers to. Each
    falls back to the first one in the file when the image does not name
    one, and is None when the file has none.
    """
    instruments = root.findall("Instrument")
    reference = image.find("InstrumentRef")
    instrument = next((i for i in instruments if reference is not None and i.get("ID") == reference.get("ID")),
                      instruments[0] if instruments else None)
    if instrument is None:
        return None, None
    objectives = instrument.findall("Objective")
    settings = image.find("ObjectiveSettings")
    objective = next((o for o in objectives if settings is not None and o.get("ID") == settings.get("ID")),
                     objectives[0] if objectives else None)
    return instrument, objective


def _image_metadata(root, image):
    """Build the metadata dict for one Image element of the OME-XML."""
    pixels = image.find("Pixels")
    channels = pixels.findall("Channel")
    instrument, objective = _instrument_and_objective(root, image)

    system_name = "N/A"
    if instrument is not None and instrument.find("Microscope") is not None:
        microscope = instrument.find("Microscope")
        system_name = microscope.get("Model") or microscope.get("Manufacturer") or "N/A"

    objective_model, objective_na, magnification, medium = "N/A", "N/A", "N/A", "N/A"
    if objective is not None:
        objective_na = _number(objective.get("LensNA"))
        magnification = _number(objective.get("NominalMagnification"), 1)
        parts = [objective.get("Model") or "",
                 f"{int(magnification)}x" if magnification != "N/A" else "",
                 f"NA {objective_na}" if objective_na != "N/A" else ""]
        objective_model = " ".join(part for part in parts if part) or "N/A"
        medium = objective.get("Immersion") or "N/A"
    # The immersion can also be recorded with the image's objective settings.
    settings = image.find("ObjectiveSettings")
    if medium == "N/A" and settings is not None:
        medium = settings.get("Medium") or "N/A"

    # One imaging mode for the image: the most common among its channels.
    modes = Counter(c.get("AcquisitionMode") for c in channels if c.get("AcquisitionMode"))
    mode = imaging_mode_term(modes.most_common(1)[0][0]) if modes else "N/A"

    size = {axis: int(pixels.get(f"Size{axis}")) for axis in "XYZTC"}
    pixel_size = {axis: _pixel_size(pixels, axis) for axis in "XYZ"}

    return {
        "Image Name":              image.get("Name") or image.get("ID") or "N/A",
        "Document Creation Date":  (image.findtext("AcquisitionDate") or "N/A").strip(),
        "System Name":             system_name,
        "Objective Model":         objective_model,
        "Objective NA":            objective_na,
        "Objective Magnification": magnification,
        "Objective Medium":        immersion_term(medium),
        "Acquisition Modes":       mode,
        "Channel Names":           [c.get("Name") or f"Channel {i + 1}" for i, c in enumerate(channels)] or ["N/A"],
        "Dye Names":               [c.get("Fluor") or "N/A" for c in channels] or ["N/A"],
        "Excitation Wavelengths":  [_number(c.get("ExcitationWavelength")) for c in channels] or ["N/A"],
        "Emission Wavelengths":    [_number(c.get("EmissionWavelength")) for c in channels] or ["N/A"],
        "Size X":                  size["X"],
        "Size Y":                  size["Y"],
        "Size Z":                  size["Z"],
        "Size T":                  size["T"],
        "Size C":                  size["C"],
        "Pixel Size X (um)":       pixel_size["X"],
        "Pixel Size Y (um)":       pixel_size["Y"],
        "Pixel Size Z (um)":       pixel_size["Z"],
        **{f"Image Size {axis} (um)": round(size[axis] * pixel_size[axis], 3) if pixel_size[axis] != "N/A" else "N/A"
           for axis in "XYZ"},
        "Pixel Type":              pixels.get("Type") or "N/A",
    }


def extract_ometiff_metadata(file_path):
    """
    Extract metadata from an OME-TIFF file.

    Args:
        file_path (str): path to the .tif or .tiff file.

    Returns:
        list[dict]: one metadata dict per image in the file. A value the file
        does not record is "N/A". Pixel sizes are converted to micrometres;
        wavelengths are given as written, which is nanometres unless the
        file says otherwise.

    Raises:
        ValueError: if the TIFF holds no OME-XML (it is a plain TIFF), or the
            OME-XML describes no images.
        Exception: whatever tifffile raises for a file it cannot read.
    """
    with TiffFile(file_path) as tif:
        ome_xml = tif.ome_metadata
    if not ome_xml:
        raise ValueError("No OME-XML metadata found in this TIFF. "
                         "It may be a plain TIFF rather than an OME-TIFF.")
    root = parse_xml(ome_xml)
    images = root.findall("Image")
    if not images:
        raise ValueError("The OME-TIFF describes no images.")
    file_name = os.path.basename(file_path)
    return [{**_image_metadata(root, image), "File Name": file_name} for image in images]


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ome_tiff_metadata.py <file.ome.tif>")
    else:
        print(json.dumps(extract_ometiff_metadata(sys.argv[1]), indent=2))
