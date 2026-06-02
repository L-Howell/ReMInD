"""
Extract metadata from OME-TIFF files using the ome-types library.
Returns key image, instrument, and channel metadata as a structured dictionary
using the same vocabulary as the other ReMInD extractors.

For multi-image OME-TIFFs the per-image metadata is collapsed to the most
common value per field (see most_common_metadata), so a leading overview or
thumbnail image does not skew the result.
"""

import os

from ome_types import from_tiff

try:
    from ._common import most_common_metadata
except ImportError:  # allow running as a standalone script
    from _common import most_common_metadata


_IMMERSION_MAP = {
    "OIL":          "Oil-23",
    "WATER":        "Water",
    "WATERDIPPING": "Water",
    "AIR":          "Air",
    "DRY":          "Air",
    "GLYCEROL":     "Glycerol",
    "MULTI":        "Other",
    "OTHER":        "Other",
}

_ACQ_MODE_MAP = {
    "WIDEFIELD":                       "Widefield",
    "LASERSCANNINGCONFOCALMICROSCOPY": "Confocal",
    "LASERSCANNINGMICROSCOPY":         "Confocal",
    "SLITSCANCONFOCAL":                "Confocal",
    "SPINNINGDISKCONFOCAL":            "Spinning Disc Confocal",
    "MULTIPHOTONMICROSCOPY":           "2Photon",
    "TOTALINTERNALREFLECTION":         "TIRF",
    "STRUCTUREDILLUMINATION":          "Widefield",
    "FLUORESCENCELIFETIME":            "FLIM",
}


def _val(enum_or_value):
    """Return the plain value of an ome-types enum, or the value unchanged."""
    return getattr(enum_or_value, "value", enum_or_value)


def _safe_round(val, decimals=3):
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return val


def _fov(size, px):
    try:
        return round(float(size) * float(px), 3)
    except (TypeError, ValueError):
        return "N/A"


def _resolve_objective(ome, image):
    """Find the Objective for an image via its ObjectiveSettings/InstrumentRef,
    falling back to the first objective available."""
    instrument = None
    if image.instrument_ref is not None:
        instrument = next(
            (i for i in ome.instruments if i.id == image.instrument_ref.id), None
        )
    if instrument is None and ome.instruments:
        instrument = ome.instruments[0]
    if instrument is None:
        return None, instrument

    objective = None
    if image.objective_settings is not None and image.objective_settings.id:
        objective = next(
            (o for o in instrument.objectives if o.id == image.objective_settings.id),
            None,
        )
    if objective is None and instrument.objectives:
        objective = instrument.objectives[0]
    return objective, instrument


def _resolve_experimenter(ome, image):
    if image.experimenter_ref is not None:
        exp = next(
            (e for e in ome.experimenters if e.id == image.experimenter_ref.id), None
        )
        if exp is not None:
            return exp
    return ome.experimenters[0] if ome.experimenters else None


def _experimenter_name(exp):
    if exp is None:
        return "N/A"
    if exp.user_name:
        return exp.user_name
    full = " ".join(p for p in (exp.first_name, exp.last_name) if p)
    return full or "N/A"


