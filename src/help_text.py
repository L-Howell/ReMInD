"""
The text of the Help window, one paragraph per line.

The start of a line says how it is shown: "# " is a section heading, "- " a
bullet, "1. " (any number) a numbered step, and "  " a plain paragraph
indented under its heading. The first line is the title. {version} and
{date} are filled in from version.py.
"""

HELP_TEXT = """\
ReMInD Help
  Version {version}, {date}

  ReMInD records metadata associated with an imaging experiment, in a ReadMe.txt that you keep beside the raw data.

# Getting started
1. Click Load Fields from Image File and choose one of your image files. ReMInD fills in whatever metadata is already available in the file.
2. Check the highlighted fields, then fill in the rest. No field is compulsory.
3. Click Generate ReadMe.txt and save it in the same folder as your image data.
  To change a record later, open it with Load ReadMe.txt, edit it and generate it again (or just edit the .txt file directly).

# Loading an image file
- Reads CZI (Zeiss), LIF (Leica), ND2 (Nikon), OIR (Evident/Olympus) and OME-TIFF files.
- Only fields the file has a value for are changed. Their labels stay highlighted until you edit them.
- How much a file supplies depends on the microscope and its software, so check every highlighted field.
- A file that holds several images, such as a Leica project, is read in full. Where its images differ, every value is listed.
- Immersion: an oil objective is filled in as "Oil". Choose Oil-23 or Oil-37 if you know which was used. "Multi-immersion" means the objective takes several media; replace it with the one you used.
- Everything read from the file is listed under Extracted Image Metadata and saved with the ReadMe.

# Filling in the form
- Channel info: give each channel as excitation wavelength and target, in order of acquisition, e.g. 405 (DAPI), 488 (GFP-tubulin), 561 (mCherry).
- The dropdown lists accept typed text. If no option fits, type your own.
- Storage Location: where the raw data will be kept. Typically, this would be your RDS project folder.
- Hover over any field for a description.

# Filename Key
- Records what the labels in your file names mean. Enter a keyword from the file names on the left and the group or treatment it identifies on the right, e.g. "ctrl" and "Vehicle control".
- Each keyword must appear only in the file names of its own group.

# Saving and reopening
- Export as JSON saves the same content as the ReadMe, for easier reading in other software.
- Load ReadMe.txt opens either kind of file.

# About
  ReMInD was created by Nicholas Condon (IMB Microscopy, The University of Queensland) and is developed and maintained independently by Liam Howell (Sydney Microscopy and Microanalysis, The University of Sydney).

  Image files are read with czifile, liffile and oirfile (Christoph Gohlke), and nd2 and ome-types (Talley Lambert).

  User guide, updates and problem reports: https://github.com/L-Howell/ReMInD
"""
