"""
Shared helpers for metadata extractors.
"""

import xml.etree.ElementTree as ET
from collections import Counter


def parse_xml(text):
    """
    Parse XML text and return its root element with the namespaces removed
    from every tag and attribute name, e.g. "{http://...}Pixels" becomes
    "Pixels". Elements can then be found by their plain names.

    Raises:
        xml.etree.ElementTree.ParseError: if the text is not well-formed XML.
    """
    root = ET.fromstring(text)
    for element in root.iter():
        element.tag = element.tag.split("}", 1)[-1]
        element.attrib = {name.split("}", 1)[-1]: value for name, value in element.attrib.items()}
    return root


def _display(value):
    """Return a metadata value as text, joining lists with ", "."""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def combine_image_metadata(per_image, name_key="Image Name"):
    """
    Describe all the images of one file in a single metadata dict.

    A file such as a LIF project can hold images taken with different
    settings. Reporting only the first or the most common value would hide
    that, so every distinct value is kept.

    Args:
        per_image (list[dict]): one metadata dict per image.
        name_key (str): the key holding each image's name.

    Returns:
        dict: for each key, in first-seen order:
          - the value itself when every image has the same one (lists stay
            lists);
          - otherwise text listing each distinct value, most common first,
            with the images it applies to: their names for up to three
            images, a count for more. For example
            "63x/1.40 OIL [14 images]; 10x/0.40 DRY [Overview]". Beyond four
            distinct values the rest are summarised as "and N more values".
        The image names are not combined this way: with more than one image
        the result has "Image Count" and "Image Names" in place of name_key.
        An empty list gives an empty dict.
    """
    if not per_image:
        return {}
    if len(per_image) == 1:
        return dict(per_image[0])

    names = [str(image.get(name_key, f"image {i + 1}")) for i, image in enumerate(per_image)]
    combined = {
        "Image Count": len(per_image),
        "Image Names": ", ".join(names[:20]) + (f" and {len(names) - 20} more" if len(names) > 20 else ""),
    }

    keys = []
    for image in per_image:
        keys.extend(key for key in image if key not in keys and key != name_key)

    for key in keys:
        images_by_value = {}
        first_value = {}
        for name, image in zip(names, per_image):
            if key in image:
                text = _display(image[key])
                images_by_value.setdefault(text, []).append(name)
                first_value.setdefault(text, image[key])
        if len(images_by_value) == 1 and len(next(iter(images_by_value.values()))) == len(per_image):
            combined[key] = next(iter(first_value.values()))
            continue
        # sorted() is stable, so equally common values keep file order.
        ranked = sorted(images_by_value.items(), key=lambda item: -len(item[1]))
        parts = [
            f"{text} [{', '.join(images) if len(images) <= 3 else f'{len(images)} images'}]"
            for text, images in ranked[:4]
        ]
        if len(ranked) > 4:
            parts.append(f"and {len(ranked) - 4} more values")
        combined[key] = "; ".join(parts)
    return combined


def immersion_from_refractive_index(refractive_index):
    """
    Return the immersion medium implied by a refractive index, for files
    that record the index but do not name the medium.

    The index of each common medium is matched with a small margin: air
    (1.0), water (1.33), silicone oil (1.40), glycerol (1.47) and immersion
    oil (1.515). Returns "" for any other index and for anything that is not
    a number.
    """
    try:
        ri = float(refractive_index)
    except (TypeError, ValueError):
        return ""
    for low, high, medium in ((0.99, 1.01, "Air"), (1.32, 1.35, "Water"), (1.39, 1.42, "Silicone"),
                              (1.44, 1.48, "Glycerol"), (1.50, 1.53, "Oil")):
        if low <= ri <= high:
            return medium
    return ""


# Image files say only "oil", never which oil, so the form gets plain "Oil"
# and the user picks Oil-23 or Oil-37 if they know.
_IMMERSION_TERMS = {
    "OIL":          "Oil",
    "WATER":        "Water",
    "W":            "Water",
    "WATERDIPPING": "Water",
    "AIR":          "Air",
    "DRY":          "Air",
    "GLYCEROL":     "Glycerol",
    "GLYC":         "Glycerol",
    "GLYCERIN":     "Glycerol",
    "GLYCERINE":    "Glycerol",
    "SILICONE":     "Silicone",
    # A multi-immersion objective works with several media, and the file
    # does not reliably say which was used.
    "IMM":          "Multi-immersion",
}

# Keys are OME acquisition-mode names (also used by CZI) plus the short device
# names found in OIR and LIF files. Values are the terms used by the ReMInD form.
_IMAGING_MODE_TERMS = {
    "WIDEFIELD":                       "Widefield",
    "CAMERA":                          "Widefield",
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
        The form's term when the mode is recognised: an "Imaging mode"
        option (e.g. "Confocal", "Widefield") or a "Specialist modality"
        option ("STED", "TIRF", "FLIM"). Any other value, including "N/A"
        and "", is returned unchanged.
    """
    return _IMAGING_MODE_TERMS.get(_lookup_key(raw), raw)
