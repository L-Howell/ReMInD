# ReMInD Developer Guide

## Project Structure
```
remind/
├── src/
│   ├── remind.py                  # Main application
│   ├── readme_io.py               # Reads and writes the ReadMe.txt format
│   ├── theme.py                   # Colours and fonts of the window
│   ├── metadata_extractors/
│   │   ├── CZI_MetadataGUI.py      # Zeiss CZI metadata extraction
│   │   ├── LIF_MetadataGUI.py      # Leica LIF metadata extraction
│   │   ├── Nd2_v2a.py              # Nikon ND2 metadata extraction
│   │   ├── OIR_MetadataGUI.py      # Olympus/Evident OIR metadata extraction
│   │   ├── OMETiff_MetadataGUI.py  # OME-TIFF metadata extraction
│   │   ├── field_mapping.py        # Turns extracted metadata into form field values
│   │   └── _common.py              # Shared helpers (combining images, term lookup)
├── tests/                         # Automated tests
├── tools/                         # Developer utilities (e.g. inspect_oir.py)
├── docs/                          # Documentation
└── templates/                     # Example templates
```

## Development Setup

### Prerequisites
- Python 3.12+
- Git

### Installation
```bash
git clone https://github.com/L-Howell/ReMInD.git
cd ReMInD
pip install -r requirements.txt
```

### Running from Source
```bash
python src/remind.py
```

## Architecture Overview

### Main Components

#### REMBIGUI Class
- **Purpose**: Main application window and logic
- **Key Methods**:
  - `__init__()` - Window setup and initialization
  - `build_toolbar()` / `build_form()` - Create the toolbar and the form
  - `load_image_file()` - Reads an image file and fills the form from it
  - `parse_readme_file()` / `load_template()` - Load a ReadMe.txt or template
  - `generate_readme()` - Creates ReadMe.txt files
  - `export_as_json()` - JSON export functionality

#### Metadata Extractors
- **CZI_MetadataGUI.py** - Handles Zeiss CZI files using `pylibCZIrw` library
- **LIF_MetadataGUI.py** - Handles Leica LIF files using `readlif` library  
- **Nd2_v2a.py** - Handles Nikon ND2 files using `nd2` library
- **OIR_MetadataGUI.py** - Handles Olympus/Evident OIR files using `oirfile` library
- **OMETiff_MetadataGUI.py** - Handles OME-TIFF files using `ome-types` library
- **field_mapping.py** - `metadata_to_form_fields()` turns an extractor's output into form field values
- **_common.py** - Shared helpers: `combine_image_metadata()` for files that hold several images, and `immersion_term()` / `imaging_mode_term()` for translating file values into the form's terms

#### readme_io.py
- **Purpose**: The ReadMe.txt file format, with no GUI code
- `format_readme()` builds the file text; `parse_readme()` reads it back

#### ToolTip Class
- **Purpose**: Provides hover help text for form fields
- **Usage**: `ToolTip(widget, "Help text")`

### Key Features Implementation

#### Window Layout
- `build_toolbar()` - the action buttons and status line, fixed at the top
- `setup_scrollable_window()` - a canvas holding the form, which scrolls
  vertically
- `build_form()` - one card (bordered panel) per section. `SECTION_HEADINGS`
  maps the first field of each section to its heading
- `arrange_cards()` - places the cards in two columns as listed in
  `CARD_PLACES`, or in one column when the form area is narrower than
  `TWO_COLUMN_WIDTH`

`HintEntry` is a text field that shows a grey example while empty; its
`get()` returns `""` while the example is shown, so examples are never saved.

#### Theme
`src/theme.py` holds the colours in one dictionary, `COLOURS`, with a `"dark"`
and a `"light"` set. To change how the program looks, edit the hex values
there. `apply_theme()` styles every ttk widget from them on top of Tk's
built-in "clam" theme, so there is no theme package and no image files.
The text boxes and the canvas are not ttk widgets; `toggle_dark_mode()`
colours them from the same dictionary.

#### Metadata Extraction Pipeline
Each supported file extension has one entry in `IMAGE_READERS` in `remind.py`:
the format name and a function that returns one metadata dict per image in
the file.

```python
IMAGE_READERS = {
    ".czi": ("CZI", lambda path: [extract_metadata(path)]),
    ".lif": ("LIF", extract_lif_metadata),
    ...
}
```

`load_image_file()` looks up the extension and reads the file. It then:
1. turns each image's metadata into form field values with
   `metadata_to_form_fields()`, and merges them with `merge_form_fields()`;
2. combines the per-image metadata with `combine_image_metadata()` and shows
   the result in the metadata panel. The same dict is written to the
   ReadMe.txt and JSON exports.

A LIF project or multi-image OME-TIFF can hold images taken with different
settings. Where the images differ, both functions list every distinct value
rather than picking one, e.g. `63x/1.40 OIL [14 images]; 10x/0.40 DRY [Overview]`.

