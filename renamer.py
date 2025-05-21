#!/usr/bin/env python3
"""
Rename image files based on a person's age at the time the photo was taken,
or undo renames using the log file. Supports common formats and Nikon NEF raw,
with safeguards to prevent collisions and offer dry-run and recursive modes.

Normal mode (default) renames:
    Name_YYYYMMDD_Age_ID.ext
where:
  - `Name` is the person’s name (underscores instead of spaces)
  - `YYYYMMDD` ensures chronological sorting
  - `Age` is:
      - `DDdays` if < DAY_MONTH_THRESHOLD days
      - `MMmonths` if < 12 months
      - `YYyears` if ≥ 12 months
  - `ID` is a three-digit counter reset per date

Undo mode (`--undo`) reverses renames recorded in rename_log.csv,
with confirmation unless `--force` is used, then deletes the log.

A log file `rename_log.csv` in the target directory records:
    timestamp,old_filename,new_filename

Dependencies:
    pip install Pillow exifread

Usage:
    python rename_by_age.py <path> "<Name>" <MM-DD-YYYY> [--recursive] [--dry-run]
    python rename_by_age.py <path> --undo [--force]
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, date
from PIL import Image
from PIL.ExifTags import TAGS
import exifread

# Threshold for day vs month switch
DAY_MONTH_THRESHOLD = 28
# Allowed image extensions (lowercase)
ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.tiff', '.heic', '.bmp', '.nef', '.dng'}

def get_exif_date(img_path: Path) -> date | None:
    """Extract photo date from EXIF or fallback to filesystem timestamp."""
    suffix = img_path.suffix.lower()
    if suffix in ('.nef', '.dng'):
        try:
            with open(img_path, 'rb') as f:
                tags = exifread.process_file(f)
            date_tag = (tags.get('EXIF DateTimeOriginal') or
                        tags.get('EXIF DateTimeDigitized') or
                        tags.get('Image DateTime'))
            if date_tag:
                return datetime.strptime(str(date_tag), "%Y:%m:%d %H:%M:%S").date()
        except Exception:
            pass
    else:
        try:
            with Image.open(img_path) as img:
                exif = img._getexif()
            if exif:
                for tag_id, val in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ("DateTimeOriginal", "DateTime"):
                        try:
                            return datetime.strptime(val, "%Y:%m:%d %H:%M:%S").date()
                        except Exception:
                            break
        except Exception:
            pass
    # Fallback to file modification time
    try:
        return datetime.fromtimestamp(img_path.stat().st_mtime).date()
    except Exception:
        return None

def calculate_age_full(birth: date, photo: date) -> str:
    """
    Return zero-padded full-word age:
      - "DDdays" if < DAY_MONTH_THRESHOLD days
      - "MMmonths" if < 12 months
      - "YYyears" if ≥ 12 months
    """
    if photo < birth:
        return "01days"
    days_diff = (photo - birth).days
    if days_diff < DAY_MONTH_THRESHOLD:
        days = max(days_diff, 1)
        return f"{days:02d}days"
    months = (photo.year - birth.year) * 12 + (photo.month - birth.month)
    if photo.day < birth.day:
        months -= 1
    if months < 12:
        return f"{months:02d}months"
    years = months // 12
    return f"{years:02d}years"

def gather_images(path: Path, recursive: bool) -> list[Path]:
    """Return sorted image files under path, optionally recursively."""
    if path.is_file():
        return [path] if path.suffix.lower() in ALLOWED_EXTS else []
    imgs = []
    iterator = path.rglob('*') if recursive else path.iterdir()
    for entry in iterator:
        if entry.is_file() and entry.suffix.lower() in ALLOWED_EXTS:
            imgs.append(entry)
    return sorted(imgs)

def undo_renames(log_file: Path, force: bool):
    if not log_file.exists():
        print(f"No log file found at {log_file}")
        return
    if not force:
        resp = input(f"Undo all renames and delete {log_file.name}? [y/N] ")
        if resp.lower() != 'y':
            print("Undo cancelled.")
            return
    lines = log_file.read_text().splitlines()[1:]
    for line in reversed(lines):
        _, old, new = line.split(',', 2)
        new_p = log_file.parent / new
        old_p = log_file.parent / old
        if new_p.exists() and not old_p.exists():
            try:
                new_p.rename(old_p)
                print(f"Reverted: {new} → {old}")
            except Exception as e:
                print(f"Failed to revert {new}: {e}", file=sys.stderr)
    try:
        log_file.unlink()
        print(f"Log file removed: {log_file.name}")
    except Exception as e:
        print(f"Failed to remove log: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Rename images by age/date or undo using log with safeguards."
    )
    parser.add_argument("path", type=Path, help="Image file or directory")
    parser.add_argument("name", nargs='?', help="Person's name for renaming")
    parser.add_argument("birth", nargs='?', help="Birth date MM-DD-YYYY for renaming")
    parser.add_argument("--undo", action='store_true', help="Reverse renames using log file")
    parser.add_argument("--recursive", action='store_true', help="Process directories recursively")
    parser.add_argument("--dry-run", action='store_true', help="Show changes without applying them")
    parser.add_argument("--force", action='store_true', help="Skip confirmations on undo")
    args = parser.parse_args()

    root = args.path if args.path.is_dir() else args.path.parent
    log_file = root / "rename_log.csv"

    if args.undo:
        undo_renames(log_file, args.force)
        return

    if not (args.name and args.birth):
        parser.error("Provide name and birth date or use --undo")

    try:
        birth = datetime.strptime(args.birth, "%m-%d-%Y").date()
    except ValueError:
        parser.error("Birth date must be in MM-DD-YYYY format")

    images = gather_images(args.path, args.recursive)
    if not images:
        print(f"No images found at {args.path}")
        return

    if not log_file.exists() and not args.dry_run:
        log_file.write_text("timestamp,old_filename,new_filename\n")

    # Group images by date to reset counter per date
    from collections import defaultdict
    groups = defaultdict(list)
    for img in images:
        dt = get_exif_date(img) or datetime.fromtimestamp(img.stat().st_mtime).date()
        groups[dt].append(img)

    for dt in sorted(groups):
        counter = 1
        for img in sorted(groups[dt]):
            old_name = img.name
            age = calculate_age_full(birth, dt)
            date_str = dt.strftime('%Y%m%d')
            padded = f"{counter:03d}"
            # New naming: name first, then date, age, and ID
            new_name = (
                f"{args.name.replace(' ','_')}_"
                f"{date_str}_"
                f"{age}_"
                f"{padded}"
                f"{img.suffix.lower()}"
            )
            new_p = img.with_name(new_name)
            # handle collisions
            temp = counter
            while new_p.exists() and new_p.name != old_name:
                temp += 1
                padded = f"{temp:03d}"
                new_name = (
                    f"{args.name.replace(' ','_')}_"
                    f"{date_str}_"
                    f"{age}_"
                    f"{padded}"
                    f"{img.suffix.lower()}"
                )
                new_p = img.with_name(new_name)
            if args.dry_run:
                print(f"[DRY-RUN] {old_name} → {new_name}")
            else:
                try:
                    img.rename(new_p)
                    print(f"Renamed: {old_name} → {new_name}")
                    with open(log_file, "a") as f:
                        f.write(f"{datetime.now().isoformat()},{old_name},{new_name}\n")
                except Exception as e:
                    print(f"Failed to rename {old_name}: {e}", file=sys.stderr)
            counter += 1

if __name__ == "__main__":
    main()
