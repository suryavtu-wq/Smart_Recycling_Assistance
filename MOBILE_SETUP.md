# Use the Android app

This project now includes a native Android client in `android_app/`. The Python
classifier runs on a server; the Android client sends the selected or captured
image to that API and displays the prediction and disposal guidance. The model
is not packaged to run offline on Android.

## Deploy the prediction API to Render

The repository includes `render.yaml` and `requirements-api.txt` for deployment.

1. Sign in to Render using the GitHub account that owns the repository.
2. Choose **New > Blueprint** and select `YAGATI-SURYA-29/Smart-Recycling-Assistant`
   on the `main` branch.
3. Review the service settings and the current plan's cost, RAM, and availability
   before applying. PyTorch needs more memory than a small static website; a
   plan with too little memory can fail during startup or prediction.
4. Wait for the service to become **Live** and copy its HTTPS URL, for example
   `https://smart-recycling-api.onrender.com`.
5. Open `https://YOUR-SERVICE-URL/health`. Confirm the response includes
   `"status":"ok"` and `"model_available":true`.
6. In the Android app, enter the HTTPS service URL as **API server address**.
   The app remembers the address. It can then send images from any network with
   internet access.

Render deploys the Python API and model; it does not build the Android APK.
Check the selected plan's pricing and sleep/cold-start behavior before creating
the service. The prediction endpoint is public and does not require sign-in, so
do not upload private images or share the service URL widely.

## Test locally (optional)

From the project root in PowerShell:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn mobile_api:app --host 0.0.0.0 --port 8000
```

Check `http://127.0.0.1:8000/health` on the computer. For local phone testing,
connect both devices to the same trusted Wi-Fi and set the app address to
`http://YOUR-COMPUTER-IP:8000`. Allow Python through Windows Firewall on the
private network if prompted. This local HTTP setup is for testing only; use the
Render HTTPS URL for internet access.

## Build and install the Android app

1. Install Android Studio with Android SDK Platform 35.
2. Open the `android_app` folder in Android Studio and allow Gradle sync.
3. Connect an Android phone with USB debugging enabled, or start an emulator.
4. Select the `app` run configuration and press **Run**.

For local emulator testing, the default address `http://10.0.2.2:8000` works
when the API runs on the same computer. For the hosted app, use the Render
HTTPS URL instead.

To create a debug APK in Android Studio, use **Build > Build App Bundle(s) /
APK(s) > Build APK(s)**. The generated APK can be found under
`android_app/app/build/outputs/apk/debug/`.

## Limitations

- Image classification runs on the API host, so internet access and an
  available hosting service are required.
- Camera capture and gallery selection use Android's system interfaces.
- The model predicts one category for the whole image; it is not an object
  detector. Confirm the material and follow local disposal rules.
- This creates a debug APK workflow, not a Play Store-ready signed release.
