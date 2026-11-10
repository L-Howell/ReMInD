# ReMInD troubleshooting

## The program does not start

- **Windows shows "Windows protected your PC".** `ReMInD.exe` is not signed, so
  Windows warns the first time it is run. Click **More info**, then **Run anyway**.
- **Nothing happens for a few seconds.** The program is a single file that unpacks
  itself each time it starts. Wait a few seconds before trying again.
- **Antivirus software blocks or removes the file.** Ask your IT support to allow it,
  or download it again from the
  [releases page](https://github.com/L-Howell/ReMInD/releases/latest).
- **Still nothing.** Open a command prompt in the folder that holds the program and
  run `ReMInD.exe --check check.log`. Then open `check.log`. It says `OK`, or lists
  what could not be loaded. Include it when you [report the problem](#reporting-a-problem).

## Loading an image file

### "Only CZI, LIF, ND2, OIR and OME-TIFF files are supported"

The file has a different extension. Export it from the acquisition software as
OME-TIFF, or fill in the form by hand.

### "Could not read the ... file"

The message ends with the reason given by the library that reads the format. Common
causes:

- The file is still being written or copied. Wait for the acquisition or the copy to
  finish.
- The file is incomplete or damaged. Check that it opens in the acquisition software
  or in Fiji.
- **"No OME-XML metadata found in this TIFF"**: the file is a plain TIFF, which holds
  no microscope metadata. Fill in the form by hand.
- **"No images found in LIF file"**: the Leica project holds no images.

If a file opens in the acquisition software but not in ReMInD, please
[report it](#reporting-a-problem).

### A field was not filled in, or holds the wrong value

ReMInD can only fill in what the file records, and that depends on the microscope and
its software. The **Extracted Image Metadata** panel lists everything that was read.
Known cases:

- **Immersion is `Oil`, not `Oil-23` or `Oil-37`.** No file says which oil was used.
  Choose it yourself.
- **Immersion is `Multi-immersion`.** The objective takes several media and the file
  does not reliably say which was used. Replace it with the one you used.
- **Microscope name did not change.** The template on this computer sets it, and the
  template's name is kept. See [Templates](user-guide.md#templates).
- **Leica: a channel has no excitation wavelength.** When one scan uses several
  lasers, the file does not say which laser belongs to which detector. All the laser
  lines are listed in the Extracted Image Metadata.
- **Nikon: Microscope name is empty.** Most ND2 files do not name the microscope.
- **Nikon: the date is not in the form `YYYY-MM-DD HH:MM:SS`.** Some older ND2 files
  record the date only as text in the format of the acquisition computer. Check the
  order of day and month.
- **A field lists several values separated by `;`.** The file holds several images
  taken with different settings. See
  [Files that hold several images](user-guide.md#files-that-hold-several-images).

If the acquisition software shows a value that ReMInD did not find, please
[report it](#reporting-a-problem).

## Templates

### The template is not loaded

- The file name must end in `_ReadME_template.txt`.
- The file must be in the folder that holds `ReMInD.exe` itself. The folder of a
  shortcut to it is not searched.
- Templates are read only when the program starts. Restart it after changing one.
- If the folder holds several templates, only the first in alphabetical order is used.

### A value in the template does not appear

Each line must be the field's label exactly as it appears in the form, then a colon
and a space, then the value, e.g. `Microscope name: Confocal 5`. Lines with any other
label are ignored.

## Saving and loading a ReadMe

- **"Could not write file"**: the folder may be read-only, or the file may be open in
  another program. Save somewhere else, or close the other program.
- **"... holds no ReMInD fields"**: the file has no lines of the form `Label: value`.
  Check that you chose the right file.
- **"Could not load file"** with a message about `utf-8`: the file was saved by an
  editor in a different encoding. Save it again as UTF-8.
- **Some fields are empty after loading.** Lines whose label does not match a field
  in the form are ignored. This happens when a label was changed by hand, and with
  files from version 3.0.0 or earlier, in which the Filename Key was written
  differently and one field had a different name.

## The window

- **The window does not fit the screen.** The window can be resized, and the form
  scrolls. In a narrow window the panels are stacked in one column.
- **The mouse wheel does not scroll the form.** Over the Notes box and the Extracted
  Image Metadata box the wheel scrolls that box. Move the pointer elsewhere.

## Reporting a problem

[Open an issue](https://github.com/L-Howell/ReMInD/issues) and include:

- the ReMInD version (shown in the window title and in Help);
- the Windows version;
- the image file format, and the microscope and acquisition software version if you
  know them;
- the exact error message, or a screenshot;
- what you did before the problem appeared.

A small example file that shows the problem helps most of all.
