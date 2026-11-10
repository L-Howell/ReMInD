"""
Convert extracted image metadata into values for the ReMInD form.
"""

import re
from collections import Counter

try:
    from ._common import immersion_term, imaging_mode_term
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term


# An ISO 8601 date and time; any fraction of a second and time zone are dropped.
_ISO_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}).*$")


def _text(value):
    """
    Return a metadata value as display text, or "" if it holds no information.

    None, "" and "N/A" become "". Lists are joined with ", " after dropping
    items that hold no information.
    """
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(t for t in (_text(v) for v in value) if t)
    text = str(value).strip()
    return "" if text == "N/A" else text


def _first(value):
    if isinstance(value, (list, tuple)):
        return next((t for t in (_text(v) for v in value) if t), "")
    return _text(value)


def _channel_info(metadata):
    names = metadata.get("Channel Names")
    dyes = metadata.get("Dye Names")
    if not (isinstance(names, list) and isinstance(dyes, list) and len(names) == len(dyes)):
        return _text(names)
    labelled = []
    for name, dye in zip(names, dyes):
        name, dye = _text(name), _text(dye)
        labelled.append(f"{name} ({dye})" if name and dye and dye != name else name or dye)
    return ", ".join(label for label in labelled if label)


def _more_than_one(count):
    try:
        return "Yes" if int(float(count)) > 1 else "No"
    except (TypeError, ValueError):
        # Formats such as CZI and OIR leave a dimension out when it has a
        # single plane or time point, so the extractors report it as "N/A".
        return "No"


def metadata_to_form_fields(metadata):
    """
    Work out which ReMInD form fields can be filled from extracted metadata.

    Args:
        metadata (dict): the metadata of one image from any extractor. The
            keys read are "Document Creation Date", "System Name",
            "Objective Model", "Objective Medium", "Acquisition Modes",
            "Channel Names", "Dye Names", "Size Z" and "Size T". Other keys
            are ignored.

    Returns:
        dict: form field label -> text to put in that field. A field is
        included only when the metadata has a value for it, so the caller can
        leave every other field as the user had it. Missing keys, None, ""
        and "N/A" all count as no value.

        "Immersion" and the acquisition mode are translated to the form's
        terms where the value is recognised and passed through unchanged
        otherwise. When "Acquisition Modes" is a list (one per channel) the
        first usable item is used. It fills "Specialist modality" when it is
        STED, TIRF, FLIM or SoRa, and "Imaging mode" otherwise.

        "Date and time" has an ISO date rewritten as "YYYY-MM-DD HH:MM:SS",
        the format of the form's Now button; other date text is kept as it
        is. "Channel info" lists the channel names, each followed by its dye
        in brackets when "Dye Names" gives one that differs from the name.

        "Z-stack" and "Time series" are "Yes" when the size is above 1 and
        "No" otherwise; they are left out only when the size key is missing
        from the metadata altogether.
    """
    values = {
        "Date and time":   _ISO_DATE.sub(r"\1 \2", _text(metadata.get("Document Creation Date"))),
        "Microscope name": _text(metadata.get("System Name")),
        "Objective":       _text(metadata.get("Objective Model")),
        "Immersion":       immersion_term(_text(metadata.get("Objective Medium"))),
        "Channel info":    _channel_info(metadata),
    }
    mode = imaging_mode_term(_first(metadata.get("Acquisition Modes")))
    values["Specialist modality" if mode in ("STED", "TIRF", "FLIM", "SoRa") else "Imaging mode"] = mode
    if "Size Z" in metadata:
        values["Z-stack"] = _more_than_one(metadata["Size Z"])
    if "Size T" in metadata:
        values["Time series"] = _more_than_one(metadata["Size T"])
    return {label: value for label, value in values.items() if value}


def merge_form_fields(per_image):
    """
    Combine the form field values of several images into one set of values.

    Args:
        per_image (list[dict]): the result of metadata_to_form_fields for
            each image of a file.

    Returns:
        dict: form field label -> text. A field is included when at least one
        image has a value for it. Where the images agree the value is used as
        it is. Where they differ:
          - "Date and time" is the earliest value;
          - "Z-stack" and "Time series" become "Both" when some images are
            "Yes" and others "No";
          - any other field lists the distinct values, most common first,
            separated by "; ".
    """
    merged = {}
    for label in dict.fromkeys(label for image in per_image for label in image):
        counts = Counter(image[label] for image in per_image if label in image)
        values = [value for value, _ in counts.most_common()]
        if len(values) == 1:
            merged[label] = values[0]
        elif label == "Date and time":
            merged[label] = min(values)
        elif set(values) == {"Yes", "No"}:
            merged[label] = "Both"
        else:
            merged[label] = "; ".join(values)
    return merged
