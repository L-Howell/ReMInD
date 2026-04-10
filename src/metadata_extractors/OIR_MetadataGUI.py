"""
Extract metadata from Olympus/Evident OIR files using the oirfile library.
Returns key image, instrument, and channel metadata as a structured dictionary.
All numeric values are converted to standard units and rounded to 3 decimal places where appropriate.
"""

import os
import re
import xml.etree.ElementTree as ET
from oirfile import OirFile


_IMMERSION_MAP = {
    "OIL":      "Oil-23",
    "WATER":    "Water",
    "AIR":      "Air",
    "DRY":      "Air",
    "GLYCEROL": "Glycerol",
    "SILICONE": "Silicone",
}

_ACQ_MODE_MAP = {
    "LSM":       "Confocal",
    "CONFOCAL":  "Confocal",
    "WIDEFIELD": "Widefield",
    "STED":      "STED",
    "TIRF":      "TIRF",
}


def _parse_strip_ns(xml_str):
    """
    Parse XML string and strip namespace URIs from all tag and attribute names.
    e.g. '{http://...}systemName' → 'systemName'
    Parsing before stripping avoids errors from namespace-prefixed attributes (xsi:type etc.).
    """
    root = ET.fromstring(xml_str)
    for el in root.iter():
        if '{' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
        el.attrib = {
            (k.split('}', 1)[1] if '{' in k else k): v
            for k, v in el.attrib.items()
        }
    return root


def _parse_all_xml(xml_metadata):
    """Parse every XML block in xml_metadata, returning a list of namespace-stripped roots."""
    roots = []
    for xml_list in xml_metadata.values():
        for xml_str in xml_list:
            try:
                roots.append(_parse_strip_ns(xml_str))
            except Exception:
                continue
    return roots


def _find_text(roots, *tag_paths, default="N/A"):
    """Search all roots for the first matching tag path. Returns stripped text or default."""
    for root in roots:
        for path in tag_paths:
            el = root.find(f'.//{path}')
            if el is not None and el.text and el.text.strip():
                return el.text.strip()
    return default


def _safe_round(val, decimals=3):
    """Round a value to N decimals if possible, else return as is."""
    try:
        return round(float(val), decimals)
    except Exception:
        return val


