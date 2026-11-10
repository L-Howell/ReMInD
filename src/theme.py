"""
The colours and fonts of the ReMInD window.

To change how the program looks, edit COLOURS. Every ttk widget is styled
from it by apply_theme, on top of the "clam" theme that ships with Tk, so no
theme package or image files are needed.
"""

import tkinter.font as tkfont
import tkinter.ttk as ttk

# What each colour is used for:
#   page       behind the cards
#   band       behind the toolbar
#   card       the panels that hold the sections of the form
#   field      text boxes, dropdowns and ordinary buttons
#   hover      an ordinary button under the pointer
#   border     outlines of cards, fields and buttons
#   text       normal text
#   muted      examples inside empty fields, captions and the status line
#   accent     the main button, the labels of fields filled from an image,
#              the outline of the field being edited, and selected text
#   on accent  text on top of the accent colour
COLOURS = {
    "dark": {
        "page": "#1b1916", "band": "#27231f", "card": "#24211d", "field": "#322e28", "hover": "#3d3831",
        "border": "#4a443d", "text": "#fbf8f3", "muted": "#9a948b", "accent": "#f2b24a", "on accent": "#1b1916",
    },
    "light": {
        "page": "#f1ede6", "band": "#fbfaf7", "card": "#fbfaf7", "field": "#ffffff", "hover": "#ebe6dd",
        "border": "#d3ccc0", "text": "#2a2620", "muted": "#7a746a", "accent": "#a65b00", "on accent": "#ffffff",
    },
}

# For the examples shown inside empty fields. One grey that is readable on
# both the dark and the light field colour, so it need not change with the mode.
HINT_COLOUR = "#8a8a8a"

BODY_FONT = "RemindBody"
HEADING_FONT = "RemindHeading"


def _set_up_fonts(root):
    """Create the two named fonts, and make Tk's standard fonts match them so
    that text boxes and fields use the same family and size as labels."""
    if BODY_FONT in tkfont.names(root):
        return
    families = tkfont.families(root)
    family = next((f for f in ("Segoe UI", "Inter", "DejaVu Sans") if f in families), "TkDefaultFont")
    # Negative sizes are in pixels, so the layout does not depend on the
    # display's DPI setting.
    # Created through Tk directly: a tkfont.Font object deletes its font
    # when Python discards the object.
    root.tk.call("font", "create", BODY_FONT, "-family", family, "-size", -14)
    root.tk.call("font", "create", HEADING_FONT, "-family", family, "-size", -16, "-weight", "bold")
    for name in ("TkTextFont", "TkDefaultFont"):
        tkfont.nametofont(name, root=root).configure(family=family, size=-14)


def apply_theme(root, mode):
    """
    Style every ttk widget of the application.

    Args:
        root: the Tk root window.
        mode: "dark" or "light", a key of COLOURS.

    Returns:
        dict: the colours now in use, for the few widgets that are not ttk
        widgets (text boxes, the scrolling canvas) and must be coloured by
        the caller.

    Besides the standard widget styles, these named styles are defined:
    "Page.TFrame" and "Page.TLabel" for widgets placed directly on the page,
    "Band.TFrame" and "Band.TLabel" for the toolbar, "Card.TFrame" for a
    bordered panel, "Muted.TLabel" and "Heading.TLabel" for text inside a
    card, and "Accent.TButton" for the main button.
    """
    c = COLOURS[mode]
    _set_up_fonts(root)
    style = ttk.Style(root)
    style.theme_use("clam")

    # "clam" draws borders from three colours; setting the light and dark
    # ones to the fill colour leaves a flat outline in the border colour.
    style.configure(".", background=c["card"], foreground=c["text"], fieldbackground=c["field"],
                    bordercolor=c["border"], lightcolor=c["card"], darkcolor=c["card"], troughcolor=c["page"],
                    focuscolor=c["accent"], selectbackground=c["accent"], selectforeground=c["on accent"],
                    insertcolor=c["text"], font=BODY_FONT)

    style.configure("Page.TFrame", background=c["page"])
    style.configure("Page.TLabel", background=c["page"], foreground=c["muted"])
    style.configure("Band.TFrame", background=c["band"])
    style.configure("Band.TLabel", background=c["band"], foreground=c["muted"])
    style.configure("Card.TFrame", background=c["card"], bordercolor=c["border"], relief="solid", borderwidth=1)
    style.configure("Muted.TLabel", foreground=c["muted"])
    style.configure("Heading.TLabel", font=HEADING_FONT)
    style.configure("TSeparator", background=c["border"])

    style.configure("TButton", background=c["field"], bordercolor=c["border"], lightcolor=c["field"],
                    darkcolor=c["field"], padding=(12, 6), width=0)
    style.map("TButton", background=[("pressed", c["border"]), ("active", c["hover"])],
              lightcolor=[("active", c["hover"])], darkcolor=[("active", c["hover"])])
    style.configure("Accent.TButton", background=c["accent"], foreground=c["on accent"], bordercolor=c["accent"],
                    lightcolor=c["accent"], darkcolor=c["accent"])
    # The accent button keeps its colour under the pointer; without this it
    # would take the hover colour of an ordinary button.
    style.map("Accent.TButton", background=[("active", c["accent"])], lightcolor=[("active", c["accent"])],
              darkcolor=[("active", c["accent"])])

    for widget in ("TEntry", "TCombobox"):
        style.configure(widget, fieldbackground=c["field"], background=c["field"], bordercolor=c["border"],
                        lightcolor=c["field"], darkcolor=c["field"], padding=6, arrowcolor=c["muted"],
                        arrowsize=14)
        style.map(widget, bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["accent"])],
                  darkcolor=[("focus", c["accent"])])

    style.configure("TScrollbar", background=c["border"], troughcolor=c["page"], bordercolor=c["page"],
                    lightcolor=c["border"], darkcolor=c["border"], arrowcolor=c["muted"])
    style.map("TScrollbar", background=[("active", c["muted"])])

    # The list that drops down from a dropdown is a classic Tk listbox.
    for option, value in (("background", c["field"]), ("foreground", c["text"]),
                          ("selectBackground", c["accent"]), ("selectForeground", c["on accent"])):
        root.option_add(f"*TCombobox*Listbox.{option}", value)
    return c
