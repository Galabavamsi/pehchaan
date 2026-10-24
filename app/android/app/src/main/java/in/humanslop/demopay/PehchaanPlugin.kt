package `in`.humanslop.demopay

import `in`.humanslop.pehchaan.CallContext
import `in`.humanslop.pehchaan.CallMonitor
import `in`.humanslop.pehchaan.Pehchaan
import android.Manifest
import android.content.Intent
import android.os.Build
import android.view.WindowManager
import com.getcapacitor.JSObject
import com.getcapacitor.PermissionState
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PermissionCallback
import org.json.JSONObject

/** Bridge from the DemoPay web screens to the native Pehchaan SDK. */
@CapacitorPlugin(
    name = "Pehchaan",
    permissions = [
        Permission(alias = "phone", strings = [Manifest.permission.READ_PHONE_STATE, Manifest.permission.READ_CALL_LOG]),
        Permission(alias = "contacts", strings = [Manifest.permission.READ_CONTACTS]),
        Permission(alias = "notifications", strings = [Manifest.permission.POST_NOTIFICATIONS]),
    ],
)
class PehchaanPlugin : Plugin() {
    private var launchRoute: String? = null
    private val onCall: (CallContext) -> Unit = { notifyListeners("callChanged", toJs(it)) }

    override fun load() {
        CallMonitor.start(context)
        CallMonitor.addListener(onCall)
        Pehchaan.onScreenRecording = { rec -> notifyListeners("screenRecording", JSObject().put("recording", rec)) }
        takeRoute(activity.intent)
    }

    override fun handleOnDestroy() { CallMonitor.removeListener(onCall) }

    override fun handleOnResume() {
        Pehchaan.appVisible = true
        CallMonitor.start(context)  // hooks anything newly permitted
        Pehchaan.watchScreenRecording(activity)
    }

    override fun handleOnPause() {
        Pehchaan.appVisible = false
        Pehchaan.unwatchScreenRecording(activity)
        // Only a Family Verify alert may show over the lock screen, and only while it is up
        if (Build.VERSION.SDK_INT >= 27) { activity.setShowWhenLocked(false); activity.setTurnScreenOn(false) }
    }

    override fun handleOnNewIntent(intent: Intent) {
        super.handleOnNewIntent(intent)
        takeRoute(intent)?.let { notifyListeners("route", JSObject().put("route", it)) }
    }

    /** Opened from a Family Verify alert: show over the lock screen and turn the screen on. */
    private fun takeRoute(intent: Intent?): String? {
        // A upi://pay link or QR opened with DemoPay: hand the whole URI to the web layer once
        if (intent?.action == Intent.ACTION_VIEW && intent.data?.scheme == "upi") {
            val uri = intent.dataString
            intent.data = null
            launchRoute = "upi:$uri"
            return launchRoute
        }
        val route = intent?.getStringExtra(Pehchaan.EXTRA_ROUTE) ?: return null
        intent.removeExtra(Pehchaan.EXTRA_ROUTE)
        launchRoute = route
        if (route == "relative" && Build.VERSION.SDK_INT >= 27) {
            activity.runOnUiThread { activity.setShowWhenLocked(true); activity.setTurnScreenOn(true) }
        }
        return route
    }

    @PluginMethod
    fun getLaunchRoute(call: PluginCall) {
        call.resolve(JSObject().put("route", launchRoute ?: JSONObject.NULL))
        launchRoute = null
    }

    @PluginMethod
    fun getCallContext(call: PluginCall) = call.resolve(toJs(Pehchaan.callContext(context)))

    @PluginMethod
    fun status(call: PluginCall) = call.resolve(statusJs())

    /** Ask only for what the role uses: the relative's phone never needs call log or contacts. */
    @PluginMethod
    fun requestForRole(call: PluginCall) {
        val aliases = if (call.getString("role") == "relative") arrayOf("notifications")
        else arrayOf("phone", "contacts", "notifications")
        requestPermissionForAliases(aliases, call, "permissionsDone")
    }

    @PermissionCallback
    private fun permissionsDone(call: PluginCall) {
        CallMonitor.start(context)
        call.resolve(statusJs())
    }

    @PluginMethod
    fun startProtection(call: PluginCall) {
        val role = call.getString("role") ?: return call.reject("role is required")
        val api = call.getString("api") ?: return call.reject("api is required")
        Pehchaan.startProtection(context, role, call.getString("deviceId"), api)
        call.resolve()
    }

    @PluginMethod
    fun stopProtection(call: PluginCall) { Pehchaan.stopProtection(context); call.resolve() }

    /** FLAG_SECURE: a screen-share or screenshot of this screen comes out black. */
    @PluginMethod
    fun setSecure(call: PluginCall) {
        val on = call.getBoolean("on", true) == true
        activity.runOnUiThread {
            if (on) activity.window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
            else activity.window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
            call.resolve()
        }
    }

    @PluginMethod
    fun openSettings(call: PluginCall) {
        runCatching { context.startActivity(Pehchaan.settingsIntent(context, call.getString("which") ?: "app")) }
            .onSuccess { call.resolve() }.onFailure { call.reject(it.message) }
    }

    private fun statusJs() = JSObject().apply {
        put("phone", getPermissionState("phone") == PermissionState.GRANTED)
        put("contacts", getPermissionState("contacts") == PermissionState.GRANTED)
        put("notifications", getPermissionState("notifications") == PermissionState.GRANTED)
        put("call_log", CallMonitor.has(context, Manifest.permission.READ_CALL_LOG))
        put("full_screen", Pehchaan.canUseFullScreen(context))
        put("battery_unrestricted", Pehchaan.ignoringBatteryOptimisations(context))
        put("sdk_int", Build.VERSION.SDK_INT)
        put("screen_share_detect", Build.VERSION.SDK_INT >= 35)
    }

    private fun toJs(c: CallContext) = JSObject().apply {
        put("call", JSObject.fromJSONObject(c.toApiJson()))
        put("meta", JSObject().apply {
            put("source", c.source)
            put("audio_mode", c.audioMode)
            put("contact_name", c.contactName ?: JSONObject.NULL)
            put("screen_recording", Pehchaan.screenRecording ?: JSONObject.NULL)
        })
    }
}
