# Vendor format fixtures

Tiny files written by each vendor's acquisition software, one folder per
software version, named `<software>-<version>` as the files record it:

| Folder | Recorded in the files as |
|---|---|
| `CZI/zen-2.6.76` | ZEN 2.6 (blue edition) 2.6.76.00000, LSM 800 |
| `LIF/lasx-4.9.2.31016` | LAS X 4.9.2.31016, STELLARIS 8 |
| `ND2/nis-elements-5.30.07` | NIS-Elements AR 5.30.07 (Build 1570), Nikon Ti |
| `OIR/fv4000-fv5000-4.1.1.137` | system FV4000/FV5000, version 4.1.1.137 |

Each folder holds a single plane (`2d`), a time series (`2d_t`), a Z-stack
(`3d`) and a Z-stack time series (`3d_t`), with as few pixels as the software
allows. To add a version, acquire the same four into a new folder and give
it its expected form fields in `tests/test_vendor_files.py`.
