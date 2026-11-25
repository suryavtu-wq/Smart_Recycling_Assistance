from functools import lru_cache
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from src.predictor import load_classifier, predict_image
from src.recommendations import get_guidance

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "waste_classifier.pth"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
CONFIDENCE_THRESHOLD = 0.60

app = FastAPI(title="Smart Recycling Assistant API", version="1.0.0")


class Suggestion(BaseModel):
    category: str
    confidence: float


class PredictionResponse(BaseModel):
    category: str
    confidence: float
    low_confidence: bool
    top_suggestions: list[Suggestion]
    guidance: dict[str, str]


@lru_cache(maxsize=1)
def get_model_bundle():
    if not MODEL_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Classifier model not found at {MODEL_PATH}.",
        )
    return load_classifier(MODEL_PATH)


@app.get("/health")
def health():
    return {"status": "ok", "model_available": MODEL_PATH.is_file()}


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 20 MB or smaller.")

    try:
        with Image.open(BytesIO(contents)) as uploaded_image:
            if uploaded_image.width * uploaded_image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail="Image dimensions must not exceed 20 megapixels.",
                )
            image = uploaded_image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from exc

    predicted, confidence, probabilities = predict_image(get_model_bundle(), image)
    suggestions = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:3]
    return PredictionResponse(
        category=predicted,
        confidence=confidence,
        low_confidence=confidence < CONFIDENCE_THRESHOLD,
        top_suggestions=[
            Suggestion(category=name, confidence=score)
            for name, score in suggestions
        ],
        guidance=get_guidance(predicted),
    )
