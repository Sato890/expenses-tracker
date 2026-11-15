package com.example.expensesmanager

import com.sun.net.httpserver.HttpServer
import java.io.IOException
import java.net.InetSocketAddress
import org.json.JSONException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class HealthClientTest {
    @Test
    fun healthRequiresSuccessfulHttpStatusAndOkJson() {
        val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        var status = 200
        var body = "{ \"status\": \"ok\" }"
        server.createContext("/api/health") { exchange ->
            assertEquals("GET", exchange.requestMethod)
            val bytes = body.toByteArray()
            exchange.sendResponseHeaders(status, bytes.size.toLong())
            exchange.responseBody.use { it.write(bytes) }
        }
        server.start()
        try {
            val client = HealthClient("http://127.0.0.1:${server.address.port}/api")
            client.checkHealth()
            HealthClient("http://127.0.0.1:${server.address.port}/api/").checkHealth()
            body = "{\"status\":\"unhealthy\"}"
            assertThrows(IOException::class.java) { client.checkHealth() }
            body = "not JSON"
            assertThrows(JSONException::class.java) { client.checkHealth() }
            status = 503
            body = "{\"status\":\"ok\"}"
            assertThrows(IOException::class.java) { client.checkHealth() }
        } finally {
            server.stop(0)
        }
    }
}
