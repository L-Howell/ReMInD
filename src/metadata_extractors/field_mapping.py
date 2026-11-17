"""
Turn extracted image metadata into values for the ReMInD form.

remind.py passes each image's metadata from an extractor to
metadata_to_form_fields. For a file with several images, it then combines
the results with merge_form_fields.
"""

import re
from collections import Counter

try:
    from ._common import immersion_term, imaging_mode_term
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term


# An ISO 8601 date and time. Any fraction of a second and the time zone are dropped.
_ISO_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}).*$")


def metadata_to_form_fields(metadata):
    """
    Work out which form fields can be filled from one image's metadata.

    Immersion and the acquisition mode are translated into the form's terms
    when they are recognised, and passed through unchanged otherwise. The
    first usable acquisition mode fills "Specialist modality" when it is
    STED, TIRF, FLIM or SoRa, and "Imaging mode" otherwise. An ISO date is
    rewritten as "YYYY-MM-DD HH:MM:SS", the format of the form's Now button.
    Other date text is kept as it is.

    Args:
        metadata (dict): one image's metadata from any extractor. Only these
            keys are read: "Document Creation Date", "System Name",
            "Objective Model", "Objective Medium", "Acquisition Modes",
            "Channel Names", "Dye Names", "Excitation Wavelengths", "Size Z"
            and "Size T".

    Returns:
        dict: form field label -> text. A field is included only when the
        metadata has a value for it, so the caller can leave every other
        field as the user had it. A missing key, None, "" and "N/A" all count
        as no value. "Z-stack" and "Time series" are "Yes" when the size is
        above 1 and "No" otherwise. They are left out only when the metadata
        has no size key at all.
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
        image has a value for it. Where every image has the same value, it is used.
        Where they differ, "Date and time" is the earliest value, and
        "Z-stack" and "Time series" are "Both" when some images are "Yes"
        and others "No". Any other field lists the distinct values, most
        common first, separated by "; ".
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


def _channel_info(metadata):
    """Describe the channels as "<excitation> (<target>)", e.g. "405 (DAPI), 561 (mCherry)"."""
    names = metadata.get("Channel Names")
    if not isinstance(names, list):
        return _text(names)
    dyes = _per_channel(metadata, "Dye Names", len(names))
    wavelengths = _per_channel(metadata, "Excitation Wavelengths", len(names))
    channels = []
    for name, dye, wavelength in zip(names, dyes, wavelengths):
        target = dye or _text(name)
        try:
            wavelength = str(round(float(wavelength)))  # stored as e.g. 488.0
        except ValueError:
            pass  # empty, or several lasers such as "405/488"
        channels.append(f"{wavelength} ({target})" if wavelength and target else wavelength or target)
    return ", ".join(channel for channel in channels if channel)


def _text(value):
    """Return a metadata value as text, with None, "N/A" and empty items as ""."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(t for t in (_text(v) for v in value) if t)
    text = str(value).strip()
    return "" if text == "N/A" else text


def _first(value):
    """Return the first item of a list that holds a value, as text."""
    if isinstance(value, (list, tuple)):
        return next((t for t in (_text(v) for v in value) if t), "")
    return _text(value)


def _per_channel(metadata, key, count):
    """Return a per-channel list as text, or blanks if it has the wrong length."""
    values = metadata.get(key)
    if isinstance(values, list) and len(values) == count:
        return [_text(value) for value in values]
    return [""] * count


def _more_than_one(count):
    """Return "Yes" if a size is above 1, and "No" otherwise."""
    try:
        return "Yes" if int(float(count)) > 1 else "No"
    except (TypeError, ValueError):
        return "No"  # a size that is not a number, such as "N/A"
