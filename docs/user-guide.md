# ReMInD User Guide

## Overview
ReMInD helps researchers capture essential metadata for imaging experiments, generating structured ReadMe.txt files and JSON exports for research data management.

## Getting Started

### First Launch
ReMInD looks for template files (names ending in `_ReadME_template.txt`) in the same folder as the executable:
- **Template found** - it is loaded automatically and its values pre-fill the form
- **No template** - the form starts blank

Keep one template per computer. If there are several, the first in alphabetical order is used.

### Interface Layout
- **Toolbar** - Load Fields from Image File, Load ReadMe.txt, Generate ReadMe.txt, Export as JSON, Clear Form, Help and the Dark/Light switch. It stays visible while the form scrolls
- **Form fields** - Grouped in panels: Experiment, Sample, Microscope and acquisition, and Notes. The panels sit in two columns, or in one column when the window is narrow
- **Examples** - An empty field shows an example in grey. It disappears when you click in the field and is never saved
- **Filename Key** - Table linking file name keywords to groups
- **Extracted Image Metadata** - Shows the metadata read from an image file

## Core Features

### 1. Manual Data Entry
Fill in relevant fields:
- **Experiment name** - Title of your experiment
- **Date and time** - Use "Now" button for current timestamp
- **Sample information** - Cell lines, animal strains, etc.
- **Microscope settings** - Objective, immersion, imaging mode
- **Notes** - Detailed experimental context

**Tips:**
- Hover over fields for help tooltips
- Not all fields are required
- Use dropdown menus where available
- If none of the dropdown items fit, type your own value into the box

### Filename Key

Use the **Filename Key** table to document what the labels in your file names mean,
instead of burying it in the Notes field:

- **Filename keyword** (left): a piece of text that appears in the file names for a
  group, e.g. `B` or `ctrl`. It **must be unique to that group** — i.e. appear only
  in that group's file names, not in any other group's — so it unambiguously
  identifies the condition.
- **Group / treatment** (right): the biological condition it identifies, e.g.
  `10 µM Drug Y` or `Vehicle control`.

Two rows are shown by default; click **+ Add row** to add more. The key is written to
both the `ReadMe.txt` and the JSON export, and is reloaded when you open a saved ReadMe.

### 2. Automatic Metadata Extraction

#### Supported File Formats
- **CZI files** (Zeiss) - Acquisition settings, channels, objectives
- **LIF files** (Leica) - System details, imaging parameters  
- **ND2 files** (Nikon) - Experimental setup, time series, Z-stacks
- **OIR files** (Olympus/Evident) - Acquisition settings, channels, objectives
- **OME-TIFF files** - Embedded OME-XML (objective, channels, pixel sizes)

> A LIF project or multi-series OME-TIFF can hold several images taken with
> different settings. ReMInD reads every image. Where they agree, the value is
> shown once. Where they differ, every distinct value is listed, most common
> first: form fields show e.g. `63x/1.40 OIL; 10x/0.40 DRY`, and the metadata
> panel also says which images each value belongs to. Z-stack and Time series
> are set to `Both` when only some of the images have them.

#### How to Extract Metadata
1. Click **"Load Fields from Image File"**
2. Select your image file (CZI, LIF, ND2, OIR, or OME-TIFF)
3. Review the automatically populated fields
4. Check the "Extracted Image Metadata" panel
5. Add additional experimental context as needed

#### What Gets Extracted (where possible)
- Date and time of acquisition
- Microscope name and model
- Objective lens specifications
- Channel information, written as excitation wavelength and target for each
  channel in file order, e.g. `405 (DAPI), 561 (Alexa Fluor 568)`. The target
  is the dye set in the acquisition software, or the channel name. Check it
  and replace it with your own label where needed; a part the file does not
  record is left out
- Immersion and imaging mode
- Whether a Z-stack and a time series were acquired
- Software and system information (shown in the metadata panel)

The labels of the fields filled from the file are highlighted so you can check
them; the highlight on a field goes away when you edit it.

Only fields the file has a value for are changed; anything else you have typed
is kept. The file records an oil objective simply as "Oil", so pick `Oil-23`
or `Oil-37` yourself if you know which was used. A Leica multi-immersion
objective is filled in as "Multi-immersion"; replace it with the medium you used.

### 3. File Operations

#### Generate ReadMe.txt
1. Complete your form
2. Click **"Generate ReadMe.txt"**
3. Choose save location (preferably with your data)
4. File includes both form data (including notes) and extracted metadata (if used)

#### Load Existing ReadMe
1. Click **"Load ReadMe.txt"**
2. Select a previously generated ReadMe.txt, or a JSON export
3. Form repopulates for editing/updating
4. The extracted metadata is replaced by the file's, and cleared if the file has none

ReadMe files written by version 3.0.0 or earlier may not load completely: the
Filename Key is written differently and one field has been renamed.

#### Unsaved changes
**Clear Form**, **Load ReadMe.txt** and closing the window ask before
discarding changes that have not been saved as a ReadMe.txt or JSON export.

#### Export as JSON
1. Click **"Export as JSON"**
2. Creates structured data file
3. Includes both form entries and raw metadata
4. Useful for data processing workflows

