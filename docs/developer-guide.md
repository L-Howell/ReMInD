# ReMInD Developer Guide

## Project Structure
```
remind/
├── src/
│   ├── remind.py                  # Main application
│   ├── readme_io.py               # Reads and writes the ReadMe.txt format
│   ├── metadata_extractors/
│   │   ├── CZI_MetadataGUI.py      # Zeiss CZI metadata extraction
│   │   ├── LIF_MetadataGUI.py      # Leica LIF metadata extraction
│   │   ├── Nd2_v2a.py              # Nikon ND2 metadata extraction
│   │   ├── OIR_MetadataGUI.py      # Olympus/Evident OIR metadata extraction
│   │   ├── OMETiff_MetadataGUI.py  # OME-TIFF metadata extraction
│   │   ├── field_mapping.py        # Turns extracted metadata into form field values
│   │   └── _common.py              # Shared helpers (most_common_metadata, term lookup)
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
  - `build_form()` - Creates the GUI form
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
- **_common.py** - Shared helpers: `most_common_metadata()` for collapsing multi-image container formats, and `immersion_term()` / `imaging_mode_term()` for translating file values into the form's terms

#### readme_io.py
- **Purpose**: The ReadMe.txt file format, with no GUI code
- `format_readme()` builds the file text; `parse_readme()` reads it back

#### ToolTip Class
- **Purpose**: Provides hover help text for form fields
- **Usage**: `ToolTip(widget, "Help text")`

### Key Features Implementation

#### Responsive Design
```python
# Screen size detection and window sizing
screen_width = self.root.winfo_screenwidth()
if screen_width >= 1920:
    window_width = 900
elif screen_width >= 1366:
    window_width = 750
else:
    window_width = 650
```

#### Metadata Extraction Pipeline
Each supported file extension has one entry in `IMAGE_READERS` in `remind.py`:
the format name, a function that returns the metadata dict for a file, and a
function that turns that dict into form field values.

```python
IMAGE_READERS = {
    ".czi": ("CZI", lambda path: extract_metadata(path)[0], metadata_to_form_fields),
    ".lif": ("LIF", _read_lif, metadata_to_form_fields),
    ".nd2": ("ND2", extract_nd2_metadata, map_nd2_to_remind_fields),
    ...
}
```

`load_image_file()` looks up the extension, calls the two functions, writes
the returned values into the form, and shows the metadata dict in the
metadata panel. The same dict is written to the ReadMe.txt and JSON exports.

The extractors share a vocabulary of metadata keys. `metadata_to_form_fields()`
reads these keys:

| Metadata key | Form field |
|---|---|
| `Document Creation Date` | Date and time |
| `System Name` | Microscope name |
| `Objective Model` | Objective |
| `Objective Medium` | Immersion |
| `Acquisition Modes` | Imaging mode |
| `Channel Names` | Channel info |
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

2. **Add it to `IMAGE_READERS`** in `remind.py`:
```python
from metadata_extractors.NEW_MetadataGUI import extract_new_metadata

IMAGE_READERS = {
    # ... existing formats ...
    ".new": ("NEW", extract_new_metadata, metadata_to_form_fields),
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
- [ ] Template loading works: one template loads automatically, several show the dialog, Clear Form returns to the template
- [ ] Metadata extraction for each format (CZI, LIF, ND2, OIR, OME-TIFF)
- [ ] Filename Key: add/clear rows, round-trip through ReadMe.txt and JSON
- [ ] ReadMe.txt generation
- [ ] JSON export
- [ ] File loading and form population
- [ ] Font size adjustment
- [ ] Help dialog displays
- [ ] Responsive design on different screen sizes

### Automated Tests
```bash
python -m unittest discover -s tests
```

- `tests/test_readme_io.py` - the ReadMe.txt format, including a file written by v3.0.0
- `tests/test_field_mapping.py` - which form fields are filled from image metadata
- `tests/test_form.py` - form behaviour (Clear Form, templates, loading files).
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
- **Returns**: `(metadata_dict, raw_metadata)` tuple
- **Raises**: Exception if extraction fails

#### extract_lif_metadata(file_path)
Extract metadata from LIF files.
- **Parameters**: `file_path` (str) - Path to LIF file  
- **Returns**: List of metadata dictionaries (one per series)
- **Raises**: Exception if extraction fails

#### extract_nd2_metadata(file_path)
Extract metadata from ND2 files.
- **Parameters**: `file_path` (str) - Path to ND2 file
- **Returns**: Metadata dictionary
- **Raises**: Exception if extraction fails

#### extract_oir_metadata(file_path)
Extract metadata from Olympus/Evident OIR files.
- **Parameters**: `file_path` (str) - Path to OIR file
- **Returns**: `(metadata_dict, raw_attrs)` tuple
- **Raises**: Exception if extraction fails

#### extract_ometiff_metadata(file_path)
Extract metadata from OME-TIFF files (reads embedded OME-XML via `ome-types`).
- **Parameters**: `file_path` (str) - Path to .tif/.tiff file
- **Returns**: `(metadata_dict, ome_object)` tuple; for multi-image files the dict is the per-field most common value across images
- **Raises**: Exception if the file contains no parseable OME-XML

### Utility Functions

#### map_nd2_to_remind_fields(metadata_dict)
Map ND2 metadata to ReMInD form fields.
- **Parameters**: `metadata_dict` (dict) - Raw ND2 metadata
- **Returns**: Dictionary mapping ReMInD field names to values

#### most_common_metadata(dicts)
Collapse a list of per-image metadata dicts into one, taking the most common value per key (ties favour the earliest/first image). Used for container formats (LIF, multi-image OME-TIFF).
- **Parameters**: `dicts` (list[dict]) - one metadata dict per image/series
- **Returns**: A single representative metadata dictionary

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
