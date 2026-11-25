# Use the Android app

This project now includes a native Android client in `android_app/`. The Python
classifier still runs on your computer (or another server); the Android client
sends the selected or captured image to that API and displays the prediction
and disposal guidance. The model is not yet packaged to run offline on Android.

## Run the API on your computer

From the project root in PowerShell, install dependencies if needed and start
the API:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn mobile_api:app --host 0.0.0.0 --port 8000
```

Confirm it is available by opening `http://127.0.0.1:8000/health` on the
computer. The response reports whether the trained model file was found.

For a physical phone:

1. Connect the phone and computer to the same trusted Wi-Fi network.
2. Find the computer's Wi-Fi IPv4 address with `ipconfig`.
3. If prompted, allow Python on the **private** network in Windows Firewall.
4. In the Android app, set **API server address** to
   `http://YOUR-COMPUTER-IP:8000` (for example `http://192.168.1.20:8000`).
5. Capture a photo or choose one from the gallery, then tap **Identify this item**.

Do not expose this development API to the public internet. The local HTTP setup
is for trusted Wi-Fi testing; a public deployment should use HTTPS and suitable
access controls.

## Build and install the Android app

1. Install Android Studio with Android SDK Platform 35.
2. Open the `android_app` folder in Android Studio and allow Gradle sync.
3. Connect an Android phone with USB debugging enabled, or start an emulator.
4. Select the `app` run configuration and press **Run**.

The default server address `http://10.0.2.2:8000` works for an Android emulator
when the API is running on the same computer. On a real phone, enter the
computer's Wi-Fi IPv4 address instead.

To create a debug APK in Android Studio, use **Build > Build App Bundle(s) /
APK(s) > Build APK(s)**. The generated APK can be found under
`android_app/app/build/outputs/apk/debug/`.

## Limitations

- Image classification runs on the Python host, so the host must remain on and
  reachable while the app is in use.
- Camera capture and gallery selection use Android's system interfaces.
- The model predicts one category for the whole image; it is not an object
  detector. Confirm the material and follow local disposal rules.
- This creates a debug APK workflow, not a Play Store-ready signed release.
