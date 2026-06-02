# ReMInD
# 🧬 Recommended Metadata Interface for Documentation

**Version**: 3.0.0  
**Maintainer**: Liam Howell, Sydney Microscopy and Microanalysis, The University of Sydney  
**Original author**: Dr Nicholas Condon (n.condon@uq.edu.au), Institute for Molecular Bioscience (IMB) Microscopy Facility, The University of Queensland  
**License**: GNU GPL v3.0  
**Date**: June 2026

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
- **Representative metadata for container formats** - multi-image files (e.g. LIF, multi-series OME-TIFF) use the most common value per field rather than the first image
- **Raw metadata display** - view complete extracted metadata
- **Round-trip compatibility** - reload metadata when opening saved ReadME files

### Adaptive Interface
- **Responsive design** - adapts to different screen resolutions (1024x768+)
- **Scrollable interface** for low-resolution displays
- **Scalable fonts** (A+/A- buttons)
- **Two-row button layout** for narrow screens
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
  - `sv-ttk` *(optional)* - dark/light theme for ttk widgets
  - `pywinstyles` *(optional)* - Windows title bar colour theming

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

The repository includes a ready-to-use build script at `build_scripts/build.bat`. To build manually:

1. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```
2.  In a terminal, navigate to the project root.
3.  Run:
   ```bash
   pyinstaller --onefile --windowed --name "ReMInD" --add-data "src/metadata_extractors;metadata_extractors" src/remind.py
   ```
4.  Your single executable will be within the `dist` directory that was created.


## 📦 Packaged Executable
- The `ReMInD.exe` file is fully self contained for Windows 11
- If using the custom icon file (provided) you will need to create a shortcut to `ReMInD.exe` to use the custom icon in Windows 11

