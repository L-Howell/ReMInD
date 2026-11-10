"""
Extract metadata from Olympus/Evident OIR files using the oirfile library.
Returns key image, instrument, and channel metadata as a structured dictionary.
All numeric values are converted to standard units and rounded to 3 decimal places where appropriate.
"""

import os
import re
import xml.etree.ElementTree as ET
from oirfile import OirFile

try:
    from ._common import immersion_term, imaging_mode_term
except ImportError:  # allow running as a standalone script
    from _common import immersion_term, imaging_mode_term


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
        dict: the metadata
    """
    with OirFile(file_path) as oir:

        # --- Image dimensions ---
        sizes  = oir.sizes
        size_x = sizes.get('X', 'N/A')
        size_y = sizes.get('Y', 'N/A')
        size_z = sizes.get('Z', 'N/A')
        size_t = sizes.get('T', 'N/A')
        size_c = sizes.get('C', 'N/A')

        # Channel names from coordinate array — matches image data. A file
        # with a single channel has no channel axis; it is named further down.
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
                # The file gives a Z step even when no Z-stack was taken.
                if pz and 'Z' in sizes: pixel_size_z = _safe_round(pz)
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
        # <base:deviceName> gives the imaging modality (e.g. "LSM", "WIDEFIELD")
        raw_mode = _find_text(roots, 'deviceName', 'acquisitionMode', 'modality')
        acq_mode = imaging_mode_term(raw_mode)

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
        objective_str = ' '.join(parts) if parts else 'N/A'

        immersion = immersion_term(imm_raw)

        # --- Channel wavelengths and pinhole sizes ---
        # Imaging channels live under <commonimage:phase>/<commonphase:group>/<commonphase:channel>.
        excitation_wavelengths = ['N/A'] * num_channels
        emission_wavelengths   = ['N/A'] * num_channels
        pinhole_sizes          = ['N/A'] * num_channels

        for root in roots:
            ch_data = []
            seen_ids = set()
            for group_el in root.findall('.//phase/group'):
                for ch_el in group_el.findall('channel'):
                    # Each channel is described twice, the second time
                    # without its detection band.
                    if ch_el.get('id') in seen_ids:
                        continue
                    seen_ids.add(ch_el.get('id'))
                    # Emission: detection band, e.g. "430-470". A lambda scan
                    # has no fixed band.
                    wl_el = ch_el.find('.//wavelengthRange')
                    try:
                        em_str = (f"{int(float(wl_el.findtext('startWavelength')))}-"
                                  f"{int(float(wl_el.findtext('endWavelength')))}")
                    except (AttributeError, TypeError, ValueError):
                        em_str = 'N/A'

                    # Excitation: laser wavelengths from the laserDataId values,
                    # e.g. "LD405_65792Imaging_main_phase_1" → 405. A channel
                    # can use several lasers.
                    lasers = [m.group(1) for m in
                              (re.search(r'LD(\d+)', el.text or '') for el in ch_el.findall('laserDataId')) if m]
                    ex_wl = int(lasers[0]) if len(lasers) == 1 else ', '.join(lasers) or 'N/A'

                    ph = ch_el.findtext('.//pinholeDiameter')
                    ch_data.append({
                        'name':       ch_el.findtext('name') or 'N/A',
                        'excitation': ex_wl,
                        'emission':   em_str,
                        'pinhole':    _safe_round(ph) if ph else 'N/A',
                    })

            if ch_data:
                if ch_coord is None and len(ch_data) > 1:
                    # One channel was saved but several are described, and
                    # the file does not say which one it is.
                    break
                if ch_coord is None:
                    channel_names = [ch_data[0]['name']]
                excitation_wavelengths = [d['excitation'] for d in ch_data[:num_channels]]
                emission_wavelengths   = [d['emission']   for d in ch_data[:num_channels]]
                pinhole_sizes          = [d['pinhole']    for d in ch_data[:num_channels]]
                break

        # Dye set for each channel, from the <lsmimage:channel> blocks.
        dye_by_channel = {root.findtext('name'): root.findtext('dyeName')
                          for root in roots if root.tag == 'lsmChannel'}
        dye_names = [dye_by_channel.get(name) or 'N/A' for name in channel_names]

        attrs = oir.attrs or {}

        metadata_output = {
            "Document Creation Date":   acq_date,
            "System Name":              system_name,
            "Objective Model":          objective_str,
            "Objective NA":             obj_na,
            "Objective Magnification":  _safe_round(obj_mag, 1) if obj_mag != 'N/A' else 'N/A',
            "Objective Medium":         immersion,
            "Acquisition Modes":        acq_mode,
            "Channel Names":            channel_names,
            "Dye Names":                dye_names,
            "Excitation Wavelengths":   excitation_wavelengths,
            "Emission Wavelength Range (nm)": emission_wavelengths,
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

        return metadata_output
