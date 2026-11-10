"""
Read and write the ReadMe.txt file format used by ReMInD.

A ReadMe has up to three parts, in this order:

    # <comment lines, ignored when reading>

    Field label: value            one line per form field
    Notes:                        multi-line fields are wrapped in --- lines
    ---
    free text
    ---

    # Filename Key
    keyword -> group              one line per row

    # Extracted Image Metadata
    key: value                    one line per item, to the end of the file

Templates use the same format.

The same content can be saved as JSON; see format_json and parse_json.
"""

import json

MULTILINE_FIELDS = ("Notes",)

_SECTION_HEADINGS = ("# Filename Key", "# Extracted Image Metadata")

# Extracted metadata that is a list in memory and written as "a, b, c".
_LIST_METADATA = ("Channel Names", "Acquisition Modes")


def format_readme(header, fields, filename_key=(), metadata=None):
    """
    Build the text of a ReadMe.txt file.

    Args:
        header (str): first line of the file. Must start with "#" so it is
            ignored when the file is read back.
        fields (list[tuple[str, str]]): (label, value) for every form field,
            in the order they should appear. Empty values are written too.
        filename_key (list[tuple[str, str]]): (keyword, group) rows. The
            section is left out when there are none.
        metadata (dict | None): extracted image metadata. List values are
            written joined with ", ". The section is left out when the dict
            is empty or None.

    Returns:
        str: the file content, without a trailing newline.

    Values are written as they are. parse_readme cannot recover a single-line
    value that contains a line break, a keyword that contains " -> ", or
    multi-line text that contains a line reading exactly "# Filename Key" or
    "# Extracted Image Metadata".
    """
    lines = [header, ""]
    for label, value in fields:
        if label in MULTILINE_FIELDS:
            lines.append(f"{label}:\n---\n{value}\n---")
        else:
            lines.append(f"{label}: {value}")

    if filename_key:
        lines.append("\n# Filename Key")
        for keyword, group in filename_key:
            lines.append(f"{keyword} -> {group}")

    if metadata:
        lines.append("\n# Extracted Image Metadata")
        for key, value in metadata.items():
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            lines.append(f"{key}: {value}")

    return "\n".join(lines)


def parse_readme(text):
    """
    Read the text of a ReadMe.txt or template file.

    Args:
        text (str): the file content.

    Returns:
        tuple: (fields, filename_key, metadata)
            fields (dict): label -> value for every "label: value" line and
                every multi-line block before the first section heading.
                Labels are returned as written, whether or not the form has a
                field with that name. Fields with an empty value are left out.
            filename_key (list[tuple[str, str]]): (keyword, group) rows.
            metadata (dict): the extracted image metadata. All values are
                strings, except "Channel Names" and "Acquisition Modes",
                which are split back into lists when they hold several items.

    Lines that are blank, start with "#", or have no ": " separator are
    skipped. Text that is not a ReadMe at all therefore gives three empty
    results rather than an error.
    """
    lines = text.splitlines()
    fields = {}
    filename_key = []
    metadata = {}

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        if line == "# Filename Key":
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith("#"):
                row = lines[idx].strip()
                if " -> " in row:
                    keyword, group = row.split(" -> ", 1)
                    filename_key.append((keyword.strip(), group.strip()))
                idx += 1
            continue

        if line == "# Extracted Image Metadata":
            # This section runs to the end of the file, so a metadata value
            # that happens to start with "#" is not mistaken for a heading.
            for row in lines[idx + 1:]:
                row = row.strip()
                if ": " in row:
                    key, value = row.split(": ", 1)
                    if key in _LIST_METADATA and ", " in value:
                        value = value.split(", ")
                    metadata[key] = value
            break

        if line.endswith(":") and idx + 1 < len(lines) and lines[idx + 1].strip() == "---":
            label = line[:-1].strip()
            # The block runs to the last "---" before the next section, so
            # that a "---" line typed into the text does not end it early.
            end = next((i for i in range(idx + 2, len(lines)) if lines[i].strip() in _SECTION_HEADINGS),
                       len(lines))
            closing = max((i for i in range(idx + 2, end) if lines[i].strip() == "---"), default=end)
            fields[label] = "\n".join(lines[idx + 2:closing])
            idx = closing
        elif ": " in line and not line.startswith("#"):
            label, value = line.split(": ", 1)
            fields[label.strip()] = value.strip()
        idx += 1

    return fields, filename_key, metadata


def format_json(fields, filename_key=(), metadata=None):
    """
    Build the text of a JSON export.

    Takes the same arguments as format_readme, without the header. The result
    is one JSON object with the form fields as its members, followed by
    "Filename Key" (a list of {"keyword", "group"} objects) and "Extracted
    Image Metadata" (an object) when there are any.
    """
    data = dict(fields)
    if filename_key:
        data["Filename Key"] = [{"keyword": keyword, "group": group} for keyword, group in filename_key]
    if metadata:
        data["Extracted Image Metadata"] = metadata
    return json.dumps(data, indent=2)


def parse_json(text):
    """
    Read the text of a JSON export.

    Returns the same (fields, filename_key, metadata) as parse_readme. Fields
    with an empty value are left out, as they are there.

    Raises:
        ValueError: if the text is not a JSON object.
    """
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("The file does not hold a ReMInD JSON export.")
    filename_key = [(row["keyword"], row["group"]) for row in data.pop("Filename Key", [])]
    metadata = data.pop("Extracted Image Metadata", {})
    return {label: value for label, value in data.items() if value}, filename_key, metadata