### 4. Templates

A template pre-fills values that are the same for every experiment. It is a
ReadMe.txt file with a name ending in `_ReadME_template.txt`, stored in the
same folder as the ReMInD executable.

#### Using Templates
- The template is loaded automatically at startup
- **Clear Form** empties the form and then puts the template's values back,
  so the next user starts from the template
- If the template sets **Microscope name**, loading an image file does not
  change it. The model name stored in the image file still appears in the
  extracted metadata

#### Templates for a shared instrument
On an instrument PC used by many people, one template per instrument works
best: it gives every ReadMe the same instrument name and storage location.
1. Copy `templates/example_ReadME_template.txt` into the same folder as the
   ReMInD executable and rename it, e.g. `Confocal5_ReadME_template.txt`
2. Edit **Storage Location** (e.g. the root folder users save under) and
   **Microscope name** (the facility's own name for the instrument)
3. Leave out anything that differs between users

Individual users do not need their own template: **Load ReadMe.txt** on a
previous ReadMe does the same job.

#### Creating a Template from a ReadMe
1. Fill out a form with common information
2. Generate ReadMe.txt
3. Rename file to `*_ReadME_template.txt`
4. Place in same folder as ReMInD executable

Extracted image metadata in a template is ignored, because it belongs to the
experiment the template was made from.

## Best Practices

### Suggested File Organization
```
/Your_Experiment_Folder/
├── raw_data/
│   ├── image001.czi
│   ├── image002.czi
│   └── ...
├── Experiment_ReadMe.txt     ← Generated by ReMInD
├── Experiment_metadata.json  ← Optional JSON export
└── analysis/
    └── ...
```

### Workflow Recommendations

#### New Experiment
1. **Load image metadata first** - Extract from your first acquired image
2. **Review and supplement** - Check imported data for accuracy
3. **Add experimental context** - Sample prep, environmental conditions
4. **Save ReadMe** - Use descriptive filename with experiment name
5. **Store with data** - Keep ReadMe.txt with raw images

#### Ongoing Experiments
1. **Load previous ReadMe** - Use as starting point for similar experiments
2. **Update differences** - Modify only what's changed
3. **Version control** - Use filenames like `ReadMe_exp1_v1.txt`, `ReadMe_exp1_v2.txt`
4. **Consistent naming** - Develop a laboratory naming convention or use standard ontologies for your discipline

#### Multi-user Labs
1. **Create lab templates** - Standard templates with common equipment/settings
2. **Share templates** - Distribute `*_ReadME_template.txt` files
3. **Standardize fields** - Agree on controlled vocabulary usage
4. **Training** - Ensure all users understand metadata importance

## Troubleshooting

### Common Issues

#### "Failed to extract metadata"
- **Cause**: Unsupported file format or corrupted file
- **Solution**: Check file format (CZI/LIF/ND2/OIR/OME-TIFF only), try different file

#### Template not appearing
- **Cause**: Incorrect filename or location
- **Solution**: Ensure filename ends with `_ReadME_template.txt` and is in same folder as executable (not the folder of a shortcut to it)

#### Window too large/small
- **Cause**: Screen resolution issues
- **Solution**: Resize the window manually and use the scroll bar; change Windows display scaling for larger or smaller text

#### Missing fields after loading ReadMe
- **Cause**: File format changes between versions  
- **Solution**: Manually re-enter missing information

### Getting Help
- Click **"Help"** button in application for built-in assistance
- Check GitHub Issues for known problems
- Contact IMB Microscopy for University of Queensland users

## Advanced Features


### Integration with Other Tools
- **OMERO integration** - Import OMERO metadata (planned feature)

## Field Descriptions

### Required Information
- **Experiment name** - Descriptive title for your experiment
- **Date and time** - When images were acquired
- **Sample information** - What you're imaging

### Microscope Settings
- **Microscope name** - Specific instrument used
- **Objective** - Lens specification (magnification, NA)
- **Immersion** - Air, oil, water, etc.
- **Imaging mode** - Confocal, widefield, etc.

### Experimental Context
- **Sample preparation** - Fixation, mounting, etc.
- **Reagents** - Antibodies, fluorophores, probes
- **Environmental conditions** - Temperature, CO2, etc.
- **Notes** - Any additional relevant information

## Data Export Formats

### ReadMe.txt Structure
```
# Generated by ReMInD v3.0.0 — Nicholas Condon, IMB Microscopy...; Liam Howell, Sydney Microscopy and Microanalysis...

Experiment name: Sample Experiment
Date and time: 2025-06-05 14:30:00
...

Notes:
---
Detailed experimental notes here...
---

# Extracted Image Metadata
Microscope Model: LSM 980
Objective: Plan-Apochromat 63x/1.40 Oil DIC M27
...
```

### JSON Structure
```json
{
  "Experiment name": "Sample Experiment",
  "Date and time": "2025-06-05 14:30:00",
  ...
  "Extracted Image Metadata": {
    "Microscope Model": "LSM 980",
    "Objective": "Plan-Apochromat 63x/1.40 Oil DIC M27",
    ...
  }
}
```
