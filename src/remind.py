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
import datetime
import os
import glob
import tkinter.ttk as ttk
import sys

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from metadata_extractors._common import combine_image_metadata
from metadata_extractors.field_mapping import metadata_to_form_fields, merge_form_fields
from readme_io import MULTILINE_FIELDS, format_json, format_readme, parse_json, parse_readme
from theme import HINT_COLOUR, apply_theme
from version import RELEASE_DATE, VERSION

APP_NAME = "ReMInD"
APP_VERSION = VERSION
APP_AUTHOR = "Nicholas Condon, IMB Microscopy, The University of Queensland, Brisbane Australia; Liam Howell, Sydney Microscopy and Microanalysis, The University of Sydney, Sydney Australia"
APP_DATE = RELEASE_DATE

# (label, dropdown options or "" for a text box, tooltip). The dropdowns also
# accept typed text, so the options are suggestions rather than limits.
FORM_FIELDS = [
    ("Experiment name", "", "Title of the experiment, e.g. Drug screen, plate 2"),
    ("Storage Location", "", "Where the raw data is stored, e.g. a data repository / shared drive or project name"),
    ("Date and time", "", "Date and time of acquisition. The Now button will autopopulate the fields"),
    ("Experimenter Name(s)", "", "Full name of everyone who acquired the data, e.g. Alex Researcher"),
    ("Sample Information", "", "e.g. Sample ID, or cell line, animal strain"),
    ("Genetic Modifications", "", "e.g. eGFP- mCherry-y"),
    ("Antibody or probes", "", "e.g. Alexa488-Phalloidin, DAPI, Alexa647-GaM"),
    ("Fixation / Live Media", "", "Fixation method used, or details of live imaging reagents,\ne.g. 4% PFA 15 min, or live in FluoroBrite + 10% FBS"),
    ("Sample Carrier", "", "e.g. 35mm Dish, #1.5 coverslip, chamber slide"),
    ("Mounting medium", "", "e.g. Prolong Gold, Mowiol, PBS, glycerol"),
    ("Microscope name", "", "e.g. Confocal 5"),
    ("Objective", "", "Objective lens details. e.g. Plan Apochromat 63x 1.4NA"),
    ("Immersion", ["Air", "Water", "Immersol W", "Glycerol", "Silicone", "Oil-23", "Oil-37"], "Select the immersion used."),
    ("Imaging mode", ["Confocal", "Widefield", "Spinning Disc Confocal", "Lightsheet", "Lattice Lightsheet", "2Photon"], "Select the imaging mode used."),
    ("Specialist modality", ["Airyscan", "STED", "FLIM", "SoRa", "TIRF"], "Select any specialist imaging modality used."),
    ("Environmental Conditions", "", "e.g. Temperature and CO2"),
    ("Channel info", "", "Excitation wavelength and target of each channel, in order of acquisition,\ne.g. 405 (DAPI), 488 (GFP-tubulin), 561 (mCherry)"),
    ("Z-stack", ["Yes", "No", "Both"], "Was a Z-stack acquired?"),
    ("Time series", ["Yes", "No", "Both"], "Was a time-lapse series acquired?"),
    ("Image format", "", "Image file format (e.g., .czi, .tif, .lif, .oir)."),
    ("Notes", "", "Analysis intent or relevant notes."),
]

# Below this width of the form area the cards are stacked in one column.
TWO_COLUMN_WIDTH = 1050

# Card title -> (row, column, rows spanned, columns spanned) in the two-column
# layout. In one column the cards are stacked in the order listed here.
CARD_PLACES = {
    "Experiment": (0, 0, 1, 1),
    "Sample": (1, 0, 1, 1),
    "Microscope and acquisition": (0, 1, 2, 1),
    "Notes": (2, 0, 1, 1),
    "Filename Key": (2, 1, 1, 1),
    "Extracted Image Metadata": (3, 0, 1, 2),
}

