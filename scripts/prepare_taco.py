"""
Prepare a combined ImageFolder dataset from RealWaste and TACO.

TACO is an object-annotated litter dataset. This script crops each annotated
object using its COCO-style bounding box, then maps only recognized category
names into the nine RealWaste classes. Unmapped categories are skipped and
reported; inspect the generated mapping review CSV before training.
"""
import argparse
import csv
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TARGET_CLASSES = [
    "Cardboard", "Food Organics", "Glass", "Metal", "Miscellaneous Trash",
    "Paper", "Plastic", "Textile Trash", "Vegetation",
]


def find_imagefolder(path):
    path = Path(path).expanduser().resolve()
    candidates = [path] + [p for p in path.rglob("*") if p.is_dir()]
    for candidate in candidates:
        class_dirs = [p for p in candidate.iterdir() if p.is_dir()]
        valid = [
            d for d in class_dirs
            if any(f.suffix.lower() in IMAGE_EXTS for f in d.rglob("*") if f.is_file())
        ]
        if len(valid) >= 2:
            return candidate
    raise RuntimeError(f"Could not locate RealWaste class folders under: {path}")


def normalize_name(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def map_taco_category(name):
    """Conservative mapping; None means skip rather than guess."""
    n = normalize_name(name)

    # Cardboard / carton products
    if any(x in n for x in (
        "corrugated carton", "other carton", "egg carton", "meal carton",
        "pizza box", "cardboard", "toilet tube",
    )):
        return "Cardboard"

    # Glass objects
    if any(x in n for x in ("glass bottle", "broken glass", "glass jar")):
        return "Glass"

    # Metal items and metal packaging
    if any(x in n for x in (
        "aluminium foil", "aluminum foil", "aluminium blister", "aluminum blister",
        "metal bottle cap", "food can", "drink can", "scrap metal", "pop tab",
        "aerosol",
    )):
        return "Metal"

    # Paper and paper-based products
    if any(x in n for x in (
        "magazine paper", "normal paper", "paper bag", "wrapping paper",
        "tissue", "paper cup", "paper straw",
    )):
        return "Paper"

    # Plastic items and plastic packaging
    if any(x in n for x in (
        "plastic", "polypropylene bag", "six pack ring", "six-pack ring",
        "crisp packet", "spread tub", "tupperware", "garbage bag",
        "squeezable tube",
    )):
        return "Plastic"

    # Residual / mixed litter. Hazardous items should still be handled separately
    # in real life; the model's label is only a broad visual class.
    if any(x in n for x in ("cigarette", "unlabeled litter")):
    	return "Miscellaneous Trash"

    # TACO does not provide reliable direct equivalents for all RealWaste classes.
    return None


def find_annotations(root, explicit=None):
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = root / p
        if p.exists():
            return p
        raise FileNotFoundError(f"Annotation JSON not found: {p}")
    candidates = list(root.rglob("annotations.json"))
    if not candidates:
        candidates = list(root.rglob("*annotations*.json"))
    if not candidates:
        raise FileNotFoundError(
            "Could not find TACO annotations JSON. Look for annotations.json "
            "inside the extracted TACO folder."
        )
    # Prefer the canonical COCO annotation file.
    candidates.sort(key=lambda p: (p.name.lower() != "annotations.json", len(p.parts)))
    return candidates[0]


def build_image_index(root):
    index = {}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            index.setdefault(p.name.lower(), p)
    return index


def resolve_image(root, file_name, index):
    rel = Path(str(file_name).replace("\\", "/"))
    candidates = [root / rel, root / "data" / rel, root / "images" / rel]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return index.get(rel.name.lower())


def link_or_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.hardlink_to(source)
    except OSError:
        shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--realwaste", required=True, help="Folder containing extracted RealWaste data")
    parser.add_argument("--taco", required=True, help="Extracted TACO dataset folder")
    parser.add_argument("--output", default="data/combined", help="Output ImageFolder dataset")
    parser.add_argument("--annotations", default=None, help="Optional relative/absolute annotations JSON path")
    parser.add_argument("--padding", type=float, default=0.10, help="Bounding-box padding ratio")
    parser.add_argument("--min-size", type=int, default=24, help="Minimum crop width/height in pixels")
    parser.add_argument("--overwrite", action="store_true", help="Delete existing output folder first")
    args = parser.parse_args()

    realwaste_root = find_imagefolder(args.realwaste)
    taco_root = Path(args.taco).expanduser().resolve()
    output_root = Path(args.output).expanduser().resolve()
    if not taco_root.exists():
        raise FileNotFoundError(f"TACO folder does not exist: {taco_root}")
    if output_root.exists():
        if not args.overwrite:
            raise FileExistsError(
                f"{output_root} already exists. Choose another --output or add --overwrite."
            )
        shutil.rmtree(output_root)

    output_root.mkdir(parents=True, exist_ok=True)
    groups = {}
    realwaste_count = Counter()

    print(f"RealWaste classes found at: {realwaste_root}")
    # Copy/hardlink RealWaste images into the combined ImageFolder.
    for class_dir in sorted(p for p in realwaste_root.iterdir() if p.is_dir()):
        if class_dir.name not in TARGET_CLASSES:
            print(f"Skipping unexpected RealWaste folder: {class_dir.name}")
            continue
        for number, src in enumerate(sorted(class_dir.rglob("*"))):
            if not src.is_file() or src.suffix.lower() not in IMAGE_EXTS:
                continue
            dest_name = f"realwaste_{number:06d}{src.suffix.lower()}"
            dest = output_root / class_dir.name / dest_name
            link_or_copy(src, dest)
            rel = dest.relative_to(output_root).as_posix()
            groups[rel] = f"realwaste::{class_dir.name}::{number:06d}"
            realwaste_count[class_dir.name] += 1

    ann_path = find_annotations(taco_root, args.annotations)
    print(f"Using TACO annotations: {ann_path}")
    coco = json.loads(ann_path.read_text(encoding="utf-8"))
    categories = {c["id"]: c["name"] for c in coco.get("categories", [])}
    category_mapping = {name: map_taco_category(name) for name in categories.values()}
    image_records = {im["id"]: im for im in coco.get("images", [])}
    image_index = build_image_index(taco_root)

    category_counts = Counter()
    mapped_counts = Counter()
    skipped_counts = Counter()
    missing_images = 0
    bad_boxes = 0

    for ann_number, ann in enumerate(coco.get("annotations", [])):
        category_name = categories.get(ann.get("category_id"), "Unknown")
        target_class = map_taco_category(category_name)
        category_counts[category_name] += 1
        if target_class is None:
            skipped_counts[category_name] += 1
            continue

        image_info = image_records.get(ann.get("image_id"))
        if not image_info:
            missing_images += 1
            continue
        image_path = resolve_image(taco_root, image_info.get("file_name", ""), image_index)
        if image_path is None:
            missing_images += 1
            continue

        bbox = ann.get("bbox")
        if not bbox or len(bbox) != 4:
            bad_boxes += 1
            continue

        try:
            with Image.open(image_path) as source:
                image = source.convert("RGB")
                x, y, w, h = [float(v) for v in bbox]
                if w <= 0 or h <= 0:
                    bad_boxes += 1
                    continue
                pad_x, pad_y = w * args.padding, h * args.padding
                left = max(0, int(x - pad_x))
                top = max(0, int(y - pad_y))
                right = min(image.width, int(x + w + pad_x))
                bottom = min(image.height, int(y + h + pad_y))
                if right - left < args.min_size or bottom - top < args.min_size:
                    bad_boxes += 1
                    continue
                crop = image.crop((left, top, right, bottom))
                image_id = str(ann.get("image_id"))
                ann_id = str(ann.get("id", ann_number))
                dest = output_root / target_class / f"taco_img{image_id}_ann{ann_id}.jpg"
                dest.parent.mkdir(parents=True, exist_ok=True)
                crop.save(dest, quality=92)
                rel = dest.relative_to(output_root).as_posix()
                groups[rel] = f"taco_source_image::{image_id}"
                mapped_counts[target_class] += 1
        except Exception as exc:
            print(f"Warning: skipped annotation {ann.get('id', ann_number)}: {exc}")

    manifest = output_root / "source_groups.csv"
    with manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["relative_path", "group_id"])
        for rel, group_id in sorted(groups.items()):
            writer.writerow([rel, group_id])

    review_path = output_root / "taco_category_mapping_review.csv"
    with review_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["taco_category", "mapped_realwaste_class_or_SKIPPED", "annotation_count"])
        for name in sorted(category_counts):
            writer.writerow([name, category_mapping[name] or "SKIPPED", category_counts[name]])

    print("\nPreparation complete.")
    print("RealWaste images:", sum(realwaste_count.values()))
    print("TACO object crops:", sum(mapped_counts.values()))
    print("Mapped TACO crops by class:", dict(mapped_counts))
    print("Skipped TACO annotations by category:", dict(skipped_counts))
    print("Missing source images:", missing_images)
    print("Invalid/small boxes:", bad_boxes)
    print("Combined dataset:", output_root)
    print("Source-group manifest:", manifest)
    print("Review category mappings before training:", review_path)
    print(
        "\nNote: Food Organics, Vegetation, and Textile Trash may receive few or no TACO crops. "
        "The original RealWaste images remain in the combined dataset."
    )


if __name__ == "__main__":
    main()
