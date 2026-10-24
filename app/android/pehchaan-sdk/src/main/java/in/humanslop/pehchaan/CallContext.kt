package `in`.humanslop.pehchaan

import org.json.JSONObject

/**
 * The `call` object of `POST /v1/risk/assess` (SPEC §7). [source] and [audioMode] are for the app's own
 * display and never sent.
 */
data class CallContext(
    val state: String,            // "active" | "ended" | "none"
    val number: String?,          // E.164; null when unknown (Play-compliant mode, VoIP, outgoing)
    val channel: String,          // "pstn" | "voip"
    val durationSec: Int?,
    val endedSecAgo: Int?,
    val inContacts: Boolean?,     // matched on this phone; null = not checked
    val source: String,           // "live" | "call_log" | "none"
    val audioMode: Int,
) {
    /** Exactly what leaves the phone. */
    fun toApiJson(): JSONObject = JSONObject().apply {
        put("state", state)
        put("number", number ?: JSONObject.NULL)
        put("channel", channel)
        put("duration_sec", durationSec ?: JSONObject.NULL)
        put("ended_sec_ago", endedSecAgo ?: JSONObject.NULL)
        if (inContacts != null) put("in_contacts", inContacts)
    }
}
