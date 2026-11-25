package com.smartrecycling.assistant

import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var endpointInput: EditText
    private lateinit var imagePreview: ImageView
    private lateinit var statusText: TextView
    private lateinit var resultBox: LinearLayout
    private lateinit var progress: ProgressBar
    private lateinit var identifyButton: Button
    private var selectedImage: Uri? = null
    private var cameraImage: Uri? = null

    private val galleryPicker =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            uri?.let(::showSelectedImage)
        }

    private val cameraCapture =
        registerForActivityResult(ActivityResultContracts.TakePicture()) { saved ->
            if (saved) cameraImage?.let(::showSelectedImage)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(242, 247, 241)
        window.navigationBarColor = Color.rgb(242, 247, 241)
        window.decorView.systemUiVisibility =
            android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
                android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR

        val preferences = getSharedPreferences("mobile_settings", MODE_PRIVATE)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(28), dp(20), dp(28))
        }
        content.setBackgroundColor(Color.rgb(242, 247, 241))

        content.addView(label("♻  Smart Recycling", 28, Color.rgb(24, 71, 51), true))
        content.addView(label("Identify an item and get practical sorting guidance.", 15, Color.DKGRAY))
        content.addView(label("API server address", 14, Color.rgb(65, 75, 68), true, top = 22))
        endpointInput = EditText(this).apply {
            setSingleLine(true)
            hint = "http://192.168.1.20:8000"
            setText(preferences.getString("api_url", "http://10.0.2.2:8000"))
            inputType = android.text.InputType.TYPE_CLASS_TEXT or
                android.text.InputType.TYPE_TEXT_VARIATION_URI
            setPadding(dp(14), dp(4), dp(14), dp(4))
            background = rounded(Color.WHITE, 12)
        }
        content.addView(endpointInput, matchWidth(height = 54))
        content.addView(
            label(
                "Use your computer's Wi-Fi IP on a real phone; 10.0.2.2 is for the Android emulator.",
                12,
                Color.GRAY,
                top = 6,
            )
        )

        val imageActions = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        imageActions.addView(
            button("Take photo") {
                val file = File(cacheDir, "images/${System.currentTimeMillis()}.jpg")
                file.parentFile?.mkdirs()
                cameraImage = FileProvider.getUriForFile(
                    this,
                    "$packageName.fileprovider",
                    file,
                )
                cameraCapture.launch(cameraImage)
            },
            LinearLayout.LayoutParams(0, dp(52), 1f).apply { marginEnd = dp(6) },
        )
        imageActions.addView(
            button("Choose image") { galleryPicker.launch("image/*") },
            LinearLayout.LayoutParams(0, dp(52), 1f).apply { marginStart = dp(6) },
        )
        content.addView(imageActions, matchWidth(top = 20))

        imagePreview = ImageView(this).apply {
            scaleType = ImageView.ScaleType.CENTER_CROP
            background = rounded(Color.rgb(225, 233, 225), 16)
            contentDescription = "Selected waste image"
        }
        content.addView(imagePreview, matchWidth(height = 240, top = 16))

        identifyButton = button("Identify this item") { submitImage() }
        identifyButton.isEnabled = false
        content.addView(identifyButton, matchWidth(height = 54, top = 14))
        progress = ProgressBar(this).apply { visibility = android.view.View.GONE }
        content.addView(progress, centered(top = 12))
        statusText = label("Take a photo or choose one from your gallery.", 14, Color.DKGRAY, top = 12)
        content.addView(statusText)

        resultBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            background = rounded(Color.WHITE, 16)
            visibility = android.view.View.GONE
        }
        content.addView(resultBox, matchWidth(top = 16))

        val scrollView = ScrollView(this).apply { addView(content) }
        setContentView(scrollView)
    }

    private fun showSelectedImage(uri: Uri) {
        selectedImage = uri
        imagePreview.setImageURI(uri)
        identifyButton.isEnabled = true
        resultBox.visibility = android.view.View.GONE
        statusText.text = "Image ready. Tap Identify this item."
    }

    private fun submitImage() {
        val image = selectedImage ?: return
        val baseUrl = endpointInput.text.toString().trim().trimEnd('/')
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            statusText.text = "Enter a server address starting with http:// or https://."
            return
        }
        getSharedPreferences("mobile_settings", MODE_PRIVATE)
            .edit()
            .putString("api_url", baseUrl)
            .apply()

        identifyButton.isEnabled = false
        progress.visibility = android.view.View.VISIBLE
        statusText.text = "Analyzing image…"
        resultBox.visibility = android.view.View.GONE

        executor.execute {
            try {
                val response = requestPrediction(baseUrl, image)
                runOnUiThread { showResult(response) }
            } catch (error: IOException) {
                runOnUiThread {
                    statusText.text = error.message ?: "Could not reach the API server."
                }
            } catch (error: org.json.JSONException) {
                runOnUiThread { statusText.text = "The API returned an invalid response." }
            } finally {
                runOnUiThread {
                    progress.visibility = android.view.View.GONE
                    identifyButton.isEnabled = selectedImage != null
                }
            }
        }
    }

    private fun requestPrediction(baseUrl: String, image: Uri): JSONObject {
        val boundary = "----SmartRecycling${System.currentTimeMillis()}"
        val connection = (URL("$baseUrl/predict").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 15_000
            readTimeout = 120_000
            doOutput = true
            setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        }
        try {
            connection.outputStream.use { output ->
                output.write(
                    "--$boundary\r\n".toByteArray(StandardCharsets.UTF_8)
                )
                output.write(
                    "Content-Disposition: form-data; name=\"file\"; filename=\"waste-image.jpg\"\r\n".toByteArray(
                        StandardCharsets.UTF_8
                    )
                )
                output.write("Content-Type: application/octet-stream\r\n\r\n".toByteArray(StandardCharsets.UTF_8))
                val input = contentResolver.openInputStream(image)
                    ?: throw IOException("Could not read the selected image.")
                input.use { it.copyTo(output) }
                output.write("\r\n--$boundary--\r\n".toByteArray(StandardCharsets.UTF_8))
            }
            val statusCode = connection.responseCode
            val stream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
                ?: throw IOException("API request failed with HTTP $statusCode.")
            val body = stream.bufferedReader(StandardCharsets.UTF_8).use { it.readText() }
            val json = JSONObject(body)
            if (statusCode !in 200..299) {
                throw IOException(json.optString("detail", "API request failed with HTTP $statusCode."))
            }
            return json
        } finally {
            connection.disconnect()
        }
    }

    private fun showResult(response: JSONObject) {
        resultBox.removeAllViews()
        val confidence = response.getDouble("confidence")
        resultBox.addView(label(response.getString("category"), 23, Color.rgb(24, 71, 51), true))
        resultBox.addView(
            label(
                "Model score: ${String.format(Locale.getDefault(), "%.1f%%", confidence * 100)}",
                14,
                Color.DKGRAY,
                top = 4,
            )
        )
        if (response.getBoolean("low_confidence")) {
            resultBox.addView(
                label(
                    "Low-confidence result. Try a clear photo of one item in good lighting.",
                    14,
                    Color.rgb(150, 87, 0),
                    top = 10,
                )
            )
        } else {
            resultBox.addView(
                label(
                    "A model score is not a guarantee. Verify the material and local collection rules.",
                    13,
                    Color.DKGRAY,
                    top = 10,
                )
            )
        }

        resultBox.addView(label("Other suggestions", 16, Color.BLACK, true, top = 18))
        val suggestions = response.getJSONArray("top_suggestions")
        for (index in 0 until suggestions.length()) {
            val item = suggestions.getJSONObject(index)
            resultBox.addView(
                label(
                    "${item.getString("category")} — ${String.format(Locale.getDefault(), "%.1f%%", item.getDouble("confidence") * 100)}",
                    14,
                    Color.DKGRAY,
                    top = 4,
                )
            )
        }

        val guidance = response.getJSONObject("guidance")
        resultBox.addView(label("Disposal", 16, Color.BLACK, true, top = 18))
        resultBox.addView(label(guidance.getString("disposal"), 14, Color.DKGRAY, top = 4))
        resultBox.addView(label("Recycling", 16, Color.BLACK, true, top = 14))
        resultBox.addView(label(guidance.getString("recycling"), 14, Color.DKGRAY, top = 4))
        statusText.text = "Identification complete. Follow your local waste authority's guidance."
        resultBox.visibility = android.view.View.VISIBLE
    }

    private fun label(
        text: String,
        size: Int,
        color: Int,
        bold: Boolean = false,
        top: Int = 0,
    ) = TextView(this).apply {
        this.text = text
        textSize = size.toFloat()
        setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
        setPadding(0, dp(top), 0, dp(2))
    }

    private fun button(text: String, action: () -> Unit) = Button(this).apply {
        this.text = text
        isAllCaps = false
        setTextColor(Color.WHITE)
        background = rounded(Color.rgb(36, 112, 75), 14)
        setOnClickListener { action() }
    }

    private fun rounded(color: Int, radius: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radius).toFloat()
    }

    private fun matchWidth(height: Int = ViewGroup.LayoutParams.WRAP_CONTENT, top: Int = 0) =
        LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(height)).apply {
            topMargin = dp(top)
        }

    private fun centered(top: Int = 0) =
        LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            gravity = Gravity.CENTER_HORIZONTAL
            topMargin = dp(top)
        }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    override fun onDestroy() {
        executor.shutdown()
        super.onDestroy()
    }
}
