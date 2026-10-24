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
 * Keeps the process alive so call state is seen even when the app is closed (payer), and holds the
 * Family Verify WebSocket (relative). Shows one quiet ongoing notification, as Android requires.
 */
class PehchaanService : Service() {
    private var fv: FamilyVerifyListener? = null
    private var linked = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Pehchaan.ensureChannels(this)
        val cfg = Pehchaan.config(this)
        ServiceCompat.startForeground(this, Pehchaan.NOTIF_SVC, ongoing(cfg),
            if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0)
        if (cfg == null) { stopSelf(); return START_NOT_STICKY }
        CallMonitor.start(this)
        if (cfg.role == "relative" && cfg.deviceId != null && fv == null) {
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
        .setContentTitle(if (cfg?.role == "relative") "Pehchaan Family is on" else "Pehchaan is protecting your payments")
        .setContentText(when {
            cfg?.role != "relative" -> "Checks payments made during or just after a call. Never listens to calls."
            linked -> "Connected. You'll be asked if someone uses your name to ask for money."
            else -> "Connecting…"
        })
        .setOngoing(true)
        .setPriority(NotificationCompat.PRIORITY_LOW)
        .setContentIntent(Pehchaan.openAppIntent(this, cfg?.role ?: "payer", 1))
        .build()

    override fun onDestroy() {
        fv?.stop()
        fv = null
        super.onDestroy()
    }
}
