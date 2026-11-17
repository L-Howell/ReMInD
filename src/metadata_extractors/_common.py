"""
Helpers shared by the metadata extractors and the form.

The extractors use parse_xml to read vendor XML, and immersion_term,
imaging_mode_term and immersion_from_refractive_index to report values in
the form's terms. remind.py uses combine_image_metadata to describe a file
that holds several images.
"""

import xml.etree.ElementTree as ET
from collections import Counter

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

# Keys are OME acquisition mode names, which CZI also uses, and the short
# device names in OIR and LIF files. Values are the form's terms.
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


def parse_xml(text):
    """
    Parse XML text and remove the namespaces from every tag and attribute.

    For example, "{http://...}Pixels" becomes "Pixels", so elements can be
    found by their plain names.

    Args:
        text (str): the XML text.

    Returns:
        xml.etree.ElementTree.Element: the root element.

    Raises:
        xml.etree.ElementTree.ParseError: if the text is not well-formed XML.
    """
    root = ET.fromstring(text)
    for element in root.iter():
        element.tag = element.tag.split("}", 1)[-1]
        element.attrib = {name.split("}", 1)[-1]: value for name, value in element.attrib.items()}
    return root


def combine_image_metadata(per_image, name_key="Image Name"):
    """
    Describe all the images of one file in a single metadata dict.

    A file such as a LIF project can hold images taken with different
    settings. Reporting only the first or the most common value would hide
    that, so every distinct value is kept.

    Args:
        per_image (list[dict]): one metadata dict per image.
        name_key (str): the key that holds each image's name.

    Returns:
        dict: one entry per key, in the order the keys first appear. When
        every image has the same value, the entry is that value, and lists
        stay lists. Otherwise it is text that lists each distinct value, most
        common first, with the images it applies to. Up to three images are
        named; more are counted. For example:
        "63x/1.40 OIL [14 images]; 10x/0.40 DRY [Overview]". Only four values
        are listed; the rest are counted as "and N more values". With more
        than one image, "Image Count" and "Image Names" replace name_key.
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


def immersion_term(raw):
    """
    Translate an immersion medium from an image file into the form's term.

    Args:
        raw (str): the medium as the file writes it, e.g. "OIL", "Dry" or
            "WaterDipping". Matching ignores case, spaces, underscores and
            hyphens.

    Returns:
        str: the form's term, e.g. "Oil", "Air" or "Water". A medium that is
        not recognised, including "N/A" and "", is returned unchanged.
    """
    return _IMMERSION_TERMS.get(_lookup_key(raw), raw)


def imaging_mode_term(raw):
    """
    Translate an acquisition mode from an image file into the form's term.

    Args:
        raw (str): the mode as the file writes it, e.g.
            "LaserScanningConfocalMicroscopy", "LSM" or
            "SPINNING_DISK_CONFOCAL". Matching ignores case, spaces,
            underscores and hyphens.

    Returns:
        str: an "Imaging mode" option such as "Confocal" or "Widefield", or a
        "Specialist modality" option such as "STED", "TIRF" or "FLIM". A
        mode that is not recognised, including "N/A" and "", is returned
        unchanged.
    """
    return _IMAGING_MODE_TERMS.get(_lookup_key(raw), raw)


def immersion_from_refractive_index(refractive_index):
    """
    Return the immersion medium that a refractive index implies.

    This is for files that record the index but do not name the medium. Each
    common medium's index is matched with a small margin: air (1.0), water
    (1.33), silicone oil (1.40), glycerol (1.47) and immersion oil (1.515).

    Args:
        refractive_index (float | str): the index from the file.

    Returns:
        str: "Air", "Water", "Silicone", "Glycerol" or "Oil". "" for any other
        index, or for a value that is not a number.
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


def _display(value):
    """Return a metadata value as text, joining lists with ", "."""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _lookup_key(value):
    """Return value in upper case without spaces, underscores or hyphens, for matching."""
    return str(value).upper().replace("_", "").replace(" ", "").replace("-", "")