The extractors share a vocabulary of metadata keys. `metadata_to_form_fields()`
reads these keys:

| Metadata key | Form field |
|---|---|
| `Document Creation Date` | Date and time |
| `System Name` | Microscope name |
| `Objective Model` | Objective |
| `Objective Medium` | Immersion |
| `Acquisition Modes` | Imaging mode, or Specialist modality for STED/TIRF/FLIM/SoRa |
| `Channel Names`, `Dye Names`, `Excitation Wavelengths` | Channel info, as `<excitation> (<target>)` per channel |
| `Size Z` | Z-stack (Yes/No) |
| `Size T` | Time series (Yes/No) |

A field is returned only when the file has a value for it (`"N/A"`, `""` and
`None` count as no value), so loading an image never overwrites what the user
typed with a placeholder.

## Adding New Features

### Adding a New File Format

1. **Create extractor module** that returns a dict using the keys above:
```python
# src/metadata_extractors/NEW_MetadataGUI.py
def extract_new_metadata(file_path):
    """Extract metadata from NEW format files."""
    return {"System Name": ..., "Objective Model": ..., "Size Z": ...}
```
For a format that can hold several images, return a list with one such dict
per image, each with an `"Image Name"`.
```python
```

2. **Add it to `IMAGE_READERS`** in `remind.py`:
```python
from metadata_extractors.NEW_MetadataGUI import extract_new_metadata

IMAGE_READERS = {
    # ... existing formats ...
    ".new": ("NEW", lambda path: [extract_new_metadata(path)]),
}
```

3. **Update file dialog**:
```python
filetypes = [
    ("Image files", "*.czi *.lif *.nd2 *.oir *.tif *.tiff *.new"),  # Add *.new
    ("All files", "*.*"),
]
```

### Adding New Form Fields

1. **Add to the `FORM_FIELDS` list** in `remind.py`:
```python
FORM_FIELDS = [
    # ... existing fields ...
    ("New Field", "", "Help text for new field"),
]
```

2. **Handle in ReadMe generation**:
```python
# Field automatically included in generate_readme()
# No additional code needed for basic text fields
```

3. **Add dropdown options**:
```python
("New Dropdown", ["Option1", "Option2", "Option3"], "Help text"),
```

### Customizing the Interface

#### Adding New Buttons
```python
# In build_form(), add to buttons list:
buttons = [
    # ... existing buttons ...
    ("New Feature", self.new_feature_method),
]

def new_feature_method(self):
    """Implementation of new feature."""
    pass
```

#### Custom Field Types
```python
# In build_form(), add new elif condition:
elif label == "Special Field":
    # Custom widget implementation
    custom_widget = tk.Scale(parent, from_=0, to=100, orient="horizontal")
    custom_widget.grid(row=self.row_counter, column=1, sticky="ew")
    self.entries[label] = custom_widget
```

## Building Executables

The repository ships a ready-to-use script at `build_scripts/build.bat`. Run it
from an **activated** conda environment (e.g. `conda activate remind-py312`).

> **Always build from an activated conda env.** Activation puts the env's
> `Library\bin` on `PATH`, which PyInstaller needs to find the Tcl/Tk (and other)
> DLLs. Building from a non-activated interpreter produces an `.exe` that fails to
> launch with `ImportError: DLL load failed while importing _tkinter`.

### Using PyInstaller manually
```bash
# Install the build requirements (includes PyInstaller)
pip install -r build_scripts/requirements_build.txt

# Build (run from the project root)
pyinstaller --onefile --windowed --name "ReMInD" --noconfirm ^
    --add-data "src/metadata_extractors;metadata_extractors" ^
    --collect-all ome_types ^
    --collect-all xsdata ^
    --collect-all xsdata_pydantic_basemodel ^
    src/remind.py
```

Notes:
- Bundle the whole `metadata_extractors` package with a single `--add-data`
  (folder, not individual files), so `_common.py` and every extractor are included.
- The `--collect-all` flags are **required**: `ome_types`/`xsdata` load some
  submodules (e.g. `xsdata_pydantic_basemodel.hooks`) dynamically, which
  PyInstaller's static analysis misses. Without them the OME-TIFF extractor import
  fails and the app exits on startup. This is **independent of the env** — the
  missing-module error happens even when building inside an activated
  `remind-py312`; activation only addresses the separate Tcl/Tk DLL issue above.
