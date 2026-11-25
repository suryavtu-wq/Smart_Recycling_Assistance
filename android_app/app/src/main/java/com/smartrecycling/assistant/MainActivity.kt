package com.smartrecycling.assistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebChromeClient.FileChooserParams
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var addressInput: EditText
    private lateinit var browser: WebView
    private lateinit var statusText: TextView
    private lateinit var progressBar: ProgressBar
    private var trustedHost: String? = null
    private var fileChooserCallback: ValueCallback<Array<Uri>>? = null
    private var cameraRequest: PermissionRequest? = null

    private val imagePicker =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            fileChooserCallback?.onReceiveValue(uri?.let { arrayOf(it) })
            fileChooserCallback = null
        }

    private val cameraPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            val request = cameraRequest
            cameraRequest = null
            if (granted && request != null && isTrustedOrigin(request.origin)) {
                val cameraResources = request.resources.filter {
                    it == PermissionRequest.RESOURCE_VIDEO_CAPTURE
                }.toTypedArray()
                if (cameraResources.isNotEmpty()) {
                    request.grant(cameraResources)
                } else {
                    request.deny()
                }
            } else {
                request?.deny()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(242, 247, 241)
        window.navigationBarColor = Color.rgb(242, 247, 241)
        window.decorView.systemUiVisibility =
            View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(18), dp(16), dp(8))
            setBackgroundColor(Color.rgb(242, 247, 241))
        }
        root.addView(
            TextView(this).apply {
                text = "Smart Recycling"
                textSize = 24f
                setTextColor(Color.rgb(24, 71, 51))
                setPadding(0, 0, 0, dp(8))
            }
        )
        root.addView(
            TextView(this).apply {
                text = "Paste your deployed Streamlit app URL to get started."
                textSize = 14f
                setTextColor(Color.DKGRAY)
            }
        )

        addressInput = EditText(this).apply {
            hint = "https://your-app.streamlit.app"
            setSingleLine(true)
            inputType = android.text.InputType.TYPE_CLASS_TEXT or
                android.text.InputType.TYPE_TEXT_VARIATION_URI
            setText(getSharedPreferences("mobile_settings", MODE_PRIVATE).getString("site_url", ""))
            setPadding(dp(12), dp(4), dp(12), dp(4))
            background = rounded(Color.WHITE, 12)
        }
        root.addView(
            addressInput,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)).apply {
                topMargin = dp(12)
            },
        )

        root.addView(
            Button(this).apply {
                text = "Open recycling app"
                isAllCaps = false
                setOnClickListener { openWebsite() }
            },
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50)).apply {
                topMargin = dp(8)
            },
        )

        progressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            visibility = View.GONE
        }
        root.addView(progressBar, ViewGroup.LayoutParams.MATCH_PARENT, dp(3))

        statusText = TextView(this).apply {
            text = "The website requires an internet connection."
            textSize = 13f
            setTextColor(Color.DKGRAY)
            setPadding(0, dp(6), 0, dp(6))
        }
        root.addView(statusText)

        browser = WebView(this).apply {
            setBackgroundColor(Color.WHITE)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.mediaPlaybackRequiresUserGesture = false
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            settings.allowFileAccess = false
            settings.allowContentAccess = true
            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
            webViewClient = createWebViewClient()
            webChromeClient = createWebChromeClient()
        }
        root.addView(
            browser,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f,
            ),
        )
        setContentView(root)

        val savedUrl = addressInput.text.toString().trim()
        if (savedUrl.isNotEmpty()) {
            openWebsite()
        }
    }

    private fun openWebsite() {
        val uri = Uri.parse(addressInput.text.toString().trim())
        val host = uri.host
        if (uri.scheme != "https" || host.isNullOrBlank() || uri.userInfo != null) {
            statusText.text = "Enter your app's full HTTPS URL, such as https://your-app.streamlit.app"
            return
        }

        trustedHost = host
        getSharedPreferences("mobile_settings", MODE_PRIVATE)
            .edit()
            .putString("site_url", uri.toString())
            .apply()
        statusText.text = "Loading recycling app..."
        browser.loadUrl(uri.toString())
    }

    private fun createWebChromeClient() = object : WebChromeClient() {
        override fun onProgressChanged(view: WebView?, newProgress: Int) {
            progressBar.progress = newProgress
            progressBar.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
        }

        override fun onShowFileChooser(
            webView: WebView?,
            callback: ValueCallback<Array<Uri>>?,
            params: FileChooserParams?,
        ): Boolean {
            fileChooserCallback?.onReceiveValue(null)
            if (callback == null || trustedHost == null) return false
            fileChooserCallback = callback
            imagePicker.launch("image/*")
            return true
        }

        override fun onPermissionRequest(request: PermissionRequest) {
            runOnUiThread {
                if (!isTrustedOrigin(request.origin) ||
                    !request.resources.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE)
                ) {
                    request.deny()
                    return@runOnUiThread
                }

                if (checkSelfPermission(Manifest.permission.CAMERA) ==
                    PackageManager.PERMISSION_GRANTED
                ) {
                    request.grant(arrayOf(PermissionRequest.RESOURCE_VIDEO_CAPTURE))
                } else {
                    cameraRequest?.deny()
                    cameraRequest = request
                    cameraPermission.launch(Manifest.permission.CAMERA)
                }
            }
        }

        override fun onPermissionRequestCanceled(request: PermissionRequest) {
            if (cameraRequest == request) cameraRequest = null
        }
    }

    private fun createWebViewClient() = object : WebViewClient() {
        override fun shouldOverrideUrlLoading(
            view: WebView?,
            request: WebResourceRequest?,
        ): Boolean {
            val uri = request?.url ?: return false
            if (uri.scheme == "https" && uri.host == trustedHost) return false
            if (uri.scheme == "https") {
                startActivity(Intent(Intent.ACTION_VIEW, uri))
            }
            return true
        }

        override fun onPageFinished(view: WebView?, url: String?) {
            statusText.text = "Ready. Choose camera capture or gallery upload on the page."
        }
    }

    private fun isTrustedOrigin(origin: Uri) =
        origin.scheme == "https" && origin.host == trustedHost

    private fun rounded(color: Int, radius: Int) =
        android.graphics.drawable.GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(radius).toFloat()
        }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    override fun onBackPressed() {
        if (::browser.isInitialized && browser.canGoBack()) {
            browser.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onDestroy() {
        fileChooserCallback?.onReceiveValue(null)
        cameraRequest?.deny()
        if (::browser.isInitialized) {
            browser.stopLoading()
            browser.destroy()
        }
        super.onDestroy()
    }
}
