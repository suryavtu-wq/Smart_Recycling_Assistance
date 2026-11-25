# Smart Recycling & Waste-Segregation Assistant

A Streamlit-based AI project for image-based waste category suggestions and general disposal/recycling guidance. The current classifier is MobileNetV2 and supports the nine RealWaste categories.

## Current features

- Dashboard with prediction statistics and history.
- Waste detection from **mobile/desktop camera capture** or image upload from the gallery/files.
- Mobile-friendly browser access when the app is running on a reachable host.
- Android WebView wrapper for the hosted Streamlit app.
- MobileNetV2 image classifier with top-three suggestions and probability scores.
- General disposal, recycling and environmental guidance for the nine categories.
- Offline knowledge-base assistant.
- Prediction history export.
- Training and evaluation scripts.
- Optional TACO object-crop preparation workflow.

## Important project status

This ZIP contains a working Streamlit application and a MobileNetV2 image classifier checkpoint. The AI Assistant currently uses a local rule/knowledge-base fallback; it is **not Llama**. The Llama-family model and ExecuTorch on-device runtime are documented as a next implementation requirement, not represented as completed.

The project includes an Android WebView wrapper in `android_app/`. It loads the Streamlit app hosted on Streamlit Community Cloud; inference runs on that hosted service, not on the phone. See `MOBILE_SETUP.md` to deploy the website and build/install the APK.

The classifier predicts one category for the whole image. It is not an object detector and is not designed to classify several separate objects in one photograph.

## Project structure

```text
Smart_Recycling_Assistant/
├── app.py
├── train.py
├── requirements.txt
├── README.md
├── MOBILE_SETUP.md
├── android_app/
│   └── app/                 # Android WebView wrapper
├── .gitignore
├── src/
│   ├── predictor.py
│   ├── recommendations.py
│   └── assistant.py
├── scripts/
│   └── prepare_taco.py
├── models/
│   └── waste_classifier.pth
├── outputs/
│   ├── evaluation_report.json
│   ├── confusion_matrix.csv
│   ├── class_names.json
│   └── prediction_history.csv
├── data/
│   └── PUT_DATASET_HERE.txt
└── executorch_llama/
    └── README.md
```

Datasets and virtual environments are intentionally not bundled.

## 1. Requirements

Recommended: Python 3.10–3.12, although compatibility depends on the PyTorch wheels available for your Python version.

Open PowerShell in the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

## 2. Run the existing trained model

The ZIP includes `models/waste_classifier.pth`.

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

On the Waste Detection page, choose:
- **Capture with camera** to use a camera supported by the browser.
- **Upload from gallery** to choose an existing image.

See `MOBILE_SETUP.md` to open the app from an Android phone.

## 3. Train using RealWaste only

Expected RealWaste ImageFolder structure:

```text
RealWaste/
  Cardboard/
  Food Organics/
  Glass/
  Metal/
  Miscellaneous Trash/
  Paper/
  Plastic/
  Textile Trash/
  Vegetation/
```

Example:

```powershell
python train.py --data "C:\Users\YourName\Downloads\realwaste-main\RealWaste" --epochs 15 --warmup-epochs 3 --batch-size 16
```

The training script uses a stratified split. If `source_groups.csv` exists in the detected dataset root, it uses source-group-aware stratified splitting so crops from one source photograph are kept in a single split.

## 4. Optional: prepare TACO + RealWaste

TACO is an object-annotated litter dataset. The preparation script:
1. Reads the TACO COCO-style annotations JSON.
2. Crops individual annotated objects using bounding boxes.
3. Maps only recognized TACO categories to the nine RealWaste classes.
4. Skips unknown/ambiguous categories instead of guessing.
5. Writes `taco_category_mapping_review.csv` so the mapping can be inspected.
6. Writes `source_groups.csv` so crops from the same TACO photograph do not cross train/validation/test splits.

After extracting TACO, run (replace the paths with your actual folders):

```powershell
python scripts/prepare_taco.py `
  --realwaste "C:\Users\YourName\Downloads\realwaste-main\RealWaste" `
  --taco "C:\Users\YourName\Downloads\TACO" `
  --output "data\combined"
```

Review:

```text
data\combined\taco_category_mapping_review.csv
```

Then train:

```powershell
python train.py --data "data\combined" --epochs 15 --warmup-epochs 3 --batch-size 16
```

To recreate an existing output folder, add `--overwrite` to the preparation command.

Notes:
- TACO does not provide reliable examples for every RealWaste class. Food Organics, Vegetation and Textile Trash may have few or no TACO crops.
- The mapping is a practical category approximation, not a perfect semantic equivalence. Inspect the mapping CSV and crop images.
- TACO contains object crops; it does not turn this classifier into an object detector.
- TACO images may have individual licensing/attribution conditions. Check the dataset's current terms before redistributing images.
- Keep an independent set of real-world photos for final evaluation; do not use the same images for training and evaluation.

## 5. Model outputs

Training writes:
- `models/waste_classifier.pth`
- `outputs/evaluation_report.json`
- `outputs/confusion_matrix.csv`
- `outputs/class_names.json`
- `outputs/test_split_indices.json`

A model probability is not a guarantee that a prediction is correct. Real-world photos can differ from training images (domain shift). Use clear photos with one main object, good lighting and the item filling much of the frame. Verify material and local disposal rules.

## 6. Llama + ExecuTorch

The project brief requires a Llama-family model deployed with ExecuTorch on an Arm-based target. This is not yet integrated in this ZIP. See `executorch_llama/README.md` for the implementation outline and official documentation. Do not describe this component as completed until a real exported model and compatible runtime have been run on the target device.

## 7. Safety and disposal guidance

Recommendations are general educational information. Local municipal rules take priority. Batteries, chemicals, medical waste and electronic waste should be directed to appropriate authorised collection services rather than ordinary mixed waste.
