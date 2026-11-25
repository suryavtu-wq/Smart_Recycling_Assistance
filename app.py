import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

from src.predictor import load_classifier, predict_image
from src.recommendations import get_guidance
from src.assistant import answer_question

ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "models" / "waste_classifier.pth"
HISTORY_PATH = ROOT / "outputs" / "prediction_history.csv"
CONFIDENCE_THRESHOLD = 0.60  # UI warning only; not a calibrated correctness guarantee.

st.set_page_config(
    page_title="Smart Recycling Assistant",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_model():
    if MODEL_PATH.exists():
        return load_classifier(MODEL_PATH)
    return None


def save_history(record):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([record])
    if HISTORY_PATH.exists():
        row.to_csv(HISTORY_PATH, mode="a", header=False, index=False)
    else:
        row.to_csv(HISTORY_PATH, index=False)


def show_prediction(image_file, source_label):
    if image_file is None:
        return

    try:
        image = Image.open(image_file).convert("RGB")
    except Exception as exc:
        st.error(f"Could not open this image: {exc}")
        return

    st.image(image, caption=f"Selected image — {source_label}", use_container_width=True)

    if model_bundle is None:
        st.error("No trained model was found. Train the model first; see README.md.")
        return

    try:
        predicted, confidence, probabilities = predict_image(model_bundle, image)
        st.subheader(f"Suggested category: {predicted}")
        st.metric("Top prediction score", f"{confidence * 100:.2f}%")

        if confidence < CONFIDENCE_THRESHOLD:
            st.warning(
                "Low-confidence result. The model may be unsure. Try a clear photo "
                "with one main item, good lighting, and the object filling much of the frame."
            )
        else:
            st.info(
                "This is a model probability score, not a guarantee of correctness. "
                "Verify the material before following disposal advice."
            )

        st.subheader("Top 3 model suggestions")
        top3 = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:3]
        for name, score in top3:
            st.write(f"**{name}** — {score * 100:.1f}%")

        guidance = get_guidance(predicted)
        st.subheader("Suggested disposal recommendation")
        st.write(guidance["disposal"])
        st.subheader("Recycling information")
        st.write(guidance["recycling"])
        st.caption(
            "Recommendations are general educational guidance. Follow local municipal "
            "collection rules. Mixed, hazardous, or unfamiliar objects need manual checking."
        )

        prob_df = pd.DataFrame({
            "Category": list(probabilities.keys()),
            "Probability": [v * 100 for v in probabilities.values()],
        }).sort_values("Probability", ascending=True)
        st.plotly_chart(
            px.bar(
                prob_df,
                x="Probability",
                y="Category",
                orientation="h",
                title="Class probability scores",
            ),
            use_container_width=True,
        )

        filename = getattr(image_file, "name", None) or f"{source_label.lower().replace(' ', '_')}.jpg"
        if st.button("Save this prediction", key="save_prediction"):
            save_history({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "filename": filename,
                "source": source_label,
                "predicted_class": predicted,
                "confidence": float(confidence),
                "low_confidence_flag": bool(confidence < CONFIDENCE_THRESHOLD),
            })
            st.success("Prediction saved to history.")
    except Exception as exc:
        st.error(f"Prediction failed: {exc}")


st.sidebar.title("♻️ Smart Recycling Assistant")
st.sidebar.caption("AI-powered waste identification and recycling guidance")
page = st.sidebar.radio("Navigation", [
    "Dashboard",
    "Waste Detection",
    "Disposal & Recycling Guide",
    "AI Assistant",
    "Prediction History",
    "About",
])

model_bundle = get_model()
classes = model_bundle["class_names"] if model_bundle else [
    "Cardboard", "Food Organics", "Glass", "Metal", "Miscellaneous Trash",
    "Paper", "Plastic", "Textile Trash", "Vegetation",
]

