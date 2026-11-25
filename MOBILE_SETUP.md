# Mobile website and Android APK

The easiest way to use this project on a phone without a paid prediction API is
to host the existing Streamlit app on Streamlit Community Cloud. The app already
supports camera capture and gallery upload. The Android project is a WebView
wrapper around that hosted website; predictions still require internet access.

## Deploy the website

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) with the GitHub
   account that owns this repository.
2. Choose **Create app** (or **New app**) and select
   `YAGATI-SURYA-29/Smart-Recycling-Assistant`.
3. Select branch `main` and main file path `app.py`.
4. Deploy the app and wait for the install/build process to finish. The first
   deployment can take several minutes while PyTorch installs.
5. Open the Streamlit URL it gives you, then test camera capture and image
   upload in a phone browser.

Community Cloud is a free hosting option, but apps are subject to its resource
limits and availability. Keep the GitHub repository private or public according
to your preference; Community Cloud supports both. Images selected in the app
are uploaded to the hosted service for prediction.

## Build and use the Android APK

1. Install Android Studio with Android SDK Platform 35.
2. Open the `android_app` folder in Android Studio and allow Gradle sync.
3. Connect an Android phone with USB debugging enabled, or start an emulator.
4. Select the `app` run configuration and press **Run**.
5. In the app, paste the HTTPS Streamlit URL from the deployment and tap
   **Open recycling app**.
6. Allow camera permission when Android asks. The website's gallery picker
   opens through the Android app.

To create a debug APK in Android Studio, use **Build > Build App Bundle(s) /
APK(s) > Build APK(s)**. The generated APK can be found under
`android_app/app/build/outputs/apk/debug/`.

The APK is a website wrapper, not an offline/native model app. It requires
internet access and loads the Streamlit site. The app only accepts HTTPS URLs;
camera access is granted to the configured site origin.