def extract_oir_metadata(file_path):
    """
    Extract metadata from an Olympus/Evident .oir file.

    Returns:
        tuple: (metadata_output_dict, raw_attrs_dict)
    """
    with OirFile(file_path) as oir:

        # --- Image dimensions ---
        sizes  = oir.sizes
        size_x = sizes.get('X', 'N/A')
        size_y = sizes.get('Y', 'N/A')
        size_z = sizes.get('Z', 'N/A')
        size_t = sizes.get('T', 'N/A')
        size_c = sizes.get('C', 'N/A')

        # Channel names from coordinate array — matches image data
        ch_coord      = oir.coords.get('C')
        channel_names = [str(c) for c in ch_coord] if ch_coord is not None else ['N/A']
        num_channels  = len(channel_names)

        # Datetime is exposed directly
        acq_date = oir.datetime if oir.datetime else 'N/A'

        # --- Parse XML metadata blocks ---
        roots = _parse_all_xml(oir.xml_metadata)

        # --- Pixel sizes ---
        # <commonphase:length> children <commonparam:x/y/z> are in µm, confirmed by
        # sibling <commonphase:pixelUnit> tags (value = MICRO_METER). All channels
        # report identical values; use the first <length> found.
        pixel_size_x = pixel_size_y = pixel_size_z = 'N/A'
        for root in roots:
            length_el = root.find('.//length')
            if length_el is not None:
                px = length_el.findtext('x')
                py = length_el.findtext('y')
                pz = length_el.findtext('z')
                if px: pixel_size_x = _safe_round(px)
                if py: pixel_size_y = _safe_round(py)
                if pz: pixel_size_z = _safe_round(pz)
                break

        # --- Image field of view in µm ---
        def _fov(size, px):
            try:    return round(float(size) * float(px), 3)
            except: return 'N/A'

        image_size_x = _fov(size_x, pixel_size_x)
        image_size_y = _fov(size_y, pixel_size_y)
        image_size_z = _fov(size_z, pixel_size_z)

        # --- System / microscope name ---
        # <base:systemName> = instrument model (e.g. "FV4000/FV5000")
        # → mapped to "Microscope name" form field via "System Name" key
        system_name = _find_text(roots, 'systemName')

        # --- Acquisition mode ---
        # <base:deviceName> gives the imaging modality (e.g. "LSM", "WIDEFIELD"), mapped via _ACQ_MODE_MAP
        raw_mode = _find_text(roots, 'deviceName', 'acquisitionMode', 'modality')
        acq_mode = _ACQ_MODE_MAP.get(raw_mode.upper(), raw_mode) if raw_mode != 'N/A' else 'N/A'

        # --- Objective ---
        # All objective fields live as direct children of <commonimage:objectiveLens>
        obj_display = _find_text(roots, 'objectiveLens/displayName', 'objectiveLens/name')
        obj_mag     = _find_text(roots, 'objectiveLens/magnification')
        obj_na_raw  = _find_text(roots, 'objectiveLens/naValue')
        imm_raw     = _find_text(roots, 'objectiveLens/immersion')

        obj_na = _safe_round(obj_na_raw) if obj_na_raw != 'N/A' else 'N/A'

        parts = []
        if obj_display != 'N/A':
            parts.append(obj_display)
        if obj_mag != 'N/A':
            try:
                parts.append(f"{int(float(obj_mag))}x")
            except Exception:
                parts.append(obj_mag)
        if obj_na != 'N/A':
            parts.append(f"NA {obj_na}")
        objective_str = '  '.join(parts) if parts else 'N/A'

        immersion = _IMMERSION_MAP.get(imm_raw.upper(), imm_raw) if imm_raw != 'N/A' else 'N/A'

        # --- Channel wavelengths and pinhole sizes ---
        # Imaging channels live under <commonimage:phase>/<commonphase:group>/<commonphase:channel>.
        excitation_wavelengths = ['N/A'] * num_channels
        emission_wavelengths   = ['N/A'] * num_channels
        pinhole_sizes          = ['N/A'] * num_channels

        for root in roots:
            ch_data = []
            for group_el in root.findall('.//phase/group'):
                for ch_el in group_el.findall('channel'):
                    wl_el = ch_el.find('.//wavelengthRange')
                    if wl_el is None:
                        continue

                    # Emission: detection band expressed as a range, e.g. "(430, 470)"
                    start = wl_el.findtext('startWavelength')
                    end   = wl_el.findtext('endWavelength')
                    if start and end:
                        try:
                            em_str = f"({int(float(start))}, {int(float(end))})"
                        except (ValueError, TypeError):
                            em_str = 'N/A'
                    else:
                        em_str = 'N/A'

                    # Excitation: laser wavelength from laserDataId
                    # e.g. "LD405_65792Imaging_main_phase_1" → 405
                    laser_id = ch_el.findtext('laserDataId') or ''
                    match = re.search(r'LD(\d+)', laser_id)
                    ex_wl = int(match.group(1)) if match else 'N/A'

                    ph = ch_el.findtext('.//pinholeDiameter')
                    ch_data.append({
                        'excitation': ex_wl,
                        'emission':   em_str,
                        'pinhole':    _safe_round(ph) if ph else 'N/A',
                    })

            if ch_data:
                excitation_wavelengths = [d['excitation'] for d in ch_data[:num_channels]]
                emission_wavelengths   = [d['emission']   for d in ch_data[:num_channels]]
                pinhole_sizes          = [d['pinhole']    for d in ch_data[:num_channels]]
                break

        attrs = oir.attrs or {}

        metadata_output = {
            "Document Creation Date":   acq_date,
            "Document User Name":       'N/A',
            "System Name":              system_name,
            "Objective Model":          objective_str,
            "Objective NA":             obj_na,
            "Objective Magnification":  _safe_round(obj_mag, 1) if obj_mag != 'N/A' else 'N/A',
            "Objective Medium":         immersion,
            "Acquisition Modes":        acq_mode,
            "Channel Names":            channel_names,
            "Excitation Wavelengths":   excitation_wavelengths,
            "Emission Wavelengths":     emission_wavelengths,
            "Pinhole Diameters (um)":   pinhole_sizes,
            "Size X":                   size_x,
            "Size Y":                   size_y,
            "Size Z":                   size_z,
            "Size T":                   size_t,
            "Size C":                   size_c,
            "Pixel Size X (um)":        pixel_size_x,
            "Pixel Size Y (um)":        pixel_size_y,
            "Pixel Size Z (um)":        pixel_size_z,
            "Image Size X (um)":        image_size_x,
            "Image Size Y (um)":        image_size_y,
            "Image Size Z (um)":        image_size_z,
            "Bits Per Sample":          attrs.get('bitspersample', 'N/A'),
            "File Name":                os.path.basename(file_path),
        }

        return metadata_output, attrs