if page == "Dashboard":
    st.title("Smart Recycling & Waste-Segregation Assistant")
    st.caption("Identify waste, understand disposal options, and encourage responsible segregation.")
    history = pd.read_csv(HISTORY_PATH) if HISTORY_PATH.exists() else pd.DataFrame()
    total = len(history)
    unique = history["predicted_class"].nunique() if total and "predicted_class" in history else 0
    avg_conf = history["confidence"].mean() * 100 if total and "confidence" in history else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Total image predictions", total)
    c2.metric("Waste categories detected", unique)
    c3.metric("Average model score", f"{avg_conf:.1f}%" if total else "—")

    st.subheader("Supported waste categories")
    cols = st.columns(3)
    for i, name in enumerate(classes):
        cols[i % 3].info(name)

    if total:
        st.subheader("Prediction distribution")
        counts = history["predicted_class"].value_counts().rename_axis("Category").reset_index(name="Predictions")
        st.plotly_chart(px.bar(counts, x="Category", y="Predictions", color="Category"), use_container_width=True)
        st.subheader("Recent activity")
        st.dataframe(history.tail(10).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No predictions yet. Open Waste Detection and capture or upload an image.")
    if not model_bundle:
        st.warning("The trained model is not available. Train it using README.md instructions.")

elif page == "Waste Detection":
    st.title("Waste Image Detection")
    st.write("Use your phone camera to take a new photo, or choose an existing image from your gallery.")

    source = st.radio(
        "Choose image source",
        ["Capture with camera", "Upload from gallery"],
        horizontal=True,
        key="image_source_choice",
    )

    image_file = None
    if source == "Capture with camera":
        st.caption("On a phone, allow camera permission when your browser asks.")
        image_file = st.camera_input(
            "Take a picture of one waste item",
            help="Keep the object in focus and make it fill much of the frame.",
            key="waste_camera_capture",
        )
        source_label = "Camera"
    else:
        image_file = st.file_uploader(
            "Choose an image from your phone or computer",
            type=["jpg", "jpeg", "png", "webp"],
            key="waste_gallery_upload",
        )
        source_label = "Gallery upload"

    if image_file is not None:
        st.divider()
        show_prediction(image_file, source_label)
    else:
        st.info(
            "No image selected yet. Choose Capture with camera or Upload from gallery. "
            "For best results, photograph one main object in good lighting."
        )

elif page == "Disposal & Recycling Guide":
    st.title("Disposal & Recycling Guide")
    selected = st.selectbox("Select a waste category", classes)
    guide = get_guidance(selected)
    st.subheader(selected)
    st.markdown("**Suggested disposal**")
    st.write(guide["disposal"])
    st.markdown("**Recycling / recovery options**")
    st.write(guide["recycling"])
    st.markdown("**Environmental note**")
    st.write(guide["impact"])
    st.caption("Educational guidance only. Local municipal rules take priority.")

elif page == "AI Assistant":
    st.title("Waste Management Assistant")
    st.write(
        "Ask about segregation, recycling, or disposal. The current offline knowledge-base "
        "fallback is available without an internet connection; it is not the Llama model."
    )
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("mode"):
                st.caption(f"Response mode: {msg['mode']}")
    prompt = st.chat_input("Example: How should I dispose of a glass bottle?")
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        response, mode = answer_question(prompt)
        st.session_state.chat.append({"role": "assistant", "content": response, "mode": mode})
        with st.chat_message("assistant"):
            st.markdown(response)
            st.caption(f"Response mode: {mode}")

elif page == "Prediction History":
    st.title("Prediction History")
    if HISTORY_PATH.exists():
        history = pd.read_csv(HISTORY_PATH)
        st.dataframe(history.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
        if st.button("Clear prediction history"):
            HISTORY_PATH.unlink(missing_ok=True)
            st.rerun()
        st.download_button(
            "Download history CSV",
            history.to_csv(index=False),
            "prediction_history.csv",
            "text/csv",
        )
    else:
        st.info("No saved predictions yet. Save a result from Waste Detection.")

elif page == "About":
    st.title("About this project")
    st.markdown("""
    **Project:** Smart Recycling & Waste-Segregation Assistant using AI.

    **Current image model:** MobileNetV2 trained on the nine RealWaste categories.

    **Workflow:** camera/gallery image → preprocessing → image classifier → suggested category
    → disposal/recycling guidance → prediction history and dashboard analytics.

    **Important limitations:** The classifier predicts one category for the whole image. It is
    not an object detector and may be unreliable for multiple objects, cluttered scenes, unusual
    camera conditions, or categories outside its training data.
    """)
    st.info(
        "The current assistant is a local knowledge-base fallback. The required Llama-family "
        "model and ExecuTorch on-device deployment are separate work and are not yet implemented."
    )
    st.markdown(
        "Mobile note: this Streamlit app can be opened in a phone browser when hosted on a "
        "reachable server or on the same Wi-Fi network. It is not an installable Android APK."
    )
