package `in`.humanslop.pehchaan

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.media.AudioManager
import android.os.Build
import android.provider.CallLog
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat
import java.util.concurrent.CopyOnWriteArraySet

/**
 * Call context for the payment check (SPEC §2 trigger, §7 SDK): is the user on a call or just off one,
 * since when, from which number, PSTN or VoIP. Nothing about the call's content is read.
 *
 * Sources, best first:
 *  - TelephonyCallback / PhoneStateListener: call state (READ_PHONE_STATE).
 *  - ACTION_PHONE_STATE_CHANGED: the incoming number (needs READ_CALL_LOG; demo build only).
 *  - AudioManager mode: MODE_IN_COMMUNICATION = a VoIP call (WhatsApp etc.), no permission needed.
 *  - CallLog: the last answered call, for when the app wasn't running during the call (READ_CALL_LOG).
 * State is kept in SharedPreferences so it survives the process being killed.
 */
object CallMonitor {
    private const val PREFS = "pehchaan.call"
    /**
     * Calls that ended longer ago are reported as "none", with no number: three times the 10-minute trigger
     * window, so "paid 15 minutes later" still reaches the API, but older personal calls never leave the phone.
     */
    private const val STALE_MS = 30 * 60 * 1000L

    private val listeners = CopyOnWriteArraySet<(CallContext) -> Unit>()
    private var telephonyHooked = false
    private var receiverHooked = false
    private var audioHooked = false

    fun addListener(f: (CallContext) -> Unit) { listeners += f }
    fun removeListener(f: (CallContext) -> Unit) { listeners -= f }

