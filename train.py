import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def locate_imagefolder(data_dir):
    data_dir = Path(data_dir)
    candidates = [data_dir] + [p for p in data_dir.rglob("*") if p.is_dir()]
    for candidate in candidates:
        if not candidate.exists():
            continue
        class_dirs = [p for p in candidate.iterdir() if p.is_dir()]
        valid = [
            p for p in class_dirs
            if any(f.suffix.lower() in IMAGE_EXTS for f in p.rglob("*") if f.is_file())
        ]
        if len(valid) >= 2:
            return candidate
    raise RuntimeError(
        f"Could not find class folders under {data_dir}. "
        "Expected one folder per category, e.g. RealWaste/Cardboard/*.jpg."
    )


def get_predictions(model, loader, device):
    model.eval()
    y_true, y_pred = [], []
    with torch.inference_mode():
        for images, targets in loader:
            logits = model(images.to(device))
            preds = logits.argmax(dim=1).cpu().numpy()
            y_pred.extend(preds.tolist())
            y_true.extend(targets.numpy().tolist())
    return y_true, y_pred


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune MobileNetV2 for the RealWaste dataset."
    )
    parser.add_argument("--data", required=True, help="Path to extracted RealWaste folder")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--warmup-epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr-head", type=float, default=0.0003)
    parser.add_argument("--lr-backbone", type=float, default=0.00003)
    parser.add_argument("--unfreeze-from", type=int, default=14,
                        help="Unfreeze MobileNetV2 feature blocks from this index (0-18).")
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--output", default="models/waste_classifier.pth")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.epochs < 2:
        raise ValueError("--epochs must be at least 2.")
    if not 0 <= args.warmup_epochs < args.epochs:
        raise ValueError("--warmup-epochs must be >=0 and less than --epochs.")
    if not 0 <= args.unfreeze_from <= 18:
        raise ValueError("--unfreeze-from must be between 0 and 18.")

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    data_root = locate_imagefolder(args.data)
    print("Detected dataset folder:", data_root)

    # Training augmentation: modest changes that preserve the waste material's identity.
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.78, 1.0), ratio=(0.85, 1.15)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.10, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    # Validation/test/inference must use the same deterministic preprocessing.
    eval_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    base = datasets.ImageFolder(data_root)
    class_names = base.classes
    labels = np.array(base.targets)
    indices = np.arange(len(base))

    # TACO produces multiple object crops from one source photograph. When a
    # source_groups.csv manifest exists, keep all crops from the same source
    # photograph in exactly one split to reduce train/test leakage.
    groups_by_path = {}
    manifest_path = data_root / "source_groups.csv"
    if manifest_path.exists():
        import csv
        with manifest_path.open("r", encoding="utf-8", newline="") as manifest_file:
            for row in csv.DictReader(manifest_file):
                rel = row.get("relative_path", "").replace("\\", "/")
                groups_by_path[rel] = row.get("group_id", rel)

    groups = []
    for sample_path, _ in base.samples:
        rel = Path(sample_path).relative_to(data_root).as_posix()
        groups.append(groups_by_path.get(rel, f"single::{rel}"))
    groups = np.asarray(groups)

    if len(set(groups.tolist())) < 10:
        raise RuntimeError("Not enough independent source groups for a 10-fold split.")

    outer_splitter = StratifiedGroupKFold(
        n_splits=10, shuffle=True, random_state=args.seed
    )
    remaining_rel, test_rel = next(
        outer_splitter.split(np.zeros(len(labels)), labels, groups)
    )
    inner_splitter = StratifiedGroupKFold(
        n_splits=9, shuffle=True, random_state=args.seed + 1
    )
    train_rel, val_rel = next(
        inner_splitter.split(
            np.zeros(len(remaining_rel)),
            labels[remaining_rel],
            groups[remaining_rel],
        )
    )
    train_idx = remaining_rel[train_rel]
    val_idx = remaining_rel[val_rel]
    test_idx = test_rel

    if set(groups[train_idx]) & set(groups[val_idx]) or set(groups[train_idx]) & set(groups[test_idx]) or set(groups[val_idx]) & set(groups[test_idx]):
        raise RuntimeError("Source-group leakage detected between data splits.")
    print(
        f"Split sizes — train: {len(train_idx)}, validation: {len(val_idx)}, "
        f"test: {len(test_idx)} | source-group-aware: {manifest_path.exists()}"
    )

    train_ds = datasets.ImageFolder(data_root, transform=train_tf)
    eval_ds = datasets.ImageFolder(data_root, transform=eval_tf)

    workers = 0  # Safe default for Windows PowerShell.
    train_loader = DataLoader(
        Subset(train_ds, train_idx), batch_size=args.batch_size,
        shuffle=True, num_workers=workers,
        pin_memory=(device.type == "cuda")
    )
    val_loader = DataLoader(
        Subset(eval_ds, val_idx), batch_size=args.batch_size,
        shuffle=False, num_workers=workers,
        pin_memory=(device.type == "cuda")
    )
    test_loader = DataLoader(
        Subset(eval_ds, test_idx), batch_size=args.batch_size,
        shuffle=False, num_workers=workers,
        pin_memory=(device.type == "cuda")
    )

    counts = np.bincount(labels[train_idx], minlength=len(class_names))
    print(f"Images: {len(base)} | Classes: {class_names}")
    print("Training images per class:")
    for name, count in zip(class_names, counts):
        print(f"  {name}: {count}")

    # Moderate class weighting reduces domination by frequent classes.
    # Square-root inverse frequency is less aggressive than full inverse weighting.
    weights = np.sqrt(counts.sum() / np.maximum(counts, 1))
    weights = weights / weights.mean()
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(weights, dtype=torch.float32, device=device)
    )

    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.last_channel, len(class_names))
    model.to(device)

    # Stage 1: train the new classification head while keeping the feature extractor frozen.
    for parameter in model.features.parameters():
        parameter.requires_grad = False
    for parameter in model.classifier.parameters():
        parameter.requires_grad = True

    optimizer = torch.optim.AdamW(
        model.classifier.parameters(), lr=args.lr_head, weight_decay=1e-4
    )
    scheduler = None

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Path("outputs").mkdir(parents=True, exist_ok=True)

    best_val_f1 = -1.0
    best_epoch = 0
    epochs_without_improvement = 0

    for epoch in range(args.epochs):
        # Stage 2: fine-tune only the final feature blocks using a lower learning rate.
        if epoch == args.warmup_epochs:
            for parameter in model.features.parameters():
                parameter.requires_grad = False
            for block in model.features[args.unfreeze_from:]:
                for parameter in block.parameters():
                    parameter.requires_grad = True
            for parameter in model.classifier.parameters():
                parameter.requires_grad = True

            optimizer = torch.optim.AdamW([
                {"params": model.features[args.unfreeze_from:].parameters(),
                 "lr": args.lr_backbone},
                {"params": model.classifier.parameters(), "lr": args.lr_head * 0.5},
            ], weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode="max", factor=0.5, patience=2
            )
            print(f"\nUnfroze MobileNetV2 feature blocks {args.unfreeze_from}-18.")

        model.train()
        if epoch < args.warmup_epochs:
            model.features.eval()  # Keep frozen backbone batch-normalization stable.
        else:
            model.features[:args.unfreeze_from].eval()  # Frozen early blocks.
        running_loss, train_correct, train_total = 0.0, 0, 0

        for images, targets in train_loader:
            images = images.to(device)
            targets = targets.to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            train_correct += (logits.argmax(1) == targets).sum().item()
            train_total += targets.size(0)

        train_loss = running_loss / max(train_total, 1)
        train_acc = train_correct / max(train_total, 1)

        val_true, val_pred = get_predictions(model, val_loader, device)
        val_acc = accuracy_score(val_true, val_pred)
        val_macro_f1 = f1_score(
            val_true, val_pred, average="macro", zero_division=0
        )

        if scheduler is not None:
            scheduler.step(val_macro_f1)

        print(
            f"Epoch {epoch + 1}/{args.epochs} | "
            f"loss={train_loss:.4f} | train_acc={train_acc:.4f} | "
            f"val_acc={val_acc:.4f} | val_macro_f1={val_macro_f1:.4f}"
        )

        # Select checkpoint by macro F1 so weaker classes matter, not only the largest class.
        if val_macro_f1 > best_val_f1:
            best_val_f1 = val_macro_f1
            best_epoch = epoch + 1
            epochs_without_improvement = 0
            torch.save({
                "model_state_dict": {
                    key: value.detach().cpu()
                    for key, value in model.state_dict().items()
                },
                "class_names": class_names,
                "image_size": 224,
                "architecture": "MobileNetV2",
                "preprocess": "Resize(256), CenterCrop(224), ImageNetNormalize",
                "best_val_macro_f1": float(best_val_f1),
                "best_epoch": best_epoch,
                "seed": args.seed,
            }, output_path)
        else:
            epochs_without_improvement += 1

        if epoch >= args.warmup_epochs and epochs_without_improvement >= args.patience:
            print(f"Early stopping: validation macro F1 did not improve for {args.patience} epochs.")
            break

    # Evaluate the selected checkpoint exactly once on the held-out test set.
    checkpoint = torch.load(output_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_true, test_pred = get_predictions(model, test_loader, device)

    test_accuracy = accuracy_score(test_true, test_pred)
    test_macro_f1 = f1_score(test_true, test_pred, average="macro", zero_division=0)
    report_text = classification_report(
        test_true, test_pred, target_names=class_names, zero_division=0
    )
    report_dict = classification_report(
        test_true, test_pred, target_names=class_names,
        output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(test_true, test_pred)

    print("\nBest epoch:", best_epoch)
    print("Best validation macro F1:", round(best_val_f1, 4))
    print("Held-out test accuracy:", round(test_accuracy, 4))
    print("Held-out test macro F1:", round(test_macro_f1, 4))
    print("\nPer-class test report:\n", report_text)

    pd.DataFrame(
        matrix, index=class_names, columns=class_names
    ).to_csv("outputs/confusion_matrix.csv", index=True)

    with open("outputs/evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "test_accuracy": float(test_accuracy),
            "test_macro_f1": float(test_macro_f1),
            "best_epoch": best_epoch,
            "best_validation_macro_f1": float(best_val_f1),
            "classification_report": report_dict,
        }, f, indent=2)

    with open("outputs/class_names.json", "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)

    with open("outputs/test_split_indices.json", "w", encoding="utf-8") as f:
        json.dump({
            "seed": args.seed,
            "train_indices": train_idx.tolist(),
            "validation_indices": val_idx.tolist(),
            "test_indices": test_idx.tolist(),
        }, f)

    print("\nSaved model to:", output_path.resolve())
    print("Saved evaluation files in outputs/")


if __name__ == "__main__":
    main()
