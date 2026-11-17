"""
The colours and fonts of the ReMInD window.

remind.py calls apply_theme when the window opens and when the user switches
between dark and light mode. To change how the program looks, edit COLOURS.
apply_theme styles every ttk widget from it, on top of Tk's built-in "clam"
theme. No theme package or image files are needed.
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
        "page": "#1a1a1a", "band": "#242424", "card": "#222222", "field": "#2e2e2e", "hover": "#3a3a3a",
        "border": "#454545", "text": "#f5f5f5", "muted": "#959595", "accent": "#f2b24a", "on accent": "#1a1a1a",
    },
    "light": {
        "page": "#f0f0f0", "band": "#fafafa", "card": "#fafafa", "field": "#ffffff", "hover": "#e8e8e8",
        "border": "#d0d0d0", "text": "#242424", "muted": "#707070", "accent": "#a65b00", "on accent": "#ffffff",
    },
}

# The colour of the example text in empty fields. This grey is readable on
# both dark and light fields, so it does not change with the mode.
HINT_COLOUR = "#8a8a8a"

BODY_FONT = "RemindBody"
HEADING_FONT = "RemindHeading"


def apply_theme(root, mode):
    """
    Style every ttk widget of the application.

    Besides the standard widget styles, this defines these named styles:
    "Page.TFrame" and "Page.TLabel" for widgets placed directly on the page,
    "Band.TFrame" and "Band.TLabel" for the toolbar, "Card.TFrame" for a
    bordered panel, "Muted.TLabel" and "Heading.TLabel" for text inside a
    card, and "Accent.TButton" for the main button.

    Args:
        root (tkinter.Tk): the root window.
        mode (str): "dark" or "light", a key of COLOURS.

    Returns:
        dict: the colours now in use. The caller colours the widgets that are
        not ttk widgets (text boxes and the scrolling canvas) from these.
    """
    c = COLOURS[mode]
    _set_up_fonts(root)
    style = ttk.Style(root)
    style.theme_use("clam")

    # "clam" draws borders in three colours. Setting the light and dark ones
    # to the fill colour leaves a flat outline in the border colour.
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
    # Without this, the accent button would take an ordinary button's hover
    # colour under the pointer.
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

    # A dropdown's list is a classic Tk listbox, which ttk styles do not reach.
    for option, value in (("background", c["field"]), ("foreground", c["text"]),
                          ("selectBackground", c["accent"]), ("selectForeground", c["on accent"])):
        root.option_add(f"*TCombobox*Listbox.{option}", value)
    return c


def _set_up_fonts(root):
    """Create the body and heading fonts, and make Tk's standard fonts match them."""
    if BODY_FONT in tkfont.names(root):
        return
    families = tkfont.families(root)
    family = next((f for f in ("Segoe UI", "Inter", "DejaVu Sans") if f in families), "TkDefaultFont")
    # Negative sizes are in pixels, so the layout does not depend on the
    # display's DPI setting. The fonts are created through Tk directly,
    # because Tk deletes a tkfont.Font's font when Python discards the object.
    root.tk.call("font", "create", BODY_FONT, "-family", family, "-size", -14)
    root.tk.call("font", "create", HEADING_FONT, "-family", family, "-size", -16, "-weight", "bold")
    for name in ("TkTextFont", "TkDefaultFont"):
        # Text boxes and fields use Tk's standard fonts, so they must match the labels.
        tkfont.nametofont(name, root=root).configure(family=family, size=-14)