    /** Idempotent; call again after permissions are granted to hook what was missing. */
    @Synchronized
    fun start(ctx: Context) {
        val c = ctx.applicationContext
        if (!telephonyHooked && has(c, Manifest.permission.READ_PHONE_STATE)) {
            val tm = c.getSystemService(TelephonyManager::class.java)
            if (Build.VERSION.SDK_INT >= 31) {
                tm.registerTelephonyCallback(c.mainExecutor, object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                    override fun onCallStateChanged(state: Int) = onTelephony(c, state, null)
                })
            } else {
                @Suppress("DEPRECATION")
                tm.listen(object : PhoneStateListener() {
                    @Deprecated("Deprecated in Java")
                    override fun onCallStateChanged(state: Int, phoneNumber: String?) = onTelephony(c, state, phoneNumber)
                }, PhoneStateListener.LISTEN_CALL_STATE)
            }
            telephonyHooked = true
        }
        if (!receiverHooked) {
            ContextCompat.registerReceiver(c, object : BroadcastReceiver() {
                override fun onReceive(context: Context, intent: Intent) {
                    val state = when (intent.getStringExtra(TelephonyManager.EXTRA_STATE)) {
                        TelephonyManager.EXTRA_STATE_RINGING -> TelephonyManager.CALL_STATE_RINGING
                        TelephonyManager.EXTRA_STATE_OFFHOOK -> TelephonyManager.CALL_STATE_OFFHOOK
                        TelephonyManager.EXTRA_STATE_IDLE -> TelephonyManager.CALL_STATE_IDLE
                        else -> return
                    }
                    @Suppress("DEPRECATION")
                    onTelephony(c, state, intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER))
                }
            }, IntentFilter(TelephonyManager.ACTION_PHONE_STATE_CHANGED), ContextCompat.RECEIVER_EXPORTED)
            receiverHooked = true
        }
        if (!audioHooked && Build.VERSION.SDK_INT >= 31) {
            c.getSystemService(AudioManager::class.java).addOnModeChangedListener(c.mainExecutor) { mode -> onAudioMode(c, mode) }
            audioHooked = true
        }
    }

    @Synchronized
    private fun onTelephony(c: Context, state: Int, rawNumber: String?) {
        val p = prefs(c)
        val prev = p.getString("state", "idle")
        val now = System.currentTimeMillis()
        val e = p.edit()
        val number = normalise(rawNumber)
        if (number != null) e.putString("number", number)
        when (state) {
            TelephonyManager.CALL_STATE_RINGING -> if (prev != "ringing" && prev != "active") {
                e.putString("state", "ringing").putString("direction", "in").putLong("ring_at", now)
                if (number == null) e.remove("number")
            }
            TelephonyManager.CALL_STATE_OFFHOOK -> if (prev != "active") {
                if (prev == "idle") e.putString("direction", "out").remove("number")  // dialled out; number unknown here
                e.putString("state", "active").putString("channel", "pstn").putLong("start", now).remove("end")
            }
            TelephonyManager.CALL_STATE_IDLE -> when (prev) {
                "active" -> e.putString("state", "idle").putLong("end", now)
                "ringing" -> e.putString("state", "idle").remove("start").remove("end")  // missed or rejected
            }
        }
        e.apply()
        emit(c)
    }

    @Synchronized
    private fun onAudioMode(c: Context, mode: Int) {
        val p = prefs(c)
        val prev = p.getString("state", "idle")
        val now = System.currentTimeMillis()
        if (mode == AudioManager.MODE_IN_COMMUNICATION && prev == "idle") {
            p.edit().putString("state", "active").putString("channel", "voip").putLong("start", now)
                .remove("end").remove("number").putString("direction", "unknown").apply()
        } else if (mode == AudioManager.MODE_NORMAL && prev == "active" && p.getString("channel", "pstn") == "voip") {
            p.edit().putString("state", "idle").putLong("end", now).apply()
        } else return
        emit(c)
    }

    private fun emit(c: Context) {
        if (listeners.isEmpty()) return
        val ctx = snapshot(c)
        listeners.forEach { runCatching { it(ctx) } }
    }

    /** The call context right now, corrected by live checks and the call log. */
    fun snapshot(ctx: Context): CallContext {
        val c = ctx.applicationContext
        val p = prefs(c)
        val now = System.currentTimeMillis()
        var state = p.getString("state", "idle")!!
        var channel = p.getString("channel", "pstn")!!
        var number = p.getString("number", null)
        var start = p.getLong("start", 0L).takeIf { it > 0 }
        var end = p.getLong("end", 0L).takeIf { it > 0 }
        var source = if (start != null) "live" else "none"

        // Live correction: the app may have started mid-call, or missed the hang-up while killed.
        val audioMode = c.getSystemService(AudioManager::class.java).mode
        val liveTel = if (has(c, Manifest.permission.READ_PHONE_STATE))
            runCatching { c.getSystemService(TelephonyManager::class.java).callStateCompat() }.getOrNull() else null
        val onPstn = liveTel == TelephonyManager.CALL_STATE_OFFHOOK || audioMode == AudioManager.MODE_IN_CALL
        val onVoip = audioMode == AudioManager.MODE_IN_COMMUNICATION
        if ((onPstn || onVoip) && state != "active") {
            // A call we didn't see start: the stored number belongs to an earlier call, unless this one rang first
            if (state != "ringing" || onVoip) number = null
            state = "active"; channel = if (onPstn) "pstn" else "voip"; start = null; end = null; source = "live"
        } else if (!onPstn && !onVoip && state == "active" && liveTel != null) {
            state = "idle"; if (end == null) end = now
        }

        // Call log: the last answered call, if it is newer than what we saw (or fills in its number).
        if (state != "active" && has(c, Manifest.permission.READ_CALL_LOG)) {
            lastLoggedCall(c)?.let { log ->
                val sameCall = end != null && kotlin.math.abs(log.end - end!!) < 15_000
                if (end == null || log.end > end!! + 15_000 || sameCall) {
                    if (!sameCall || number == null) number = log.number
                    if (!sameCall) { start = log.start; end = log.end; channel = "pstn"; source = "call_log" }
                    else if (start == null) start = log.start
                }
            }
        }

        val apiState = when {
            state == "active" -> "active"
            end != null && now - end!! < STALE_MS -> "ended"
            else -> "none"
        }
        val duration = when (apiState) {
            "active" -> start?.let { ((now - it) / 1000).toInt() }
            "ended" -> if (start != null) ((end!! - start!!) / 1000).toInt() else null
            else -> null
        }
        val match = if (apiState != "none" && number != null) ContactCheck.lookup(c, number) else null
        return CallContext(
            state = apiState,
            number = if (apiState == "none") null else number,
            channel = if (apiState == "none") "pstn" else channel,
            durationSec = duration,
            endedSecAgo = if (apiState == "ended") ((now - end!!) / 1000).toInt() else null,
            inContacts = match?.inContacts,
            source = if (apiState == "none") "none" else source,
            audioMode = audioMode,
            contactName = match?.name,
        )
    }

    private data class LoggedCall(val number: String?, val start: Long, val end: Long)

    private fun lastLoggedCall(c: Context): LoggedCall? = runCatching {
        c.contentResolver.query(
            CallLog.Calls.CONTENT_URI,
            arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.DATE, CallLog.Calls.DURATION, CallLog.Calls.TYPE),
            "${CallLog.Calls.DURATION} > 0", null, "${CallLog.Calls.DATE} DESC",
        )?.use { cur ->
            if (!cur.moveToFirst()) return@use null
            val start = cur.getLong(1)
            LoggedCall(normalise(cur.getString(0)), start, start + cur.getLong(2) * 1000)
        }
    }.getOrNull()

    @Suppress("DEPRECATION")
    private fun TelephonyManager.callStateCompat(): Int =
        if (Build.VERSION.SDK_INT >= 31) callStateForSubscription else callState

    /** E.164 for Indian numbers as the risk API expects (+91…); other formats are passed through. */
    fun normalise(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        val plus = raw.trim().startsWith("+")
        val d = raw.filter { it.isDigit() }
        if (d.isEmpty()) return null
        return when {
            plus -> "+$d"
            d.length == 10 -> "+91$d"
            d.length == 11 && d.startsWith("0") -> "+91${d.substring(1)}"
            d.length == 12 && d.startsWith("91") -> "+$d"
            d.startsWith("00") -> "+${d.substring(2)}"
            else -> d
        }
    }

    fun has(c: Context, perm: String) =
        ContextCompat.checkSelfPermission(c, perm) == PackageManager.PERMISSION_GRANTED

    private fun prefs(c: Context) = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
