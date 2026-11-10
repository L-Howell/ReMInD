"""
ReMInD - Recommended Metadata Interface for Documentation

Copyright (C) 2025  Nicholas Condon (IMB Microscopy, The University of Queensland)
Copyright (C) 2025-2026  Liam Howell (Sydney Microscopy and Microanalysis,
                                      The University of Sydney)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. See the LICENSE file for details.

This is a derivative work. It originated from ReMInD by Nicholas Condon and has
been modified and extended (OIR support, dark mode, single unified application),
and is maintained independently from v3.0.0 onward by Liam Howell.
"""

import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.font as tkfont
import datetime
import os
import glob
import tkinter.ttk as ttk
import sys
import json

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Updated imports to look in metadata_extractors subfolder
try:
    from metadata_extractors.CZI_MetadataGUI import extract_metadata
    from metadata_extractors.LIF_MetadataGUI import extract_lif_metadata
    from metadata_extractors.Nd2_v2a import extract_nd2_metadata, map_nd2_to_remind_fields
    from metadata_extractors.OIR_MetadataGUI import extract_oir_metadata
    from metadata_extractors.OMETiff_MetadataGUI import extract_ometiff_metadata
    from metadata_extractors._common import most_common_metadata
    from metadata_extractors.field_mapping import metadata_to_form_fields
    from readme_io import MULTILINE_FIELDS, format_readme, parse_readme
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the metadata_extractors folder contains the required files")
    sys.exit(1)

import sv_ttk

# Module-level flag read by ToolTip to choose tooltip colours at hover time
_dark_mode = False

APP_NAME = "ReMInD"
APP_VERSION = "3.0.0"
APP_AUTHOR = "Nicholas Condon, IMB Microscopy, The University of Queensland, Brisbane Australia; Liam Howell, Sydney Microscopy and Microanalysis, The University of Sydney, Sydney Australia"
APP_DATE = "June 2026"

# (label, dropdown options or "" for a text box, tooltip). The dropdowns also
# accept typed text, so the options are suggestions rather than limits.
FORM_FIELDS = [
    ("Experiment name", "", "Title of the experiment."),
    ("Storage Location", "", "Where the raw data is stored, e.g. a data repository / shared drive or project name"),
    ("Date and time", "", "Date and time of acquisition. The Now button will autopopulate the fields"),
    ("Experimentor Name(s)", "", "Enter your full name."),
    ("Sample Information", "", "e.g. Sample ID, or cell line, animal strain"),
    ("Genetic Modifications", "", "e.g. eGFP- mCherry-y"),
    ("Antibody or probes", "", "e.g. Alexa488-Phalloidin, DAPI, Alexa647-GaM"),
    ("Fixation / Live Media", "", "Fixation method used, or details of live imaging reagents"),
    ("Sample Carrier", "", "e.g. 35mm Dish, #1.5 coverslip, chamber slide"),
    ("Mounting medium", "", "e.g. Prolong Gold, Mowiol, PBS, glycerol"),
    ("Microscope name", "", "e.g. Confocal 5"),
    ("Objective", "", "Objective lens details. e.g. Plan Apochromat 63x 1.4NA"),
    ("Immersion", ["Air", "Water", "Immersol W", "Glycerol", "Silicone", "Oil-23", "Oil-37"], "Select the immersion used."),
    ("Imaging mode", ["Confocal", "Widefield", "Spinning Disc Confocal", "Lightsheet", "Lattice Lightsheet", "2Photon"], "Select the imaging mode used."),
    ("Specialist modality", ["Airyscan", "STED", "FLIM", "SoRa", "TIRF"], "Select any specialist imaging modality used."),
    ("Environmental Conditions", "", "e.g. Temperature and CO2"),
    ("Channel info", "", "Channel names, stains or labels used."),
    ("Z-stack", ["Yes", "No", "Both"], "Was a Z-stack acquired?"),
    ("Time series", ["Yes", "No", "Both"], "Was a time-lapse series acquired?"),
    ("Image format", "", "Image file format (e.g., .czi, .tif, .lif, .oir)."),
    ("Notes", "", "Analysis intent or relevant notes."),
]


def _read_lif(path):
    """Return one metadata dict for a LIF file, which can hold many images."""
    per_image = extract_lif_metadata(path)
    if not per_image:
        raise ValueError("No images found in LIF file.")
    # The first image is often an overview, so use the most common value of
    # each item rather than the first.
    return most_common_metadata(per_image)


