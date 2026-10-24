package `in`.humanslop.pehchaan

import android.annotation.SuppressLint
import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.util.function.Consumer

/** Public entry point of the SDK. A host app calls [startProtection] once and [callContext] at the Pay tap. */
object Pehchaan {
    const val EXTRA_ROUTE = "pehchaan_route"
    internal const val CH_FV = "pehchaan_family_verify"
    internal const val CH_SVC = "pehchaan_protection"
    internal const val NOTIF_SVC = 1
    internal const val NOTIF_FV = 2
    private const val PREFS = "pehchaan.config"

    /** Set by the host while its UI is on screen; the WebView then shows requests itself. */
    @Volatile var appVisible = false
    /** Android 15+: true while this app's window is being recorded or shared. null = can't tell (older OS). */
    @Volatile var screenRecording: Boolean? = null
        internal set

    data class Config(val role: String, val deviceId: String?, val apiBase: String)

    fun callContext(ctx: Context): CallContext = CallMonitor.snapshot(ctx)

    /** role: "payer" (watch calls) or "relative" (receive Family Verify for [deviceId]). */
    fun startProtection(ctx: Context, role: String, deviceId: String?, apiBase: String) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString("role", role).putString("device_id", deviceId).putString("api", apiBase.trimEnd('/')).apply()
        CallMonitor.start(ctx)
        ContextCompat.startForegroundService(ctx, Intent(ctx, PehchaanService::class.java))
    }

    fun stopProtection(ctx: Context) {
        ctx.stopService(Intent(ctx, PehchaanService::class.java))
    }

    internal fun config(ctx: Context): Config? {
        val p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val role = p.getString("role", null) ?: return null
        return Config(role, p.getString("device_id", null), p.getString("api", "https://api.humanslop.in")!!)
    }

    fun canUseFullScreen(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < 34 || ctx.getSystemService(NotificationManager::class.java).canUseFullScreenIntent()

    fun ignoringBatteryOptimisations(ctx: Context): Boolean =
        ctx.getSystemService(PowerManager::class.java).isIgnoringBatteryOptimizations(ctx.packageName)

    /** Settings screens the user needs for reliable background delivery (MIUI and One UI kill services). */
    @SuppressLint("BatteryLife")
    fun settingsIntent(ctx: Context, which: String): Intent = when (which) {
        "battery" -> Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:${ctx.packageName}"))
        "fullscreen" -> if (Build.VERSION.SDK_INT >= 34)
            Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:${ctx.packageName}"))
        else appDetails(ctx)
        "notifications" -> Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, ctx.packageName)
        else -> appDetails(ctx)
    }.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    private fun appDetails(ctx: Context) =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${ctx.packageName}"))

    internal fun ensureChannels(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CH_FV, "Family Verify requests", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "A relative is about to pay because someone said they are you"
            enableVibration(true)
            lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
        })
        nm.createNotificationChannel(NotificationChannel(CH_SVC, "Protection status", NotificationManager.IMPORTANCE_LOW))
    }

    internal fun openAppIntent(ctx: Context, route: String, code: Int): PendingIntent {
        val i = (ctx.packageManager.getLaunchIntentForPackage(ctx.packageName) ?: Intent())
            .putExtra(EXTRA_ROUTE, route)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        return PendingIntent.getActivity(ctx, code, i, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    /** The relative's alert: heads-up, and full screen over the lock screen when allowed. */
    internal fun showFamilyVerify(ctx: Context, data: JSONObject) {
        if (appVisible) return
        ensureChannels(ctx)
        val msg = data.optJSONObject("message")
        val body = msg?.optString("en")?.takeIf { it.isNotBlank() }
            ?: "Someone said they are you and asked for money. Is this you?"
        val pi = openAppIntent(ctx, "relative", 2)
        val n = NotificationCompat.Builder(ctx, CH_FV)
            .setSmallIcon(R.drawable.ic_pehchaan)
            .setContentTitle("Family Verify: is this you?")
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setAutoCancel(true)
            .setContentIntent(pi)
            .apply { if (canUseFullScreen(ctx)) setFullScreenIntent(pi, true) }
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify(NOTIF_FV, n)
    }

    internal fun clearFamilyVerify(ctx: Context) =
        ctx.getSystemService(NotificationManager::class.java).cancel(NOTIF_FV)

    // ---------------------------------------------------------------- screen sharing (Android 15+)
    private val recordingCallback = Consumer<Int> { state ->
        screenRecording = state == WindowManager.SCREEN_RECORDING_STATE_VISIBLE
        onScreenRecording?.invoke(screenRecording == true)
    }
    var onScreenRecording: ((Boolean) -> Unit)? = null

    fun watchScreenRecording(activity: Activity) {
        if (Build.VERSION.SDK_INT < 35) return
        val initial = activity.windowManager.addScreenRecordingCallback(activity.mainExecutor, recordingCallback)
        recordingCallback.accept(initial)
    }

    fun unwatchScreenRecording(activity: Activity) {
        if (Build.VERSION.SDK_INT < 35) return
        activity.windowManager.removeScreenRecordingCallback(recordingCallback)
    }
}
