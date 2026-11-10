# ReMInD Developer Guide

## Project Structure
```
remind/
├── src/
│   ├── remind.py                  # Main application
│   ├── readme_io.py               # Reads and writes the ReadMe.txt format
│   ├── theme.py                   # Colours and fonts of the window
│   ├── help_text.py               # Text of the Help window
│   ├── version.py                 # The version number (the only place it is written)
│   ├── metadata_extractors/
│   │   ├── czi_metadata.py         # Zeiss CZI metadata extraction
│   │   ├── lif_metadata.py         # Leica LIF metadata extraction
│   │   ├── nd2_metadata.py         # Nikon ND2 metadata extraction
│   │   ├── oir_metadata.py         # Olympus/Evident OIR metadata extraction
│   │   ├── ome_tiff_metadata.py    # OME-TIFF metadata extraction
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

#### RemindApp Class
- **Purpose**: Main application window and logic
- **Key Methods**:
  - `__init__()` - Window setup and initialization
  - `build_toolbar()` / `build_form()` - Create the toolbar and the form
  - `load_image_file()` - Reads an image file and fills the form from it
  - `parse_readme_file()` / `load_template()` - Load a ReadMe.txt or template
  - `generate_readme()` - Creates ReadMe.txt files
  - `export_as_json()` - JSON export functionality

#### Metadata Extractors
- **czi_metadata.py** - Handles Zeiss CZI files using `pylibCZIrw` library
- **lif_metadata.py** - Handles Leica LIF files using `readlif` library  
- **nd2_metadata.py** - Handles Nikon ND2 files using `nd2` library
- **oir_metadata.py** - Handles Olympus/Evident OIR files using `oirfile` library
- **ome_tiff_metadata.py** - Handles OME-TIFF files using `ome-types` library
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
def _read_czi(path):
    from metadata_extractors.czi_metadata import extract_czi_metadata
    return [extract_czi_metadata(path)]

IMAGE_READERS = {
    ".czi": ("CZI", _read_czi),
    ".lif": ("LIF", _read_lif),
    ...
}
```

Each reader imports its library inside the function. The program therefore
starts without loading any of them, and a library that fails to load only
stops its own format from being read (the user sees the error in a message
box). PyInstaller still finds imports written this way.

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
# src/metadata_extractors/new_metadata.py
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
def _read_new(path):
    from metadata_extractors.new_metadata import extract_new_metadata
    return [extract_new_metadata(path)]

IMAGE_READERS = {
    # ... existing formats ...
    ".new": ("NEW", _read_new),
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

The field is saved, loaded and exported with no further code.

2. **For a dropdown, give the options**:
```python
("New Dropdown", ["Option1", "Option2", "Option3"], "Help text"),
```

## Building Executables

Run `build_scripts/build.bat` from the `build_scripts` folder; the executable
is written to `dist/`. The PyInstaller options are only written there, with
comments giving the reason for each. CI runs the same script.

> **With conda, build from an activated env** (e.g. `conda activate remind-py312`).
> Activation puts the env's `Library\bin` on `PATH`, which PyInstaller needs to
> find the Tcl/Tk (and other) DLLs. Building from a non-activated interpreter
> produces an `.exe` that fails to launch with
> `ImportError: DLL load failed while importing _tkinter`.

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

- `tests/test_readme_io.py` - the ReadMe.txt and JSON formats read back what was written
- `tests/test_field_mapping.py` - which form fields are filled from image metadata, and how several images are combined
- `tests/test_lif.py` - each image in a LIF file reports its own settings
- `tests/test_nd2.py` - laser lines are read from the ND2 acquisition settings text
- `tests/test_form.py` - form behaviour (Clear Form, unsaved changes, templates, loading files, examples in empty fields).
  These open the real window and are skipped where no display is available

The tests do not need image files: the extractor libraries are not exercised,
so check each format by hand with a real file when changing an extractor.

## Contributing

### Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Make changes and test
4. Commit with descriptive messages
5. Push to fork and create pull request

### Pull Request Guidelines
- Include description of changes
- Check the CI run passes
- Update documentation if needed
- Add examples for new features

### Issue Reporting
When reporting bugs, include:
- ReMInD version
- Operating system
- Steps to reproduce
- Error messages
- Sample files (if applicable)

## Release Process

1. **Version Update**: Change `VERSION` and `RELEASE_DATE` in `src/version.py`,
   following [EffVer](https://jacobtomlinson.dev/effver/) (macro.meso.micro, by the
   effort a user needs to move to the new version).
   It is the only place the version is written; the window title, the ReadMe
   header and the Help text read it from there
2. **Checks**: Push and wait for the CI run to pass (tests, build, and the
   check that the built executable starts)
3. **Manual testing**: Run the manual test checklist on the executable from
   the CI run's artifacts
4. **GitHub Release**: Create a release and attach that executable
5. **Announcement**: Notify users of new version

### Continuous integration
`.github/workflows/ci.yml` runs on every push, on Windows. It installs the
pinned requirements, runs the tests, runs `build_scripts/build.bat`, and then
runs `ReMInD.exe --check check.log`. `--check` imports the library of every
file format and builds the window, then exits with code 1 if anything failed
and writes the reasons to the log file. A windowed program has no console, so
without this a library missing from the build would only show up as a window
that never opens.

### Pinned versions
`requirements.txt` gives exact versions so that rebuilding later produces
the same program. To update a library, change its version there and let CI
confirm that the tests pass and the build still starts.
