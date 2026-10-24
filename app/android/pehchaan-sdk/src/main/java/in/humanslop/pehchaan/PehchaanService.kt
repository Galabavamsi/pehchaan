package `in`.humanslop.pehchaan

import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat

/**
 * Keeps the process alive so call state is seen even when the app is closed, and holds this phone's Family Verify
 * WebSocket (every phone answers for someone in a circle). Shows one quiet ongoing notification, as Android requires.
 */
class PehchaanService : Service() {
    private var fv: FamilyVerifyListener? = null
    private var fvDevice: String? = null
    private var linked = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Pehchaan.ensureChannels(this)
        val cfg = Pehchaan.config(this)
        ServiceCompat.startForeground(this, Pehchaan.NOTIF_SVC, ongoing(cfg),
            if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0)
        if (cfg == null) { stopSelf(); return START_NOT_STICKY }
        CallMonitor.start(this)
        if (cfg.deviceId != fvDevice) {  // first start, or someone else now uses this phone
            fv?.stop()
            fv = null
            fvDevice = cfg.deviceId
            linked = false
        }
        if (cfg.deviceId != null && fv == null) {
            val ws = cfg.apiBase.replaceFirst(Regex("^http"), "ws") + "/ws/device/" + cfg.deviceId
            fv = FamilyVerifyListener(ws,
                onRequest = { Pehchaan.showFamilyVerify(this, it) },
                onClear = { Pehchaan.clearFamilyVerify(this) },
                onLink = { up -> if (up != linked) { linked = up; refresh() } },
            ).also { it.start() }
        }
        return START_STICKY
    }

    private fun refresh() {
        runCatching { NotificationManagerCompat.from(this).notify(Pehchaan.NOTIF_SVC, ongoing(Pehchaan.config(this))) }
    }

    private fun ongoing(cfg: Pehchaan.Config?) = NotificationCompat.Builder(this, Pehchaan.CH_SVC)
        .setSmallIcon(R.drawable.ic_pehchaan)
        .setContentTitle("Pehchaan is protecting your payments")
        .setContentText(when {
            cfg?.deviceId == null -> "Checks payments made during or just after a call. Never listens to calls."
            linked -> "Checks payments during calls, and asks you first when someone uses your name."
            else -> "Connecting…"
        })
        .setOngoing(true)
        .setPriority(NotificationCompat.PRIORITY_LOW)
        .setContentIntent(Pehchaan.openAppIntent(this, "home", 1))
        .addAction(0, "Setup", Pehchaan.openAppIntent(this, "setup", 3))
        .build()

    override fun onDestroy() {
        fv?.stop()
        fv = null
        super.onDestroy()
    }
}