# First field of each section of the form -> section heading.
SECTION_HEADINGS = {
    "Experiment name": "Experiment",
    "Sample Information": "Sample",
    "Microscope name": "Microscope and acquisition",
    "Notes": "Notes",
}


# Each reader imports its library when it is first used, not when the program
# starts. A library that fails to load then only stops its own file format
# from being read, and the window opens sooner.
def _read_czi(path):
    from metadata_extractors.czi_metadata import extract_czi_metadata
    return [extract_czi_metadata(path)]


def _read_lif(path):
    from metadata_extractors.lif_metadata import extract_lif_metadata
    return extract_lif_metadata(path)


def _read_nd2(path):
    from metadata_extractors.nd2_metadata import extract_nd2_metadata
    return [extract_nd2_metadata(path)]


def _read_oir(path):
    from metadata_extractors.oir_metadata import extract_oir_metadata
    return [extract_oir_metadata(path)]


def _read_ome_tiff(path):
    from metadata_extractors.ome_tiff_metadata import extract_ometiff_metadata
    return extract_ometiff_metadata(path)


# File extension -> (format name, function returning one metadata dict per
# image in a file).
IMAGE_READERS = {
    ".czi":  ("CZI", _read_czi),
    ".lif":  ("LIF", _read_lif),
    ".nd2":  ("ND2", _read_nd2),
    ".oir":  ("OIR", _read_oir),
    ".tif":  ("OME-TIFF", _read_ome_tiff),
    ".tiff": ("OME-TIFF", _read_ome_tiff),
}


def resource_path(name):
    """Return the path of a file shipped with the program: inside the
    unpacked executable when built, at the top of the repository otherwise."""
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(current_dir)), name)


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


class HintEntry(ttk.Entry):
    """
    A text field that shows a grey example while it is empty and does not
    have the keyboard focus. The example is display only: get() returns ""
    while it is shown.
    """

    def __init__(self, parent, hint, **options):
        super().__init__(parent, **options)
        self.hint = hint
        self.showing_hint = False
        self.bind("<FocusIn>", lambda event: self._hide_hint())
        self.bind("<FocusOut>", lambda event: self._show_hint())
        self._show_hint()

    def _show_hint(self):
        if not self.showing_hint and not super().get():
            self.showing_hint = True
            super().insert(0, self.hint)
            self.configure(foreground=HINT_COLOUR)

    def _hide_hint(self):
        if self.showing_hint:
            self.showing_hint = False
            super().delete(0, tk.END)
            self.configure(foreground="")

    def get(self):
        return "" if self.showing_hint else super().get()

    def delete(self, first, last=None):
        self._hide_hint()
        super().delete(first, last)

    def insert(self, index, text):
        self._hide_hint()
        super().insert(index, text)
        if self.focus_get() is not self:
            self._show_hint()


