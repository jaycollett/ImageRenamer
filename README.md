# ImageRenamer

A command-line tool to rename image files based on a person's age at the time the photo was taken, or to undo such renames using a log file. Supports common image formats and Nikon NEF RAW files, with safeguards to prevent filename collisions. Offers dry-run and recursive modes for flexible operation.

## Features
- Renames images using the format: `Name_YYYYMMDD_Age_ID.ext`
  - `Name`: Person’s name (spaces replaced with underscores)
  - `YYYYMMDD`: Date photo was taken (from EXIF or file timestamp)
  - `Age`:
    - `DDdays` if < 28 days
    - `MMmonths` if < 12 months
    - `YYyears` if ≥ 12 months
  - `ID`: Three-digit counter per date
- Undo renames using `rename_log.csv` with confirmation and force options
- Supports JPG, JPEG, PNG, TIFF, HEIC, BMP, and NEF files
- Dry-run mode to preview changes
- Recursive directory traversal
- Logging of all renames for safe undo

## Requirements
- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/) >= 9.0.0
- [exifread](https://pypi.org/project/ExifRead/) >= 3.0.0

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Usage

### Rename Images by Age
```bash
python renamer.py <path> "<Name>" <MM-DD-YYYY> [--recursive] [--dry-run]
```
- `<path>`: Directory containing images
- `<Name>`: Person’s name (use quotes if it contains spaces)
- `<MM-DD-YYYY>`: Birth date of the person
- `--recursive`: (Optional) Process subdirectories
- `--dry-run`: (Optional) Preview changes without renaming files

### Undo Renames
```bash
python renamer.py <path> --undo [--force]
```
- `--undo`: Revert changes using `rename_log.csv` in the target directory
- `--force`: (Optional) Skip confirmation prompts and delete the log file

## Example
Rename all images in `~/Pictures/Baby` for "Jane Doe" born on Jan 15, 2022:
```bash
python renamer.py ~/Pictures/Baby "Jane Doe" 01-15-2022 --recursive
```

Undo all renames:
```bash
python renamer.py ~/Pictures/Baby --undo --force
```

## Notes
- The script will not overwrite existing files.
- EXIF date is preferred; if missing, file modification date is used.
- All renames are logged in `rename_log.csv` for safe undo.

## License
MIT License

