"""The text of the Help window. A line starting with "## " is shown as the
title and one starting with "# " as a section heading."""

HELP_TEXT = """\
## 📄 ReMInD - Recommended Metadata Interface for Documentation Help

This tool was originally created by Nicholas Condon (IMB Microscopy, The University of Queensland) in 2025, and is now developed and maintained independently by Liam Howell (Sydney Microscopy and Microanalysis, The University of Sydney).

The purpose of this tool is to help capture additional metadata to store with your RAW experimental data.

# ✒️ Entering Information
	• Not every field needs to be filled in.
	• Enter where your raw data is stored (e.g. a data repository or project name) in the 'Storage Location' field.
	• Empty fields show an example in grey. Hover your cursor over a field for more description.
	• Some fields contain drop down lists you can choose items from. If none of the items fit, type your own value into the box.
	• The notes box can be filled in with as much detail as possible. You can use the 'Insert timestamp' button to generate a new line with the date and time.

# 🔑 Filename Key
	• Use the 'Filename Key' table to record what the labels in your file names mean.
	• In the left box, enter a keyword that appears in the file names for a group (e.g. 'B' or 'ctrl').
	• The keyword must be unique to that group — it should appear only in that group's file names, not in any other group's.
	• In the right box, enter the matching biological group or treatment (e.g. '10 uM Drug Y' or 'Vehicle control').
	• Click '+ Add row' for as many groups as you need. The key is saved in the ReadMe.txt and JSON exports.

# 🔬 Load Fields from Image File
	• Click 'Load Fields from Image File' to automatically extract metadata from your image files.
	• Supported formats: CZI (Zeiss), LIF (Leica), ND2 (Nikon), OIR (Olympus/Evident), and OME-TIFF files.
	• The tool will automatically populate relevant fields with metadata from the image file including:
		- Date and time of acquisition
		- Microscope name and settings
		- Objective lens information
		- Channel information
		- Imaging parameters (Z-stack, time series)
		- Software and system information
	• Extracted metadata will be displayed in the 'Extracted Image Metadata' section.
	• The fields that were filled from the file are highlighted until you edit them. Review them before generating your ReadMe file.
	• The raw metadata is also included when exporting as JSON or generating ReadMe files.

# 💾 Generate ReadMe.txt
	• Once you have filled in the form to your liking you can save a ReadMe.txt file to any location (ideally within the data folder it's associated with).
	• Save the ReadMe.txt file alongside the captured data.
	• Use a filename that includes 'ReadMe' and the experiment name if needed.
	• If you imported metadata from an image file, the raw metadata will be appended to the ReadMe file.

# 📂 Load ReadMe.txt
	• The program can read a previously generated ReadMe file, or a JSON export, and repopulate the fields for quick editing/updating.
	• This can be particularly useful when adding to the notes section.

# 📖 Templates
	• The program automatically looks for any template files stored in the same location as the executable.
	• Any template file must be saved as *_ReadMe_template.txt with something in place of the *.
	• The template is loaded automatically, and 'Clear Form' returns to its values.
	• If the template sets the microscope name, loading an image file does not change it.
	• Keep one template per computer. If there are several, the first in alphabetical order is used.

# 📁 Export as JSON
	• Export all form data and extracted metadata as a structured JSON file.
	• Useful for data processing, analysis workflows, or integration with other tools.
	• Includes both form entries and raw extracted image metadata.

# 📌 Tips:
	• Use a previously generated ReadMe.txt file as a template to pre-load certain fields such as Storage Location, Name, Sample information etc.
	• If you're iterating on an experiment, consider labeling your files like ReadMe_exp1_v1.txt, v2, etc.
	• Be descriptive: When entering experiment details, use full names, reagent IDs, microscope configurations, etc.
	• Always load metadata from your original image files first, then supplement with additional information.
	• Review imported metadata for accuracy - some fields may need manual correction or additional detail.
	• Use the metadata extraction feature to ensure consistency across multiple experiments.

# 🙏 Acknowledgements
This tool uses several open-source libraries for metadata extraction:

	• pylibCZIrw by ZEISS - For reading Zeiss CZI files
		  https://github.com/ZEISS/pylibczirw

	• readlif by Nimesh Khadka - For reading Leica LIF files
		  https://github.com/nimne/readlif

	• nd2 by Talley Lambert - For reading Nikon ND2 files
		  https://github.com/tlambert03/nd2

	• oirfile by Christoph Gohlke - For reading Olympus/Evident OIR files
		  https://github.com/cgohlke/oirfile

	• ome-types by Talley Lambert - For reading OME-TIFF files
		  https://github.com/tlambert03/ome-types

	• Python standard libraries: tkinter, json, datetime, os, glob

Special thanks to the open-source community for making microscopy metadata
accessible and standardized across different imaging platforms.

For support or feature requests, please open an issue at https://github.com/L-Howell/ReMInD.
"""
