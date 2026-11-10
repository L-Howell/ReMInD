# ReMInD user guide

ReMInD records the metadata for an imaging experiment in a `ReadMe.txt` that you keep
beside the raw data. This guide covers each part of the window. For problems, see
[Troubleshooting](troubleshooting.md).

## Quick start

1. Click **Load Fields from Image File** and choose one of your image files.
2. Check the highlighted fields, then fill in the rest. No field is compulsory.
3. Click **Generate ReadMe.txt** and save it in the same folder as your image data.

## Loading an image file

| Format | Microscopes |
|---|---|
| `.czi` | Zeiss |
| `.lif` | Leica |
| `.nd2` | Nikon |
| `.oir` | Evident / Olympus |
| `.ome.tif` | Any that writes OME-TIFF. A plain TIFF holds no metadata to read |

ReMInD reads only the metadata, so large files load quickly. It can fill in:

- Date and time
- Microscope name
- Objective and Immersion
- Imaging mode, or Specialist modality for STED, TIRF, FLIM and SoRa
- Channel info
- Z-stack and Time series
- Image format

Only fields the file has a value for are changed. Anything else you have typed is
kept. The labels of the fields that were filled are highlighted until you edit them.
How much a file supplies depends on the microscope and its software, so check every
highlighted field.

Everything read from the file is listed under **Extracted Image Metadata** at the
bottom of the form and is saved with the ReadMe.

### Things to check

- **Channel info** is written as excitation wavelength and target for each channel,
  in file order, e.g. `405 (DAPI), 561 (Alexa Fluor 568)`. The target is the dye set
  in the acquisition software, or the channel name where no dye was set. Replace it
  with your own label where needed. A part the file does not record is left out, so
  a channel can appear as just `405` or just `DAPI`.
- **Immersion**: a file says only that an objective uses oil, so it is filled in as
  `Oil`. Choose `Oil-23` or `Oil-37` if you know which was used. `Multi-immersion`
  means the objective takes several media; replace it with the one you used.
- **Microscope name** is the model name stored in the file. If a
  [template](#templates) sets the microscope name, loading an image file does not
  change it.

### Files that hold several images

A Leica project or a multi-series OME-TIFF can hold images taken with different
settings. ReMInD reads every image.

- Where the images agree, the value is shown once.
- Where they differ, every distinct value is listed, most common first, e.g.
  `63x/1.40 OIL; 10x/0.40 DRY`. The Extracted Image Metadata also says which images
  each value belongs to.
- **Date and time** is that of the earliest image.
- **Z-stack** and **Time series** are set to `Both` when only some of the images have
  them.

## Filling in the form

- An empty field shows an example in grey. The example is never saved.
- Hover over a field for a description.
- The dropdown lists accept typed text. If no option fits, type your own.
- **Now** enters the current date and time. **Insert timestamp** adds it to the Notes.
- **Storage Location** is where the raw data will be kept, typically your project
  folder on your institution's research data store.

### Filename Key

The Filename Key records what the labels in your file names mean.

- **Filename keyword** (left): text that appears in the file names of one group, e.g.
  `ctrl` or `B`. It must appear only in that group's file names.
- **Group / treatment** (right): what that group is, e.g. `Vehicle control` or
  `10 uM Drug Y`.

Click **+ Add row** for more rows. A row with no keyword is not saved.

## Saving and reopening

**Generate ReadMe.txt** saves the form as a text file. The suggested name is the
experiment name followed by `_ReadME.txt`. Fields you left empty are written with no
value, so the file shows what was not recorded.

**Export as JSON** saves the same content as structured data, which scripts and other
software can read directly.

**Load ReadMe.txt** opens either kind of file and replaces everything in the form with
its content. Use it to update a record, or to start a similar experiment from an
earlier one. You can also edit a `ReadMe.txt` in any text editor.

**Clear Form** empties the form and puts back the values of the template, if there is
one.

Clear Form, Load ReadMe.txt and closing the window ask first if the form has changes
that have not been saved.

ReadMe files written by version 3.0.0 or earlier may not load completely: the Filename
Key was written differently and one field has been renamed.

## Templates

A template pre-fills values that are the same for every experiment on a computer. It
is a text file with a name ending in `_ReadME_template.txt`, stored in the same folder
as `ReMInD.exe`.

- The template is loaded when ReMInD starts. If the folder holds several, the first in
  alphabetical order is used.
- **Clear Form** returns to the template's values, so the next user starts from them.
- If the template sets **Microscope name**, loading an image file does not change it.
  The model name stored in the file still appears in the Extracted Image Metadata.

### Setting up a shared instrument

One template per instrument gives every ReadMe from it the same instrument name and
storage location.

1. Copy [`templates/example_ReadME_template.txt`](../templates/example_ReadME_template.txt)
   into the folder that holds `ReMInD.exe` and rename it, e.g.
   `Confocal5_ReadME_template.txt`.
2. Edit **Storage Location** (the root folder users save under) and **Microscope name**
   (the facility's own name for the instrument).
3. Leave out anything that differs between users.

Any field can be set in a template: add a line with the field's label as it appears in
the form, a colon and a space, and the value. A ReadMe.txt renamed to end in
`_ReadME_template.txt` also works as a template. Its Extracted Image Metadata is
ignored, because it belongs to the experiment the file came from.

## File formats

### ReadMe.txt

[`templates/example_ReadME.txt`](../templates/example_ReadME.txt) is a complete example.
The file has up to three parts:

```text
# Generated by ReMInD v4.0.0 — ...

Experiment name: Brain section tiling, cohort 3
Date and time: 2024-09-04 08:50:44
...
Notes:
---
Tiled overview of the hippocampus to count labelled neurons.
---

# Filename Key
ctrl -> Vehicle control
B -> 10 uM Drug Y

# Extracted Image Metadata
System Name: FV4000
Objective Model: UPLXAPO60X 60x NA 1.42
...
```

The Filename Key and Extracted Image Metadata parts are left out when they are empty.

### JSON

```json
{
  "Experiment name": "Brain section tiling, cohort 3",
  "Date and time": "2024-09-04 08:50:44",
  "Notes": "Tiled overview of the hippocampus to count labelled neurons.",
  "Filename Key": [
    {"keyword": "ctrl", "group": "Vehicle control"},
    {"keyword": "B", "group": "10 uM Drug Y"}
  ],
  "Extracted Image Metadata": {
    "System Name": "FV4000",
    "Channel Names": ["CH1", "CH2"]
  }
}
```

Every form field is a member of the object, including the empty ones. `Filename Key`
and `Extracted Image Metadata` are left out when they are empty.
