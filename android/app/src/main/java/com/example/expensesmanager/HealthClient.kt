package com.example.expensesmanager

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject

private const val REQUEST_TIMEOUT_MILLIS = 5000

class HealthClient(
    baseUrl: String = BuildConfig.API_BASE_URL,
) {
    private val endpoint = URL("${baseUrl.trimEnd('/')}/health")

    fun check() {
        val connection = endpoint.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = REQUEST_TIMEOUT_MILLIS
            connection.readTimeout = REQUEST_TIMEOUT_MILLIS
            connection.instanceFollowRedirects = false
            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                throw IOException("Health request failed")
            }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            if (JSONObject(body).optString("status") != "ok") {
                throw IOException("Unexpected health response")
            }
        } finally {
            connection.disconnect()
        }
    }
}
