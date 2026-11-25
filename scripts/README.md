# TACO dataset preparation

Run this script after extracting TACO. It reads the COCO-style annotations, crops individual annotated objects using bounding boxes, and maps only recognized category names to the existing RealWaste classes.

Unknown/ambiguous TACO categories are skipped rather than guessed. Review `taco_category_mapping_review.csv` before training. The script keeps all crops from the same TACO source photograph under one group ID; the updated `train.py` uses `source_groups.csv` for group-aware train/validation/test splitting.

Example (PowerShell; replace the TACO path with your actual extracted folder):

```powershell
python scripts/prepare_taco.py `
  --realwaste "C:\Users\YourName\Downloads\realwaste-main\RealWaste" `
  --taco "C:\Users\YourName\Downloads\TACO" `
  --output "data\combined"
```

Then train:

```powershell
python train.py --data "data\combined" --epochs 15 --warmup-epochs 3 --batch-size 16
```

If you need to regenerate the combined folder, add `--overwrite`.

Important:
- This creates object crops, not a multi-object detector.
- TACO categories do not cover all nine RealWaste classes.
- The mapping is a practical approximation; inspect the generated CSV.
- Check TACO's dataset/image licensing and attribution terms before redistributing any images.
