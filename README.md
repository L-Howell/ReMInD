# ReMInD
# 🧬 Recommended Metadata Interface for Documentation

**Version**: see [`src/version.py`](src/version.py) or the [releases](https://github.com/L-Howell/ReMInD/releases)  
**Maintainer**: Liam Howell, Sydney Microscopy and Microanalysis, The University of Sydney  
**Original author**: Dr Nicholas Condon (n.condon@uq.edu.au), Institute for Molecular Bioscience (IMB) Microscopy Facility, The University of Queensland  
**License**: GNU GPL v3.0

---

## 📖 Overview

ReMInD assists researchers in capturing and organizing essential metadata for imaging experiments. It generates structured `ReadME.txt` files and JSON exports that can be stored alongside raw data to support good research data management (RDM) practices and future reuse.

The tool is especially useful for users of light microscopy and other imaging systems, helping to ensure that contextual information is not lost after acquisition. It features automatic metadata extraction from microscopy file formats to streamline the documentation process.

> **Project history:** ReMInD 3.0 is a single, unified application that continues from the
> earlier "ReMInD Lite" line. It originated as [ReMInD by Nicholas Condon](https://github.com/NickCondon/Remind)
> and is now developed and maintained independently by Liam Howell under the GPL v3.0.

---

## 🚀 Features

### Core Functionality
- **GUI-based metadata form** with tooltips for each field  
- **Controlled vocabulary dropdowns** (e.g. microscope type, immersion media)  
- **Timestamp insertion** in Notes field
- **Filename Key table** - map a keyword in your file names to the biological group/treatment it identifies (add as many rows as needed)
- **Template system** for pre-filling common fields
- **Load existing ReadME.txt** files to edit and update metadata
- **Export to multiple formats**: human-readable `ReadME.txt` and structured JSON

### Image Metadata Extraction
- **Automatic metadata extraction** from microscopy files:
  - **CZI files** (Zeiss) - acquisition settings, microscope info, channels
  - **LIF files** (Leica) - system details, imaging parameters
  - **ND2 files** (Nikon) - experimental setup, time series, Z-stacks
  - **OIR files** (Olympus/Evident) - acquisition settings, channels, objectives
  - **OME-TIFF files** - reads embedded OME-XML (objective, channels, pixel sizes)
- **Smart field mapping** - automatically populates relevant form fields
- **Multi-image files** - every image in a LIF project or multi-series OME-TIFF is read; settings that differ between images are all listed
- **Raw metadata display** - view complete extracted metadata
- **Round-trip compatibility** - reload metadata when opening saved ReadME files

### Adaptive Interface
- **Two-column layout** - most of the form fits on one screen; a narrow window stacks it in one column
- **Fixed toolbar** - the action buttons stay visible while the form scrolls
- **Examples in empty fields** and highlighting of the fields filled from an image file
- **Dark/light mode toggle** with Windows title bar theming

---

## 🖥️ Requirements*

- **Python** 3.12+
- **Tkinter** (included with most Python installations)
- **Additional libraries** for metadata extraction:
  - `pylibCZIrw` - for Zeiss CZI files [link](https://github.com/ZEISS/pylibczirw)
  - `readlif` - for Leica LIF files [link](https://github.com/Arcadia-Science/readlif)
  - `nd2` - for Nikon ND2 files [link](https://github.com/tlambert03/nd2)
  - `oirfile` - for Olympus/Evident OIR files [link](https://github.com/cgohlke/oirfile)
  - `ome-types` - for OME-TIFF files [link](https://github.com/tlambert03/ome-types)

*Only needed for editing and testing the Python code

---

## ▶️ Running from Source

```bash
git clone https://github.com/L-Howell/ReMInD.git
cd ReMInD
pip install -r requirements.txt
python src/remind.py
```

---

## ⌨️ Creating the Executable

Run `build_scripts/build.bat` from the `build_scripts` folder. It installs the
build requirements, runs PyInstaller, and writes `dist/ReMInD.exe`. The
PyInstaller options, and the reasons for them, are in the script.

With conda, **activate the environment first** (e.g. `conda activate remind-py312`).
Activation puts the environment's `Library\bin` on `PATH`, which PyInstaller
needs to find the Tcl/Tk (and other) DLLs. Building from a non-activated
interpreter produces an `.exe` that fails to launch with
`ImportError: DLL load failed while importing _tkinter`.

You can also download a ready-built `ReMInD.exe` from the artifacts of any
CI run (see below).

## ✅ Automated checks

Every push runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml) on Windows:
the tests, the build script, and a check that the built `ReMInD.exe` starts
and can load every metadata library. The executable is attached to the run
as an artifact.

## 📦 Packaged Executable
- The `ReMInD.exe` file is fully self contained for Windows 11
- The icon is built into `ReMInD.exe`