def _image_metadata(ome, image):
    """Build a metadata dict (ReMInD vocabulary) for a single OME Image."""
    px = image.pixels

    # --- Channels ---
    channel_names = []
    excitation = []
    emission = []
    acq_modes = []
    for i, ch in enumerate(px.channels):
        channel_names.append(ch.name or f"Channel {i + 1}")
        excitation.append(_safe_round(ch.excitation_wavelength)
                          if ch.excitation_wavelength is not None else "N/A")
        emission.append(_safe_round(ch.emission_wavelength)
                        if ch.emission_wavelength is not None else "N/A")
        if ch.acquisition_mode is not None:
            acq_modes.append(_val(ch.acquisition_mode))
    if not channel_names:
        channel_names = ["N/A"]

    # Imaging mode: most common channel acquisition mode, mapped to a friendly term.
    acq_mode = "N/A"
    if acq_modes:
        raw_mode = max(set(acq_modes), key=acq_modes.count)
        key = str(raw_mode).upper().replace("_", "").replace(" ", "")
        acq_mode = _ACQ_MODE_MAP.get(key, raw_mode)

    # --- Objective / instrument ---
    objective, instrument = _resolve_objective(ome, image)

    system_name = "N/A"
    if instrument is not None and instrument.microscope is not None:
        m = instrument.microscope
        system_name = m.model or m.manufacturer or "N/A"

    obj_na = obj_mag = "N/A"
    objective_str = "N/A"
    immersion = "N/A"
    if objective is not None:
        obj_na = _safe_round(objective.lens_na) if objective.lens_na is not None else "N/A"
        obj_mag = (_safe_round(objective.nominal_magnification, 1)
                   if objective.nominal_magnification is not None else "N/A")
        parts = []
        if objective.model:
            parts.append(objective.model)
        if obj_mag != "N/A":
            try:
                parts.append(f"{int(float(obj_mag))}x")
            except (TypeError, ValueError):
                parts.append(str(obj_mag))
        if obj_na != "N/A":
            parts.append(f"NA {obj_na}")
        objective_str = "  ".join(parts) if parts else "N/A"
        if objective.immersion is not None:
            immersion = _IMMERSION_MAP.get(str(_val(objective.immersion)).upper(),
                                           _val(objective.immersion))
    # ObjectiveSettings medium can override / supply immersion.
    if immersion == "N/A" and image.objective_settings is not None \
            and image.objective_settings.medium is not None:
        immersion = _IMMERSION_MAP.get(str(_val(image.objective_settings.medium)).upper(),
                                       _val(image.objective_settings.medium))

    # --- Pixel sizes ---
    px_x = _safe_round(px.physical_size_x) if px.physical_size_x is not None else "N/A"
    px_y = _safe_round(px.physical_size_y) if px.physical_size_y is not None else "N/A"
    px_z = _safe_round(px.physical_size_z) if px.physical_size_z is not None else "N/A"

    acq_date = image.acquisition_date.isoformat() if image.acquisition_date else "N/A"

    return {
        "Document Creation Date":  acq_date,
        "Document User Name":      _experimenter_name(_resolve_experimenter(ome, image)),
        "System Name":             system_name,
        "Objective Model":         objective_str,
        "Objective NA":            obj_na,
        "Objective Magnification": obj_mag,
        "Objective Medium":        immersion,
        "Acquisition Modes":       acq_mode,
        "Channel Names":           channel_names,
        "Excitation Wavelengths":  excitation or ["N/A"],
        "Emission Wavelengths":    emission or ["N/A"],
        "Size X":                  px.size_x,
        "Size Y":                  px.size_y,
        "Size Z":                  px.size_z,
        "Size T":                  px.size_t,
        "Size C":                  px.size_c,
        "Pixel Size X (um)":       px_x,
        "Pixel Size Y (um)":       px_y,
        "Pixel Size Z (um)":       px_z,
        "Image Size X (um)":       _fov(px.size_x, px_x),
        "Image Size Y (um)":       _fov(px.size_y, px_y),
        "Image Size Z (um)":       _fov(px.size_z, px_z),
        "Pixel Type":              str(_val(px.type)) if px.type is not None else "N/A",
    }


def extract_ometiff_metadata(file_path):
    """
    Extract metadata from an OME-TIFF file.

    Returns:
        tuple: (metadata_output_dict, ome_object)

    Raises:
        Exception: if the file contains no parseable OME-XML metadata.
    """
    try:
        ome = from_tiff(file_path)
    except Exception as e:
        raise Exception(
            "No OME-XML metadata found in this TIFF — it may be a plain TIFF "
            f"rather than an OME-TIFF.\n({e})"
        )

    if not ome.images:
        raise Exception("OME-TIFF contains no image metadata.")

    per_image = [_image_metadata(ome, img) for img in ome.images]
    metadata_output = most_common_metadata(per_image)
    metadata_output["Image Count"] = len(ome.images)
    metadata_output["File Name"] = os.path.basename(file_path)

    return metadata_output, ome


# CLI usage for testing
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python OMETiff_MetadataGUI.py <file.ome.tif>")
    else:
        meta, _ = extract_ometiff_metadata(sys.argv[1])
        print(json.dumps(meta, indent=2, default=str))
