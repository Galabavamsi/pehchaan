package `in`.humanslop.pehchaan

import android.os.Handler
import android.os.Looper
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Holds `/ws/device/{device_id}` open for the relative's phone (SPEC §7). No FCM: one WebSocket, pinged every
 * 20 s so mobile NATs keep it, reconnecting with backoff. The server's hello carries challenges missed while
 * offline, so nothing is polled.
 */
class FamilyVerifyListener(
    private val wsUrl: String,
    private val onRequest: (JSONObject) -> Unit,
    private val onClear: (String) -> Unit,
    private val onLink: (Boolean) -> Unit = {},
) {
    private val client = OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS).build()
    private val main = Handler(Looper.getMainLooper())
    private var ws: WebSocket? = null
    private var stopped = false
    private var attempt = 0

    fun start() { stopped = false; connect() }

    fun stop() {
        stopped = true
        main.removeCallbacksAndMessages(null)
        ws?.close(1000, "stop")
        ws = null
    }

    private fun connect() {
        if (stopped) return
        ws = client.newWebSocket(Request.Builder().url(wsUrl).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) { attempt = 0; onLink(true) }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val m = runCatching { JSONObject(text) }.getOrNull() ?: return
                when (m.optString("type")) {
                    "hello" -> m.optJSONArray("pending")?.optJSONObject(0)?.let { main.post { onRequest(it) } }
                    "fv_request" -> m.optJSONObject("data")?.let { main.post { onRequest(it) } }
                    "fv_expired", "fv_done", "reset" -> main.post { onClear(m.optString("type")) }
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = retry()
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) = retry()
        })
    }

    private fun retry() {
        onLink(false)
        if (stopped) return
        val delay = minOf(30_000L, 1_000L shl minOf(attempt++, 5))
        main.postDelayed({ connect() }, delay)
    }
}