# File extension -> (format name, function returning the metadata dict for a
# file, function turning that dict into form field values).
IMAGE_READERS = {
    ".czi":  ("CZI", extract_metadata, metadata_to_form_fields),
    ".lif":  ("LIF", _read_lif, metadata_to_form_fields),
    ".nd2":  ("ND2", extract_nd2_metadata, map_nd2_to_remind_fields),
    ".oir":  ("OIR", extract_oir_metadata, metadata_to_form_fields),
    ".tif":  ("OME-TIFF", extract_ometiff_metadata, metadata_to_form_fields),
    ".tiff": ("OME-TIFF", extract_ometiff_metadata, metadata_to_form_fields),
}


def application_folder():
    """
    Return the folder that holds ReMInD: the folder of ReMInD.exe for a built
    executable, or the folder of this file when run from source.

    Templates are looked up here rather than in the working directory, which
    is somewhere else when the program is started from a shortcut.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return current_dir


def find_templates(folder):
    return sorted(glob.glob(os.path.join(glob.escape(folder), "*_ReadME_template.txt")))


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tooltip or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.geometry(f"+{x}+{y}")
        tip_bg = "#3a3a3a" if _dark_mode else "#ffffe0"
        tip_fg = "#e8e8e8" if _dark_mode else "black"
        label = tk.Label(self.tooltip, text=self.text, justify='left',
                         background=tip_bg, foreground=tip_fg,
                         relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class REMBIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Recommended Metadata Interface for Documentation - {APP_NAME} v{APP_VERSION}")

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate appropriate window size - make it narrower
        if screen_width >= 1920:
            window_width = 900
            window_height = 700
        elif screen_width >= 1366:
            window_width = 750
            window_height = 650
        else:
            window_width = 650
            window_height = 600
    
        # Don't exceed 80% of screen size
        window_width = min(window_width, int(screen_width * 0.8))
        window_height = min(window_height, int(screen_height * 0.8))
        
        # Center the window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set window geometry and make it resizable
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(600, 500)  # Reduced minimum size
    
        # Make the window scrollable if content exceeds window size
        self.setup_scrollable_window()

        self.entries = {}
        self.text_fields = {}
        self.last_metadata_output = {}
        # Content of the template loaded at startup, if any. Clear Form
        # returns to these values.
        self.template_fields = {}
        self.template_filename_key = []

        # Font size management - adjust based on screen size
        base_size = 10 if screen_width >= 1920 else 9 if screen_width >= 1200 else 8
        self.base_font_size = base_size
        self.font_family = "Segoe UI"
        self.app_font = tkfont.Font(family=self.font_family, size=self.base_font_size)
        self.bold_font = tkfont.Font(family=self.font_family, size=self.base_font_size, weight="bold")

        self.fields = FORM_FIELDS

        self.build_form()
        # Start in dark mode by default (user can switch with the toggle).
        self.toggle_dark_mode()
        self.root.after(200, self.load_startup_template)

    def build_form(self):
        # Use self.form_root instead of self.root for all grid operations
        parent = self.form_root if hasattr(self, 'form_root') else self.root
        
        self.row_counter = 0
        for label, options, tooltip_text in self.fields:
            tk.Label(parent, text=label, font=self.app_font).grid(row=self.row_counter, column=0, sticky="e", padx=5, pady=2)

            if isinstance(options, list):
                var = tk.StringVar()
                combo = ttk.Combobox(parent, textvariable=var, values=options, state="normal", font=self.app_font, style="TCombobox")
                combo.grid(row=self.row_counter, column=1, padx=5, pady=2, sticky="ew")
                self.entries[label] = var
                ToolTip(combo, tooltip_text)
                # Without this the wheel changes the selected value of a
                # dropdown the pointer happens to be over.
                for wheel_event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    combo.bind(wheel_event, self.scroll_form)

            elif label == "Date and time":
                frame = tk.Frame(parent)
                frame.grid(row=self.row_counter, column=1, padx=5, pady=2, sticky="ew")

                date_entry = tk.Entry(frame)
                date_entry.pack(side="left", fill="x", expand=True)
                self.entries[label] = date_entry
                ToolTip(date_entry, tooltip_text)

                def insert_datetime(entry_widget=date_entry):
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, now)

                timestamp_btn = tk.Button(frame, text="Now", command=insert_datetime, font=self.app_font)
                timestamp_btn.pack(side="right", padx=5)
                ToolTip(timestamp_btn, "Insert current date and time")

            elif label in MULTILINE_FIELDS:
                frame = tk.Frame(parent)
                frame.grid(row=self.row_counter, column=1, padx=5, pady=2, sticky="ew")

                text_box = tk.Text(frame, height=8, width=50, font=self.app_font)  # Reduced height for small screens
                text_box.pack(side="left", fill="both", expand=True)
                self.entries[label] = text_box
                self.text_fields[label] = text_box
                ToolTip(text_box, tooltip_text)

                def insert_timestamp():
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    text_box.insert(tk.END, f"\n[{now}] ")

                timestamp_btn = tk.Button(frame, text="Timestamp", command=insert_timestamp, font=self.app_font)
                timestamp_btn.pack(side="right", padx=5, pady=5)
                ToolTip(timestamp_btn, "Insert timestamp into notes")

            else:
                entry = tk.Entry(parent, font=self.app_font)
                entry.grid(row=self.row_counter, column=1, padx=5, pady=2, sticky="ew")
                self.entries[label] = entry
                ToolTip(entry, tooltip_text)

            self.row_counter += 1

        # Configure column weights for proper resizing
        parent.grid_columnconfigure(1, weight=1)

        # --- Filename Key: map a filename keyword to a biological group/treatment ---
        self.condition_frame = tk.LabelFrame(parent, text="Filename Key", font=self.bold_font)
        self.condition_frame.grid(row=self.row_counter, column=0, columnspan=2, sticky="ew", padx=5, pady=(2, 8))
        self.condition_frame.grid_columnconfigure(0, weight=1)
        self.condition_frame.grid_columnconfigure(1, weight=1)
        self.row_counter += 1

        tk.Label(self.condition_frame,
                 text="Link a keyword in your filenames to the group it identifies.\n"
                      "Each keyword must be unique to one group (appear only in that group's file names).",
                 font=self.app_font, justify="left").grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 2))
        tk.Label(self.condition_frame, text="Filename keyword",
                 font=self.bold_font).grid(row=1, column=0, sticky="w", padx=6)
        tk.Label(self.condition_frame, text="Group / treatment",
                 font=self.bold_font).grid(row=1, column=1, sticky="w", padx=6)

        self.condition_rows_frame = tk.Frame(self.condition_frame)
        self.condition_rows_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2)
        self.condition_rows_frame.grid_columnconfigure(0, weight=1)
        self.condition_rows_frame.grid_columnconfigure(1, weight=1)

        # Two empty rows by default; users add more with the + button.
        self.condition_rows = []
        self.add_condition_row()
        self.add_condition_row()

        tk.Button(self.condition_frame, text="+ Add row", command=self.add_condition_row,
                  font=self.app_font).grid(row=3, column=0, sticky="w", padx=6, pady=(2, 4))

        # Add a scrollable, read-only text widget for metadata display
        self.metadata_frame = tk.Frame(parent)
        self.metadata_frame.grid(row=self.row_counter, column=0, columnspan=2, sticky="nsew", padx=5, pady=(0, 10))

        tk.Label(self.metadata_frame, text="Extracted Image Metadata:").pack(anchor="w")

        self.metadata_text = tk.Text(self.metadata_frame, height=8, width=80, wrap="none", state="disabled")  # Reduced height
        self.metadata_text.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(self.metadata_frame, command=self.metadata_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.metadata_text.config(yscrollcommand=scrollbar.set)

        self.row_counter += 1

        # Place the Load Fields from Image File button on its own row above the rest
        loadfields_frame = tk.Frame(parent)
        loadfields_frame.grid(row=self.row_counter + 1, column=0, columnspan=2, pady=(0, 5))
        tk.Button(loadfields_frame, text="Load Fields from Image File", command=self.load_fields_from_image, font=self.app_font).pack(side="left", padx=5)

        # Main button row - make buttons smaller for low res
        button_frame = tk.Frame(parent)
        button_frame.grid(row=self.row_counter + 2, column=0, columnspan=2, pady=10)

        # Create buttons in a more compact layout
        buttons = [
            ("Generate ReadMe.txt", self.generate_readme),
            ("Load ReadMe.txt", self.load_existing),
            ("Clear Form", self.clear_form),
            ("Help", self.show_help),
            ("Export as JSON", self.export_as_json),
        ]

        # Arrange buttons in two rows if screen is narrow
        screen_width = self.root.winfo_screenwidth()
        if screen_width < 1366:  # Small screen
            # First row
            row1_frame = tk.Frame(button_frame)
            row1_frame.pack(pady=2)
            for text, command in buttons[:4]:
                tk.Button(row1_frame, text=text, command=command, font=self.app_font).pack(side="left", padx=2)

            # Second row
            row2_frame = tk.Frame(button_frame)
            row2_frame.pack(pady=2)
            for text, command in buttons[4:]:
                tk.Button(row2_frame, text=text, command=command, font=self.app_font).pack(side="left", padx=2)
        else:
            # Single row for larger screens
            for text, command in buttons:
                tk.Button(button_frame, text=text, command=command, font=self.app_font).pack(side="left", padx=5)

        # Dark mode toggle — top-right corner, outside the scrollable area
        self.dark_mode_btn = tk.Button(self.header_frame, text="Dark",
                                       command=self.toggle_dark_mode, font=self.app_font)
        self.dark_mode_btn.pack(side="right", padx=8, pady=3)

        version_label = tk.Label(parent, text=f"{APP_NAME} v{APP_VERSION}  —  {APP_DATE}", fg="gray")
        version_label.grid(row=self.row_counter + 3, column=0, columnspan=2, pady=(0, 5))

    def setup_scrollable_window(self):
        """Create a scrollable main window for low resolution screens"""
        # Thin header bar at the very top (holds the dark mode toggle)
        self.header_frame = tk.Frame(self.root)
        self.header_frame.pack(side="top", fill="x")

        # Create main canvas and scrollbar below the header
        self.main_canvas = tk.Canvas(self.root)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = tk.Frame(self.main_canvas)

        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )

        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack canvas and scrollbar
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bound for every widget so the form scrolls wherever the pointer is.
        self.root.bind_all("<MouseWheel>", self.scroll_form)  # Windows
        self.root.bind_all("<Button-4>", self.scroll_form)    # Linux
        self.root.bind_all("<Button-5>", self.scroll_form)    # Linux

        # Update the root reference for form building
        self.form_root = self.scrollable_frame

    def scroll_form(self, event):
        """Scroll the form in response to a mouse wheel event."""
        widget = event.widget
        # Text boxes and open dropdown lists scroll their own content. Tk
        # reports a dropdown list as a path string, not a widget object.
        if isinstance(widget, str) or widget.winfo_class() == "Text":
            return None
        if widget.winfo_toplevel() is not self.root:
            return None
        if event.num in (4, 5):
            steps = -1 if event.num == 4 else 1
        else:
            steps = int(-event.delta / 120)
        self.main_canvas.yview_scroll(steps, "units")
        return "break"

    def field_values(self):
        values = []
        for label, _, _ in self.fields:
            if label in self.text_fields:
                values.append((label, self.text_fields[label].get("1.0", tk.END).strip()))
            else:
                values.append((label, self.entries[label].get()))
        return values

    def set_field(self, label, value):
        """Replace the content of a form field. Labels the form does not have
        are ignored, so files written by other versions still load."""
        widget = self.entries.get(label)
        if widget is None:
            return
        if label in self.text_fields:
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value)
        elif isinstance(widget, tk.StringVar):
            widget.set(value)
        else:
            widget.delete(0, tk.END)
            widget.insert(0, value)

    def default_filename(self, suffix):
        """Return "<experiment name>_<suffix>", or just the suffix when the
        experiment name is empty. Characters that are not letters, digits,
        spaces, hyphens or underscores are dropped from the name."""
        name = self.entries["Experiment name"].get().strip()
        clean_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return f"{clean_name}_{suffix}" if clean_name else suffix

    def readme_text(self):
        return format_readme(
            f"# Generated by {APP_NAME} v{APP_VERSION} — {APP_AUTHOR}, {APP_DATE}",
            self.field_values(),
            self.get_condition_rows(),
            self.last_metadata_output,
        )

    def generate_readme(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 initialfile=self.default_filename("ReadME.txt"),
                                                 filetypes=[("Text files", "*.txt")],
                                                 title="Save ReadMe.txt as")
        if not save_path:
            return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(self.readme_text())
        except Exception as e:
            messagebox.showerror("Error", f"Could not write file: {e}")

    def load_existing(self):
        path = filedialog.askopenfilename(title="Select existing ReadMe.txt", filetypes=[("Text files", "*.txt")])
        if not path:
            return
        self.parse_readme_file(path)

    def clear_form(self):
        """Empty the form, then put back the template's values if a template
        was loaded at startup."""
        for label, _, _ in self.fields:
            self.set_field(label, "")
        self.fill_form(self.template_fields, self.template_filename_key, {})

    def add_condition_row(self, keyword="", group=""):
        """Append a (filename keyword -> group/treatment) row to the Filename Key table."""
        r = len(self.condition_rows)
        left = tk.Entry(self.condition_rows_frame, font=self.app_font)
        right = tk.Entry(self.condition_rows_frame, font=self.app_font)
        if keyword:
            left.insert(0, keyword)
        if group:
            right.insert(0, group)
        left.grid(row=r, column=0, sticky="ew", padx=2, pady=1)
        right.grid(row=r, column=1, sticky="ew", padx=2, pady=1)
        ToolTip(left, "Text that appears only in this group's file names, so it uniquely identifies the group, e.g. 'B' or 'ctrl'")
        ToolTip(right, "What that group is, e.g. '10 uM Drug Y' or 'Vehicle control'")
        # Match the current theme for rows added after dark mode is enabled.
        if getattr(self, "dark_mode", False):
            for e in (left, right):
                e.configure(bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff")
        self.condition_rows.append((left, right))
        return left, right

    def get_condition_rows(self):
        """Return [(keyword, group), ...] for rows whose keyword is non-empty."""
        pairs = []
        for left, right in self.condition_rows:
            keyword = left.get().strip()
            group = right.get().strip()
            if keyword:
                pairs.append((keyword, group))
        return pairs

    def _reset_condition_rows(self, rows=None):
        """Replace all Filename Key rows with the given list, padding to >= 2 rows."""
        for left, right in self.condition_rows:
            left.destroy()
            right.destroy()
        self.condition_rows = []
        for keyword, group in (rows or []):
            self.add_condition_row(keyword, group)
        while len(self.condition_rows) < 2:
            self.add_condition_row()

    def read_readme_file(self, path):
        """Return (fields, filename_key, metadata) from a ReadMe.txt or
        template file, or None after showing a message if it cannot be read."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return parse_readme(f.read())
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file: {e}")
            return None

    def fill_form(self, fields, filename_key, metadata):
        """
        Put the content of a ReadMe.txt into the form.

        Fields with a value replace what is in the form; fields that are
        empty or absent are left as they are. The Filename Key and the
        extracted image metadata are replaced, and emptied if there are none.
        """
        for label, value in fields.items():
            self.set_field(label, value)
        self._reset_condition_rows(filename_key)
        self.show_metadata_in_window(metadata)

    def parse_readme_file(self, path):
        content = self.read_readme_file(path)
        if content:
            self.fill_form(*content)

    def load_template(self, path):
        """Load a template into the form and keep its content for Clear Form."""
        content = self.read_readme_file(path)
        if not content:
            return
        # The metadata is dropped: a template made by renaming a real ReadMe
        # still carries that experiment's image metadata, which must not be
        # written into the ReadMe of every later experiment.
        self.template_fields, self.template_filename_key, _ = content
        self.fill_form(self.template_fields, self.template_filename_key, {})

    def load_startup_template(self):
        """Load the template stored next to the program, if there is one.
        With several, the first in alphabetical order is used."""
        templates = find_templates(application_folder())
        if templates:
            self.load_template(templates[0])

    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Help / Info")
        help_window.geometry("1000x650")  # Made taller to accommodate acknowledgements

        help_text = tk.Text(help_window, wrap="word", font=("Segoe UI", 10), width=80, height=35)
        help_text.pack(expand=True, fill="both", padx=10, pady=10)

        help_text.insert("1.0", "📄 ReMInD - Recommended Metadata Interface for Documentation Help\n\n", "title")
        help_text.insert("end", "This tool was originally created by Nicholas Condon (IMB Microscopy, The University of Queensland) in 2025, and is now developed and maintained independently by Liam Howell (Sydney Microscopy and Microanalysis, The University of Sydney).\n\n")
        help_text.insert("end", "The purpose of this tool is to help capture additional metadata to store with your RAW experimental data.\n\n")
        
        help_text.insert("end", "✒️ Entering Information \n", "subtitle")
        help_text.insert("end", "\t• Not every field needs to be filled in.\n")
        help_text.insert("end", "\t• Enter where your raw data is stored (e.g. a data repository or project name) in the 'Storage Location' field.\n")
        help_text.insert("end", "\t• Hover your cursor over the text box for more description for the field.\n")
        help_text.insert("end", "\t• Some fields contain drop down lists you can choose items from. If none of the items fit, type your own value into the box.\n")
        help_text.insert("end", "\t• The notes box can be filled in with as much detail as possible. You can use the 'Timestamp' button to generate a new line with the date and time.\n\n")

        help_text.insert("end", "🔑 Filename Key \n", "subtitle")
        help_text.insert("end", "\t• Use the 'Filename Key' table to record what the labels in your file names mean.\n")
        help_text.insert("end", "\t• In the left box, enter a keyword that appears in the file names for a group (e.g. 'B' or 'ctrl').\n")
        help_text.insert("end", "\t• The keyword must be unique to that group — it should appear only in that group's file names, not in any other group's.\n")
        help_text.insert("end", "\t• In the right box, enter the matching biological group or treatment (e.g. '10 uM Drug Y' or 'Vehicle control').\n")
        help_text.insert("end", "\t• Click '+ Add row' for as many groups as you need. The key is saved in the ReadMe.txt and JSON exports.\n\n")

        help_text.insert("end", "🔬 Load Fields from Image File \n", "subtitle")
        help_text.insert("end", "\t• Click 'Load Fields from Image File' to automatically extract metadata from your image files.\n")
        help_text.insert("end", "\t• Supported formats: CZI (Zeiss), LIF (Leica), ND2 (Nikon), OIR (Olympus/Evident), and OME-TIFF files.\n")
        help_text.insert("end", "\t• The tool will automatically populate relevant fields with metadata from the image file including:\n")
        help_text.insert("end", "\t\t- Date and time of acquisition\n")
        help_text.insert("end", "\t\t- Microscope name and settings\n")
        help_text.insert("end", "\t\t- Objective lens information\n")
        help_text.insert("end", "\t\t- Channel information\n")
        help_text.insert("end", "\t\t- Imaging parameters (Z-stack, time series)\n")
        help_text.insert("end", "\t\t- Software and system information\n")
        help_text.insert("end", "\t• Extracted metadata will be displayed in the 'Extracted Image Metadata' section.\n")
        help_text.insert("end", "\t• You can review and edit the imported information before generating your ReadMe file.\n")
        help_text.insert("end", "\t• The raw metadata is also included when exporting as JSON or generating ReadMe files.\n\n")
        
        help_text.insert("end", "💾 Generate ReadMe.txt\n", "subtitle")
        help_text.insert("end", "\t• Once you have filled in the form to your liking you can save a ReadMe.txt file to any location (ideally within the data folder it's associated with).\n")
        help_text.insert("end", "\t• Save the ReadMe.txt file alongside the captured data.\n")
        help_text.insert("end", "\t• Use a filename that includes 'ReadMe' and the experiment name if needed.\n")
        help_text.insert("end", "\t• If you imported metadata from an image file, the raw metadata will be appended to the ReadMe file.\n\n")
        
        help_text.insert("end", "📂 Load ReadMe.txt\n", "subtitle")
        help_text.insert("end", "\t• The program has the ability to read a previously generated ReadMe file and repopulate the fields for quick editing/updating.\n")
        help_text.insert("end", "\t• This can be particularly useful when adding to the notes section.\n\n")
        
        help_text.insert("end", "📖 Templates \n", "subtitle")
        help_text.insert("end", "\t• The program automatically looks for any template files stored in the same location as the executable.\n")
        help_text.insert("end", "\t• Any template file must be saved as *_ReadMe_template.txt with something in place of the *.\n")
        help_text.insert("end", "\t• The template is loaded automatically, and 'Clear Form' returns to its values.\n")
        help_text.insert("end", "\t• If the template sets the microscope name, loading an image file does not change it.\n")
        help_text.insert("end", "\t• Keep one template per computer. If there are several, the first in alphabetical order is used.\n\n")
        
        help_text.insert("end", "📁 Export as JSON\n", "subtitle")
        help_text.insert("end", "\t• Export all form data and extracted metadata as a structured JSON file.\n")
        help_text.insert("end", "\t• Useful for data processing, analysis workflows, or integration with other tools.\n")
        help_text.insert("end", "\t• Includes both form entries and raw extracted image metadata.\n\n")
        
        help_text.insert("end", "📌 Tips:\n", "subtitle")
        help_text.insert("end", "\t• Use a previously generated ReadMe.txt file as a template to pre-load certain fields such as Storage Location, Name, Sample information etc.\n")
        help_text.insert("end", "\t• If you're iterating on an experiment, consider labeling your files like ReadMe_exp1_v1.txt, v2, etc.\n")
        help_text.insert("end", "\t• Be descriptive: When entering experiment details, use full names, reagent IDs, microscope configurations, etc.\n")
        help_text.insert("end", "\t• Always load metadata from your original image files first, then supplement with additional information.\n")
        help_text.insert("end", "\t• Review imported metadata for accuracy - some fields may need manual correction or additional detail.\n")
        help_text.insert("end", "\t• Use the metadata extraction feature to ensure consistency across multiple experiments.\n\n")

        help_text.insert("end", "🙏 Acknowledgements\n", "subtitle")
        help_text.insert("end", "This tool uses several open-source libraries for metadata extraction:\n\n")
        help_text.insert("end", "\t• pylibCZIrw by ZEISS - For reading Zeiss CZI files\n")
        help_text.insert("end", "\t\t  https://github.com/ZEISS/pylibczirw\n\n")
        help_text.insert("end", "\t• readlif by Nimesh Khadka - For reading Leica LIF files\n")
        help_text.insert("end", "\t\t  https://github.com/nimne/readlif\n\n")
        help_text.insert("end", "\t• nd2 by Talley Lambert - For reading Nikon ND2 files\n")
        help_text.insert("end", "\t\t  https://github.com/tlambert03/nd2\n\n")
        help_text.insert("end", "\t• oirfile by Christoph Gohlke - For reading Olympus/Evident OIR files\n")
        help_text.insert("end", "\t\t  https://github.com/cgohlke/oirfile\n\n")
        help_text.insert("end", "\t• ome-types by Talley Lambert - For reading OME-TIFF files\n")
        help_text.insert("end", "\t\t  https://github.com/tlambert03/ome-types\n\n")
        help_text.insert("end", "\t• Python standard libraries: tkinter, json, datetime, os, glob\n\n")
        help_text.insert("end", "Special thanks to the open-source community for making microscopy metadata\n")
        help_text.insert("end", "accessible and standardized across different imaging platforms.\n\n")
        help_text.insert("end", "For support or feature requests, please open an issue at https://github.com/L-Howell/ReMInD.")

        help_text.tag_configure("title", font=("Segoe UI", 12, "bold"))
        help_text.tag_configure("subtitle", font=("Segoe UI", 10, "bold"))
        help_text.config(state="disabled")


    def load_fields_from_image(self):
        filetypes = [
            ("Image files", "*.czi *.lif *.nd2 *.oir *.tif *.tiff"),
            ("All files", "*.*"),
        ]
        path = filedialog.askopenfilename(
            title="Select an image file to extract metadata",
            filetypes=filetypes
        )
        if path:
            self.load_image_file(path)

    def load_image_file(self, path):
        """
        Fill the form from an image file's metadata and show the metadata.

        Only fields the file has a value for are changed. The microscope name
        is also left alone when the template supplied one, because the
        facility's own name for the instrument is more useful than the model
        name stored in the file (which still appears in the extracted
        metadata). Unsupported file types and unreadable files show a message
        and change nothing.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext not in IMAGE_READERS:
            messagebox.showinfo("Not Supported", "Only CZI, LIF, ND2, OIR and OME-TIFF files are supported for metadata extraction at this time.")
            return

        format_name, read_metadata, to_form_fields = IMAGE_READERS[ext]
        try:
            metadata = read_metadata(path)
            form_values = to_form_fields(metadata)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract {format_name} metadata:\n{e}")
            return

        if self.template_fields.get("Microscope name"):
            form_values.pop("Microscope name", None)
        for label, value in form_values.items():
            self.set_field(label, value)
        self.set_field("Image format", ext)
        self.show_metadata_in_window(metadata)

    def show_metadata_in_window(self, metadata_dict):
        """Make metadata_dict the extracted image metadata: it is shown in
        the metadata box and written to the ReadMe and JSON exports. An empty
        dict clears it."""
        self.last_metadata_output = metadata_dict
        self.metadata_text.config(state="normal")
        self.metadata_text.delete("1.0", tk.END)
        for k, v in metadata_dict.items():
            if isinstance(v, list):
                v = ", ".join(str(i) for i in v)
            self.metadata_text.insert(tk.END, f"{k}: {v}\n")
        self.metadata_text.config(state="disabled")

    def toggle_dark_mode(self):
        global _dark_mode
        # Main window colours
        dark_bg  = "#1e1e1e"
        dark_fg  = "#e8e8e8"
        # Combobox colours
        entry_bg = "#2d2d2d"
        entry_fg = "#ffffff"
        highlight = "#3a3a3a"

        if not getattr(self, "dark_mode", False):
            # --- Switch to dark ---
            sv_ttk.set_theme("dark")
            self.root.configure(bg=dark_bg)
            for w in self.root.winfo_children():
                self._set_widget_dark(w, dark_bg, dark_fg, entry_bg, entry_fg, highlight)
            self.dark_mode = True
            _dark_mode = True
            if hasattr(self, "dark_mode_btn"):
                self.dark_mode_btn.configure(text="Light")
        else:
            # --- Switch to light ---
            sv_ttk.set_theme("light")
            self.root.configure(bg="SystemButtonFace")
            for w in self.root.winfo_children():
                self._set_widget_light(w)
            self.dark_mode = False
            _dark_mode = False
            if hasattr(self, "dark_mode_btn"):
                self.dark_mode_btn.configure(text="Dark")

        self._apply_theme_to_titlebar()

    def _apply_theme_to_titlebar(self):
        """Give the Windows title bar the dark or light style of the app
        theme. Does nothing on other systems, or on Windows versions that
        have no dark title bar."""
        if sys.platform != "win32":
            return
        try:
            self.root.update()  # the window needs a handle before it can be styled
            window = ctypes.windll.user32.GetParent(self.root.winfo_id())
            dark = ctypes.c_int(1 if self.dark_mode else 0)
            # 20 is DWMWA_USE_IMMERSIVE_DARK_MODE.
            ctypes.windll.dwmapi.DwmSetWindowAttribute(window, 20, ctypes.byref(dark), ctypes.sizeof(dark))
            if sys.getwindowsversion().build < 22000:
                # Windows 10 repaints the title bar only when the window changes.
                self.root.wm_attributes("-alpha", 0.99)
                self.root.wm_attributes("-alpha", 1)
        except Exception:
            pass

    def _set_widget_dark(self, widget, bg, fg, entry_bg, entry_fg, highlight):
        cls = widget.__class__.__name__
        if cls in ["Frame", "LabelFrame"]:
            widget.configure(bg=bg)
        elif cls == "Canvas":
            widget.configure(bg=bg, highlightbackground=bg)
        elif cls == "Label":
            widget.configure(bg=bg, fg=fg)
        elif cls == "Entry":
            widget.configure(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        elif cls == "Text":
            widget.configure(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        elif cls == "Button":
            widget.configure(bg=highlight, fg=fg, activebackground=bg, activeforeground=fg)
        elif cls == "Toplevel":
            widget.configure(bg=bg)
        elif cls == "Scrollbar":
            widget.configure(bg=bg, troughcolor=highlight)
        # ttk.Combobox colours are handled by sv-ttk; skip here
        for child in widget.winfo_children():
            self._set_widget_dark(child, bg, fg, entry_bg, entry_fg, highlight)

    def _set_widget_light(self, widget):
        """Recursively reset all widgets to system default (light) colours."""
        cls = widget.__class__.__name__
        if cls in ["Frame", "LabelFrame", "Toplevel"]:
            widget.configure(bg="SystemButtonFace")
        elif cls == "Canvas":
            widget.configure(bg="SystemButtonFace", highlightbackground="SystemButtonFace")
        elif cls == "Label":
            widget.configure(bg="SystemButtonFace", fg="black")
        elif cls == "Entry":
            widget.configure(bg="white", fg="black", insertbackground="black")
        elif cls == "Text":
            widget.configure(bg="white", fg="black", insertbackground="black")
        elif cls == "Button":
            widget.configure(bg="SystemButtonFace", fg="black",
                             activebackground="SystemButtonFace", activeforeground="black")
        elif cls == "Scrollbar":
            widget.configure(bg="SystemButtonFace")
        for child in widget.winfo_children():
            self._set_widget_light(child)

    def export_as_json(self):
        data = dict(self.field_values())

        # Add the Filename Key (keyword -> group/treatment) if any rows are filled
        condition_pairs = self.get_condition_rows()
        if condition_pairs:
            data["Filename Key"] = [{"keyword": k, "group": g} for k, g in condition_pairs]

        if self.last_metadata_output:
            data["Extracted Image Metadata"] = self.last_metadata_output

        save_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 initialfile=self.default_filename("metadata.json"),
                                                 filetypes=[("JSON files", "*.json")],
                                                 title="Save as JSON")
        if not save_path:
            return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not write JSON file: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = REMBIGUI(root)
    root.mainloop()