- `^` is the Windows line-continuation character; on macOS/Linux use `\` and swap
  the `--add-data` separator from `;` to `:`.

The single executable is written to the `dist/` directory.

## Testing

### Manual Testing Checklist
- [ ] Application launches without errors
- [ ] All form fields accept input
- [ ] Template loading works: a template next to the executable loads automatically, and Clear Form returns to it
- [ ] Metadata extraction for each format (CZI, LIF, ND2, OIR, OME-TIFF)
- [ ] Filename Key: add/clear rows, round-trip through ReadMe.txt and JSON
- [ ] ReadMe.txt generation
- [ ] JSON export
- [ ] File loading and form population
- [ ] Help dialog displays
- [ ] Resizing: form follows the window width, mouse wheel scrolls over any field
- [ ] Dark and light mode, including the title bar and an opened dropdown list
- [ ] Narrow window: cards stack in one column

### Automated Tests
```bash
python -m unittest discover -s tests
```

- `tests/test_readme_io.py` - the ReadMe.txt format, including a file written by v3.0.0
- `tests/test_field_mapping.py` - which form fields are filled from image metadata, and how several images are combined
- `tests/test_lif.py` - each image in a LIF file reports its own settings
- `tests/test_nd2.py` - laser lines are read from the ND2 acquisition settings text
- `tests/test_form.py` - form behaviour (Clear Form, templates, loading files, examples in empty fields).
  These open the real window and are skipped where no display is available

The tests do not need image files: the extractor libraries are not exercised,
so check each format by hand with a real file when changing an extractor.

## Code Style and Standards

### Python Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Handle exceptions appropriately

### GUI Standards
- Consistent font usage (`self.app_font`)
- Proper tooltip implementation
- Responsive design considerations
- Accessible color schemes

### Error Handling
```python
try:
    # Risky operation
    result = some_operation()
except SpecificException as e:
    messagebox.showerror("Error", f"Specific error occurred: {e}")
except Exception as e:
    messagebox.showerror("Error", f"Unexpected error: {e}")
```

## Contributing

### Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Make changes and test
4. Commit with descriptive messages
5. Push to fork and create pull request

### Pull Request Guidelines
- Include description of changes
- Test on multiple screen resolutions
- Update documentation if needed
- Add examples for new features

### Issue Reporting
When reporting bugs, include:
- ReMInD version
- Operating system
- Steps to reproduce
- Error messages
- Sample files (if applicable)

## API Reference

### Core Functions

#### extract_metadata(file_path)
Extract metadata from CZI files.
- **Parameters**: `file_path` (str) - Path to CZI file
- **Returns**: Metadata dictionary
- **Raises**: Exception if extraction fails

#### extract_lif_metadata(file_path)
Extract metadata from LIF files.
- **Parameters**: `file_path` (str) - Path to LIF file  
- **Returns**: List of metadata dictionaries, one per image, each read from that image's own settings
- **Raises**: Exception if extraction fails

#### extract_nd2_metadata(file_path)
Extract metadata from ND2 files.
- **Parameters**: `file_path` (str) - Path to ND2 file
- **Returns**: Metadata dictionary
- **Raises**: Exception if extraction fails

#### extract_oir_metadata(file_path)
Extract metadata from Olympus/Evident OIR files.
- **Parameters**: `file_path` (str) - Path to OIR file
- **Returns**: Metadata dictionary
- **Raises**: Exception if extraction fails

#### extract_ometiff_metadata(file_path)
Extract metadata from OME-TIFF files (reads embedded OME-XML via `ome-types`).
- **Parameters**: `file_path` (str) - Path to .tif/.tiff file
- **Returns**: List of metadata dictionaries, one per image
- **Raises**: Exception if the file contains no parseable OME-XML

### Utility Functions

#### combine_image_metadata(per_image)
Describe all the images of one file in a single metadata dict. A value shared by every image is kept as it is; otherwise each distinct value is listed with the images it applies to.
- **Parameters**: `per_image` (list[dict]) - one metadata dict per image
- **Returns**: A single metadata dictionary

#### merge_form_fields(per_image)
Combine the form field values of several images. Differing values are joined with "; ", except that the earliest date is used and Yes/No becomes "Both".
- **Parameters**: `per_image` (list[dict]) - `metadata_to_form_fields()` output for each image
- **Returns**: Dictionary mapping form field labels to values

## Release Process

1. **Version Update**: Update `APP_VERSION` in source code
2. **Testing**: Run manual test checklist
3. **Documentation**: Update README and changelog  
4. **Build**: Create executable with PyInstaller
5. **GitHub Release**: Create release with executable attachment
6. **Announcement**: Notify users of new version

## Dependencies

### Core Dependencies
- **tkinter** - GUI framework (included with Python)
- **datetime** - Date/time handling
- **os, glob** - File system operations
- **json** - JSON export functionality

### Metadata Dependencies
- **pylibCZIrw** - Zeiss CZI file reading
- **readlif** - Leica LIF file reading
- **nd2** - Nikon ND2 file reading
- **oirfile** - Olympus/Evident OIR file reading

### Development Dependencies
- **pyinstaller** - Executable building
- **unittest** - Testing framework
