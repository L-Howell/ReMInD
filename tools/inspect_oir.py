"""
OIR Metadata Inspector
Run: python inspect_oir.py path/to/your/file.oir

Dumps all metadata exposed by oirfile to the console and writes each
XML block to a separate file (oir_xml_block_<n>.xml) for easy inspection.
"""

import sys
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom

def pretty_xml(xml_str):
    try:
        return xml.dom.minidom.parseString(xml_str).toprettyxml(indent="  ")
    except Exception:
        return xml_str

def main(filepath):
    from oirfile import OirFile

    print(f"\n{'='*60}")
    print(f"FILE: {filepath}")
    print(f"{'='*60}\n")

    with OirFile(filepath) as oir:

        # --- Basic image structure ---
        print("--- dims / sizes ---")
        print(f"  dims:  {oir.dims}")
        print(f"  shape: {oir.shape}")
        print(f"  sizes: {oir.sizes}")
        print(f"  dtype: {oir.dtype}")
        print()

        # --- Datetime ---
        print("--- datetime ---")
        print(f"  {oir.datetime!r}")
        print()

        # --- Attributes (attrs) ---
        print("--- attrs ---")
        for k, v in (oir.attrs or {}).items():
            print(f"  {k!r}: {v!r}")
        print()

        # --- Channels ---
        print("--- channels ---")
        for ch in (oir.channels or []):
            print(f"  {ch}")
        print()

        # --- Coords ---
        print("--- coords (physical axes) ---")
        for dim, arr in (oir.coords or {}).items():
            if arr is not None and len(arr) > 0:
                preview = list(arr[:5])
                suffix = "..." if len(arr) > 5 else ""
                print(f"  {dim}: first values = {preview}{suffix}  (len={len(arr)})")
                if len(arr) > 1:
                    try:
                        step = float(arr[1]) - float(arr[0])
                        print(f"       step = {step:.6g}  (likely units: µm for X/Y/Z, s for T)")
                    except (ValueError, TypeError):
                        print(f"       (non-numeric axis — string labels)")
            else:
                print(f"  {dim}: empty or None")
        print()

        # --- XML metadata blocks ---
        xml_blocks = oir.xml_metadata or {}
        print(f"--- xml_metadata ({len(xml_blocks)} block type(s)) ---")

        out_dir = os.path.dirname(os.path.abspath(filepath))
        written = []

        for block_id, xml_list in xml_blocks.items():
            print(f"\n  Block ID: {block_id!r}  ({len(xml_list)} string(s))")
            for i, xml_str in enumerate(xml_list):
                out_name = f"oir_xml_block_{block_id}_part{i}.xml"
                out_path = os.path.join(out_dir, out_name)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(pretty_xml(xml_str))
                written.append(out_path)
                print(f"    → Written to: {out_name}")

                # Print a flat list of all tags and their text content
                try:
                    root = ET.fromstring(xml_str)
                    print(f"    Tags with text content:")
                    for el in root.iter():
                        text = (el.text or "").strip()
                        if text:
                            # Build simple path
                            print(f"      <{el.tag}>: {text!r}")
                except Exception as e:
                    print(f"    Could not parse XML: {e}")

    print(f"\n{'='*60}")
    print(f"XML files written ({len(written)} total):")
    for p in written:
        print(f"  {p}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_oir.py <path_to_file.oir>")
        sys.exit(1)
    main(sys.argv[1])
