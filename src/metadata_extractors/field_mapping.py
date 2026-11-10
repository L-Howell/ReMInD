"""
Convert extracted image metadata into values for the ReMInD form.
"""

try:
    from ._common import immersion_term, imaging_mode_term
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term


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
        metadata (dict): output of a CZI, LIF, OIR or OME-TIFF extractor. The
            keys read are "Document Creation Date", "System Name",
            "Objective Model", "Objective Medium", "Acquisition Modes",
            "Channel Names", "Size Z" and "Size T". Other keys are ignored.

    Returns:
        dict: form field label -> text to put in that field. A field is
        included only when the metadata has a value for it, so the caller can
        leave every other field as the user had it. Missing keys, None, ""
        and "N/A" all count as no value.

        "Immersion" and the acquisition mode are translated to the form's
        terms where the value is recognised and passed through unchanged
        otherwise. When "Acquisition Modes" is a list (one per channel) the
        first usable item is used. It fills "Specialist modality" when it is
        STED, TIRF or FLIM, and "Imaging mode" otherwise.

        "Z-stack" and "Time series" are "Yes" when the size is above 1 and
        "No" otherwise; they are left out only when the size key is missing
        from the metadata altogether.
    """
    values = {
        "Date and time":   _text(metadata.get("Document Creation Date")),
        "Microscope name": _text(metadata.get("System Name")),
        "Objective":       _text(metadata.get("Objective Model")),
        "Immersion":       immersion_term(_text(metadata.get("Objective Medium"))),
        "Channel info":    _text(metadata.get("Channel Names")),
    }
    mode = imaging_mode_term(_first(metadata.get("Acquisition Modes")))
    values["Specialist modality" if mode in ("STED", "TIRF", "FLIM") else "Imaging mode"] = mode
    if "Size Z" in metadata:
        values["Z-stack"] = _more_than_one(metadata["Size Z"])
    if "Size T" in metadata:
        values["Time series"] = _more_than_one(metadata["Size T"])
    return {label: value for label, value in values.items() if value}