def field_hint(tooltip_text):
    """Return the example to show inside an empty field: the "e.g." part of
    its tooltip, or "" if the tooltip gives no example."""
    position = tooltip_text.find("e.g.")
    return tooltip_text[position:].replace("\n", " ") if position >= 0 else ""


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
        x = self.widget.winfo_rootx() + 25
        # Just below a one-line field; tall text boxes get it near their top.
        y = self.widget.winfo_rooty() + min(self.widget.winfo_height(), 30) + 2
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        ttk.Label(self.tooltip, text=self.text, justify="left",
                  relief="solid", borderwidth=1, padding=(4, 2)).pack()
        # Keep the tooltip on screen for widgets near the right edge.
        self.tooltip.update_idletasks()
        x = max(0, min(x, self.widget.winfo_screenwidth() - self.tooltip.winfo_reqwidth()))
        self.tooltip.geometry(f"+{x}+{y}")

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class RemindApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Recommended Metadata Interface for Documentation - {APP_NAME} v{APP_VERSION}")
        try:
            self.root.iconbitmap(resource_path("ReMInD.ico"))
        except tk.TclError:
            pass  # .ico files are only understood on Windows
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

        # Capped at 85% of the screen so the window fits on small displays.
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1360, int(screen_width * 0.85))
        window_height = min(900, int(screen_height * 0.85))
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.fields = FORM_FIELDS
        self.entries = {}
        self.text_fields = {}
        self.field_labels = {}
        self.dropdowns = []
        self.filled_from_image = set()
        self.last_metadata_output = {}
        # Content of the template loaded at startup, if any. Clear Form
        # returns to these values.
        self.template_fields = {}
        self.template_filename_key = []

        self.build_toolbar()
        self.setup_scrollable_window()
        self.build_form()
        self.show_metadata_in_window({})

        self.dark_mode = False
        self.toggle_dark_mode()  # start in dark mode

        # The toolbar does not wrap, so the window must stay wide enough for it.
        self.root.update_idletasks()
        self.root.minsize(self.toolbar.winfo_reqwidth(), 400)

        self.mark_saved()
        self.root.after(200, self.load_startup_template)

    def build_toolbar(self):
        """Create the row of action buttons, which stays visible while the
        form below it scrolls."""
        self.toolbar = ttk.Frame(self.root, padding=(12, 10, 12, 6), style="Band.TFrame")
        self.toolbar.pack(side="top", fill="x")

        def button(text, command, tooltip_text, side="left", accent=False):
            widget = ttk.Button(self.toolbar, text=text, command=command,
                                style="Accent.TButton" if accent else "TButton")
            widget.pack(side=side, padx=(0, 6) if side == "left" else (6, 0))
            ToolTip(widget, tooltip_text)
            return widget

        def gap():
            ttk.Frame(self.toolbar, width=14, style="Band.TFrame").pack(side="left")

        # Left to right in the order they are used: bring information in,
        # then save it.
        button("Load Fields from Image File", self.load_fields_from_image,
               "Fill in fields from the metadata stored in a CZI, LIF, ND2, OIR or OME-TIFF file")
        button("Load ReadMe.txt", self.load_existing,
               "Open a ReadMe.txt or JSON export saved earlier to edit or reuse it")
        gap()
        button("Generate ReadMe.txt", self.generate_readme,
               "Save this form as a ReadMe.txt, ideally next to the data it describes", accent=True)
        button("Export as JSON", self.export_as_json,
               "Save this form and the image metadata as a JSON file for other software")
        gap()
        button("Clear Form", self.clear_form,
               "Empty the form. Values from this computer's template are put back")

        self.dark_mode_btn = button("Dark", self.toggle_dark_mode, "Switch between dark and light", side="right")
        button("Help", self.show_help, "", side="right")

        # Says what the last action did, since success is not shown in a popup.
        self.status_label = ttk.Label(
            self.root, padding=(14, 0, 14, 10), style="Band.TLabel",
            text="Start by loading an image file, or fill in the form by hand.")
        self.status_label.pack(side="top", fill="x")
        ttk.Separator(self.root, orient="horizontal").pack(side="top", fill="x")

    def setup_scrollable_window(self):
        """Create the scrolling area that holds the form."""
        self.main_canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        self.scrollable_frame = ttk.Frame(self.main_canvas, padding=12, style="Page.TFrame")
        frame_id = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )

        def fit_form(event):
            two_columns = event.width >= TWO_COLUMN_WIDTH
            self.arrange_cards(two_columns)
            # Very long fields are hard to read, so the form stops growing at
            # a maximum width and is then centred.
            width = min(event.width, 1500 if two_columns else 920)
            self.main_canvas.itemconfigure(frame_id, width=width)
            self.main_canvas.coords(frame_id, (event.width - width) // 2, 0)

        self.main_canvas.bind("<Configure>", fit_form)

        # Bound for every widget so the form scrolls wherever the pointer is.
        self.root.bind_all("<MouseWheel>", self.scroll_form)  # Windows
        self.root.bind_all("<Button-4>", self.scroll_form)    # Linux
        self.root.bind_all("<Button-5>", self.scroll_form)    # Linux

    def card(self, title, subtitle=""):
        """Create a bordered panel with a heading for one section of the
        form, and return it. arrange_cards puts it in place."""
        frame = ttk.Frame(self.scrollable_frame, style="Card.TFrame", padding=(16, 12, 16, 16))
        heading = ttk.Frame(frame)
        heading.pack(fill="x", pady=(0, 10))
        ttk.Label(heading, text=title, style="Heading.TLabel").pack(side="left")
        if subtitle:
            ttk.Label(heading, text=subtitle, style="Muted.TLabel").pack(side="left", padx=(10, 0))
        self.cards[title] = frame
        return frame

    def arrange_cards(self, two_columns):
        """Lay the cards out in two columns, or in one for a narrow window."""
        if two_columns == self.two_columns:
            return
        self.two_columns = two_columns
        parent = self.scrollable_frame
        parent.grid_columnconfigure(0, weight=1, uniform="column")
        parent.grid_columnconfigure(1, weight=1 if two_columns else 0, uniform="column" if two_columns else "")
        for title, (row, column, rowspan, columnspan) in CARD_PLACES.items():
            if two_columns:
                self.cards[title].grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan,
                                       sticky="nsew", pady=(0, 12),
                                       padx=(0, 12) if column == 0 and columnspan == 1 else 0)
            else:
                self.cards[title].grid(row=list(CARD_PLACES).index(title), column=0, rowspan=1, columnspan=1,
                                       sticky="nsew", pady=(0, 12), padx=0)
        self.version_label.grid(row=len(CARD_PLACES), column=0, columnspan=2 if two_columns else 1)

    def build_form(self):
        self.cards = {}
        self.two_columns = None
        # The same label width in every section keeps the fields lined up.
        label_width = max(len(label) for label, _, _ in self.fields)

        for label, options, tooltip_text in self.fields:
            if label in SECTION_HEADINGS:
                section = ttk.Frame(self.card(SECTION_HEADINGS[label]))
                section.pack(fill="both", expand=True)
                section.grid_columnconfigure(1, weight=1)
            row = section.grid_size()[1]

            if label in MULTILINE_FIELDS:
                text_box = tk.Text(section, height=7, wrap="word", font="TkTextFont", padx=8, pady=6)
                text_box.grid(row=row, column=0, columnspan=2, sticky="nsew")
                section.grid_rowconfigure(row, weight=1)
                self.entries[label] = text_box
                self.text_fields[label] = text_box
                ToolTip(text_box, tooltip_text)

                def insert_timestamp(text_box=text_box):
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    text_box.insert(tk.END, f"\n[{now}] ")

                timestamp_btn = ttk.Button(section, text="Insert timestamp", command=insert_timestamp)
                timestamp_btn.grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(8, 0))
                ToolTip(timestamp_btn, "Add the current date and time to the notes")
                continue

            self.field_labels[label] = ttk.Label(section, text=label, width=label_width, anchor="e")
            self.field_labels[label].grid(row=row, column=0, sticky="e", padx=(0, 10), pady=3)

            if isinstance(options, list):
                var = tk.StringVar()
                widget = ttk.Combobox(section, textvariable=var, values=options)
                widget.grid(row=row, column=1, pady=3, sticky="ew")
                self.entries[label] = var
                self.dropdowns.append(widget)
                # Without this the wheel changes the selected value of a
                # dropdown the pointer happens to be over.
                for wheel_event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    widget.bind(wheel_event, self.scroll_form)
                widget.bind("<<ComboboxSelected>>", lambda event, label=label: self.unmark_field(label))

            elif label == "Date and time":
                frame = ttk.Frame(section)
                frame.grid(row=row, column=1, pady=3, sticky="ew")

                widget = HintEntry(frame, "YYYY-MM-DD HH:MM:SS")
                widget.pack(side="left", fill="x", expand=True)
                self.entries[label] = widget

                def insert_datetime(entry_widget=widget, label=label):
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, now)
                    self.unmark_field(label)

                timestamp_btn = ttk.Button(frame, text="Now", command=insert_datetime)
                timestamp_btn.pack(side="right", padx=(6, 0))
                ToolTip(timestamp_btn, "Insert current date and time")

            else:
                widget = HintEntry(section, field_hint(tooltip_text))
                widget.grid(row=row, column=1, pady=3, sticky="ew")
                self.entries[label] = widget

            ToolTip(widget, tooltip_text)
            # Once the user types in a field its value is no longer the one
            # read from the image.
            widget.bind("<Key>", lambda event, label=label: self.unmark_field(label), add="+")

        # --- Filename Key: map a filename keyword to a biological group/treatment ---
        key_card = self.card("Filename Key", "Link a keyword in your file names to the group it identifies")
        self.condition_rows_frame = ttk.Frame(key_card)
        self.condition_rows_frame.pack(fill="x")
        for column, heading in enumerate(("Filename keyword", "Group / treatment")):
            self.condition_rows_frame.grid_columnconfigure(column, weight=1, uniform="key")
            ttk.Label(self.condition_rows_frame, text=heading, style="Muted.TLabel"
                      ).grid(row=0, column=column, sticky="w", padx=2, pady=(0, 2))

        # Two empty rows by default; users add more with the + button.
        self.condition_rows = []
        self.add_condition_row()
        self.add_condition_row()

        ttk.Button(key_card, text="+ Add row", command=self.add_condition_row
                   ).pack(anchor="w", pady=(8, 0))

        # --- Read-only display of the metadata extracted from an image file ---
        metadata_card = self.card("Extracted Image Metadata", "Read from the image file and saved with the ReadMe")
        self.metadata_text = tk.Text(metadata_card, height=12, wrap="word", state="disabled",
                                     font="TkTextFont", padx=8, pady=6, spacing1=2,
                                     # Names in one column, values in the next;
                                     # a long value wraps under its own start.
                                     tabs=("230",))
        self.metadata_text.tag_configure("value", lmargin2=230)
        scrollbar = ttk.Scrollbar(metadata_card, command=self.metadata_text.yview)
        self.metadata_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.metadata_text.pack(side="left", fill="both", expand=True)

        self.version_label = ttk.Label(self.scrollable_frame, style="Page.TLabel",
                                       text=f"{APP_NAME} v{APP_VERSION}  —  {APP_DATE}")

    def mark_saved(self):
        """Record the form as it is now as having nothing to lose."""
        self.saved_content = self.readme_text()

    def may_discard_changes(self):
        """Return True if the form may be emptied or closed: either nothing
        has changed since it was last saved, loaded or cleared, or the user
        agrees to lose the changes."""
        return self.readme_text() == self.saved_content or messagebox.askyesno(
            "Discard changes?", "The form has changes that have not been saved. Discard them?")

    def close_window(self):
        if self.may_discard_changes():
            self.root.destroy()

    def scroll_form(self, event):
        """Scroll the form in response to a mouse wheel event."""
        widget = event.widget
        # Text boxes and open dropdown lists scroll their own content. Tk
        # reports a dropdown list as a path string, not a widget object.
        if isinstance(widget, str) or widget.winfo_class() == "Text":
            return None
        if widget.winfo_toplevel() is not self.root:
            return None
        if self.scrollable_frame.winfo_height() <= self.main_canvas.winfo_height():
            return "break"  # the whole form is visible
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
            self.mark_saved()
            self.status_label.configure(text=f"Saved {os.path.basename(save_path)}.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not write file: {e}")

    def load_existing(self):
        path = filedialog.askopenfilename(title="Select a ReadMe.txt or a JSON export",
                                          filetypes=[("ReadMe or JSON export", "*.txt *.json")])
        if path and self.may_discard_changes():
            self.parse_readme_file(path)

    def clear_form(self):
        """Empty the form, then put back the template's values if a template
        was loaded at startup. Asks first if there are unsaved changes."""
        if not self.may_discard_changes():
            return
        for label, _, _ in self.fields:
            self.set_field(label, "")
        self.mark_filled_from_image([])
        self.fill_form(self.template_fields, self.template_filename_key, {})
        self.mark_saved()
        self.status_label.configure(
            text="Form cleared and template values put back." if self.template_fields else "Form cleared.")

    def add_condition_row(self, keyword="", group=""):
        """Append a (filename keyword -> group/treatment) row to the Filename Key table."""
        r = len(self.condition_rows) + 1  # row 0 holds the column headings
        left = HintEntry(self.condition_rows_frame, "e.g. ctrl")
        right = HintEntry(self.condition_rows_frame, "e.g. Vehicle control")
        left.insert(0, keyword)
        right.insert(0, group)
        left.grid(row=r, column=0, sticky="ew", padx=2, pady=1)
        right.grid(row=r, column=1, sticky="ew", padx=2, pady=1)
        ToolTip(left, "Text that appears only in this group's file names, so it uniquely identifies the group, e.g. 'B' or 'ctrl'")
        ToolTip(right, "What that group is, e.g. '10 uM Drug Y' or 'Vehicle control'")
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
        """Return (fields, filename_key, metadata) from a ReadMe.txt, template
        or JSON export, or None after showing a message if it cannot be read."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return (parse_json if path.lower().endswith(".json") else parse_readme)(f.read())
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
            self.mark_saved()
            self.status_label.configure(text=f"Loaded {os.path.basename(path)}.")

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
        self.mark_saved()
        self.status_label.configure(
            text=f"Fields pre-filled from this computer's template, {os.path.basename(path)}.")

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

        help_text = tk.Text(help_window, wrap="word", font=("Segoe UI", 10), width=80, height=35,
                            **self.text_colours())
        help_text.pack(expand=True, fill="both", padx=10, pady=10)

        help_text.insert("1.0", "📄 ReMInD - Recommended Metadata Interface for Documentation Help\n\n", "title")
        help_text.insert("end", "This tool was originally created by Nicholas Condon (IMB Microscopy, The University of Queensland) in 2025, and is now developed and maintained independently by Liam Howell (Sydney Microscopy and Microanalysis, The University of Sydney).\n\n")
        help_text.insert("end", "The purpose of this tool is to help capture additional metadata to store with your RAW experimental data.\n\n")
        
        help_text.insert("end", "✒️ Entering Information \n", "subtitle")
        help_text.insert("end", "\t• Not every field needs to be filled in.\n")
        help_text.insert("end", "\t• Enter where your raw data is stored (e.g. a data repository or project name) in the 'Storage Location' field.\n")
        help_text.insert("end", "\t• Empty fields show an example in grey. Hover your cursor over a field for more description.\n")
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
        help_text.insert("end", "\t• The fields that were filled from the file are highlighted until you edit them. Review them before generating your ReadMe file.\n")
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

        A file can hold several images taken with different settings. Fields
        on which they differ list each distinct value (see merge_form_fields
        and combine_image_metadata).

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

        format_name, read_metadata = IMAGE_READERS[ext]
        try:
            per_image = read_metadata(path)
            form_values = merge_form_fields([metadata_to_form_fields(image) for image in per_image])
            metadata = combine_image_metadata(per_image)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read the {format_name} file:\n{e}")
            return

        if self.template_fields.get("Microscope name"):
            form_values.pop("Microscope name", None)
        for label, value in form_values.items():
            self.set_field(label, value)
        self.set_field("Image format", ext)
        self.show_metadata_in_window(metadata)
        self.mark_filled_from_image([*form_values, "Image format"])
        self.status_label.configure(
            text=f"Filled {len(form_values) + 1} fields from {os.path.basename(path)}"
                 f"{f' ({len(per_image)} images)' if len(per_image) > 1 else ''}. "
                 "Check the highlighted fields.")

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
            self.metadata_text.insert(tk.END, f"{k}\t", "key")
            self.metadata_text.insert(tk.END, f"{v}\n", "value")
        if not metadata_dict:
            self.metadata_text.insert(
                tk.END,
                "No image file loaded.\n\n"
                "Use 'Load Fields from Image File' to fill in fields from a CZI, LIF, ND2, OIR "
                "or OME-TIFF file. The metadata read from the file is listed here and saved "
                "with the ReadMe.txt.",
                "hint")
        self.metadata_text.config(state="disabled")

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.colours = apply_theme(self.root, "dark" if self.dark_mode else "light")
        self.dark_mode_btn.configure(text="Light" if self.dark_mode else "Dark")

        # The widgets that are not ttk widgets are coloured here.
        self.root.configure(bg=self.colours["page"])
        self.main_canvas.configure(bg=self.colours["page"])
        for text_widget in (*self.text_fields.values(), self.metadata_text):
            text_widget.configure(**self.text_colours())
        self.metadata_text.tag_configure("key", foreground=self.colours["muted"])
        self.metadata_text.tag_configure("hint", foreground=self.colours["muted"])
        for dropdown in self.dropdowns:
            # A list that has already been opened keeps its old colours
            # unless it is recoloured directly.
            self.root.tk.eval(
                f"[ttk::combobox::PopdownWindow {dropdown}].f.l configure"
                f" -background {self.colours['field']} -foreground {self.colours['text']}")
        self.mark_filled_from_image(self.filled_from_image)
        self._apply_theme_to_titlebar()

    def mark_filled_from_image(self, labels):
        """Show the labels of the fields that were filled from an image file
        in the accent colour, so the user knows which values to check."""
        self.filled_from_image = set(labels)
        for label, widget in self.field_labels.items():
            widget.configure(foreground=self.colours["accent"] if label in self.filled_from_image else "")

    def unmark_field(self, label):
        """Stop showing a field as filled from an image file."""
        if label in self.filled_from_image:
            self.mark_filled_from_image(self.filled_from_image - {label})

    def text_colours(self):
        """Return the options that make a tk.Text look like the fields of
        the current theme."""
        return {"bg": self.colours["field"], "fg": self.colours["text"],
                "insertbackground": self.colours["text"], "selectbackground": self.colours["accent"],
                "selectforeground": self.colours["on accent"], "highlightbackground": self.colours["border"],
                "highlightcolor": self.colours["accent"], "relief": "flat", "highlightthickness": 1}

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

    def export_as_json(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 initialfile=self.default_filename("metadata.json"),
                                                 filetypes=[("JSON files", "*.json")],
                                                 title="Save as JSON")
        if not save_path:
            return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(format_json(self.field_values(), self.get_condition_rows(), self.last_metadata_output))
            self.mark_saved()
            self.status_label.configure(text=f"Saved {os.path.basename(save_path)}.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not write JSON file: {e}")


def check_installation(log_path):
    """
    Check that everything the program needs at run time can be loaded, for
    testing a built executable: import the library of every file format and
    build the window. Problems are written to log_path.

    Returns the process exit code: 0 if all is well, 1 otherwise.
    """
    problems = []
    for extension, (format_name, read) in IMAGE_READERS.items():
        try:
            read(f"missing{extension}")
        except ImportError as e:
            problems.append(f"{format_name}: {e}")
        except Exception:
            pass  # expected: the file does not exist, but the library loaded
    try:
        root = tk.Tk()
        RemindApp(root)
        root.update()
        root.destroy()
    except Exception as e:
        problems.append(f"window: {e!r}")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(problems) or "OK")
    return 1 if problems else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check_installation(sys.argv[sys.argv.index("--check") + 1]))
    root = tk.Tk()
    app = RemindApp(root)
    root.mainloop()
