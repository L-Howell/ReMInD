"""
Shared helpers for metadata extractors.
"""

from collections import Counter


def _signature(value):
    """Return a hashable signature for counting, falling back to repr for
    unhashable values (e.g. lists of channel names)."""
    try:
        hash(value)
        return value
    except TypeError:
        return repr(value)


def most_common_metadata(dicts):
    """
    Collapse a list of per-image metadata dicts into a single dict by taking,
    for each key, the value that occurs most often across the images.

    Useful for container formats (e.g. .lif, multi-image OME-TIFF) where the
    first image may be an overview/thumbnail that is not representative. Ties
    are broken in favour of the value seen earliest (i.e. the first image).

    Args:
        dicts (list[dict]): one metadata dict per image/series.

    Returns:
        dict: a single representative metadata dict.
    """
    dicts = [d for d in dicts if d]
    if not dicts:
        return {}
    if len(dicts) == 1:
        return dict(dicts[0])

    # Union of keys, preserving first-seen order.
    keys = []
    for d in dicts:
        for k in d:
            if k not in keys:
                keys.append(k)

    result = {}
    for k in keys:
        values = [d[k] for d in dicts if k in d]
        if not values:
            continue
        counts = Counter()
        first_seen = {}
        for v in values:
            sig = _signature(v)
            counts[sig] += 1
            if sig not in first_seen:
                first_seen[sig] = v
        # Counter.most_common breaks ties by first-encountered order (Py3.7+).
        best_sig = counts.most_common(1)[0][0]
        result[k] = first_seen[best_sig]
    return result


# Image files say only "oil", never which oil, so the form gets plain "Oil"
# and the user picks Oil-23 or Oil-37 if they know.
_IMMERSION_TERMS = {
    "OIL":          "Oil",
    "WATER":        "Water",
    "WATERDIPPING": "Water",
    "AIR":          "Air",
    "DRY":          "Air",
    "GLYCEROL":     "Glycerol",
    "GLYCERIN":     "Glycerol",
    "GLYCERINE":    "Glycerol",
    "SILICONE":     "Silicone",
}

# Keys are OME acquisition-mode names (also used by CZI) plus the short device
# names found in OIR files. Values are the terms used by the ReMInD form.
_IMAGING_MODE_TERMS = {
    "WIDEFIELD":                       "Widefield",
    "LASERSCANNINGCONFOCALMICROSCOPY": "Confocal",
    "LASERSCANNINGMICROSCOPY":         "Confocal",
    "LSM":                             "Confocal",
    "CONFOCAL":                        "Confocal",
    "SLITSCANCONFOCAL":                "Confocal",
    "SPINNINGDISKCONFOCAL":            "Spinning Disc Confocal",
    "MULTIPHOTONMICROSCOPY":           "2Photon",
    "TOTALINTERNALREFLECTION":         "TIRF",
    "TIRF":                            "TIRF",
    "STRUCTUREDILLUMINATION":          "Widefield",
    "FLUORESCENCELIFETIME":            "FLIM",
    "STED":                            "STED",
}


def _lookup_key(value):
    """Upper-case a value and drop spaces, underscores and hyphens."""
    return str(value).upper().replace("_", "").replace(" ", "").replace("-", "")


def immersion_term(raw):
    """
    Translate an immersion medium as written in an image file into the term
    used by the ReMInD form.

    Args:
        raw: the medium from the file, e.g. "OIL", "Dry", "WaterDipping".
            Matching ignores case, spaces, underscores and hyphens.

    Returns:
        The form's term (e.g. "Oil", "Air", "Water") when the medium is
        recognised. Any other value, including "N/A" and "", is returned
        unchanged.
    """
    return _IMMERSION_TERMS.get(_lookup_key(raw), raw)


def imaging_mode_term(raw):
    """
    Translate an acquisition mode as written in an image file into the term
    used by the ReMInD form.

    Args:
        raw: the mode from the file, e.g. "LaserScanningConfocalMicroscopy",
            "LSM", "SPINNING_DISK_CONFOCAL". Matching ignores case, spaces,
            underscores and hyphens.

    Returns:
        The form's term (e.g. "Confocal", "Widefield") when the mode is
        recognised. Any other value, including "N/A" and "", is returned
        unchanged.
    """
    return _IMAGING_MODE_TERMS.get(_lookup_key(raw), raw)
