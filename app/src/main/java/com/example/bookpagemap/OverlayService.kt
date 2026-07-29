package com.example.bookpagemap

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import java.io.File
import java.io.PrintWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 参考 Quasar 的 OverlayService：
 * 在 Service 中通过 WindowManager.addView() 把覆盖层挂到系统窗口上，
 * 用 removeView() 把它摘掉。
 * 用前台服务保活，保证切到游戏后覆盖层依然在。
 */
class OverlayService : Service() {

    private var windowManager: WindowManager? = null
    private var overlayView: OverlayView? = null

    override fun onCreate() {
        super.onCreate()
        // 必须先成为前台服务，否则 addView 也可能被回收
        try {
            startForeground(NOTIFICATION_ID, buildNotification())
        } catch (e: Exception) {
            logCrash("startForeground", e)
        }

        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager

        try {
            overlayView = OverlayView(this).apply {
                val lp = WindowManager.LayoutParams(
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    // 系统级覆盖层类型（Android 8.0+ 唯一合法悬浮窗类型）
                    WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                    // 不抢焦点 + 窗口外的触摸穿透到下层（游戏）
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                    PixelFormat.TRANSLUCENT
                )
                lp.gravity = Gravity.TOP or Gravity.START
                lp.x = 100
                lp.y = 250

                this.overlayLayoutParams = lp
                this.windowManager = windowManager
                windowManager?.addView(this, lp)
            }
        } catch (e: Exception) {
            logCrash("addView", e)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // 被杀后系统尝试重启，保持覆盖层可用
        return START_STICKY
    }

    override fun onDestroy() {
        overlayView?.let { windowManager?.removeView(it) }
        overlayView = null
        windowManager = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildNotification(): Notification {
        val channelId = "overlay_channel"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val chan = NotificationChannel(
                channelId,
                "地图覆盖层",
                NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(chan)
        }
        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("书页笔记地图助手")
            .setContentText("地图覆盖层运行中")
            .setSmallIcon(R.drawable.ic_overlay)
            .build()
    }

    /** 把异常写到 App 私有目录的 overlay_crash.log，方便回传定位（不会弹窗） */
    private fun logCrash(where: String, e: Exception) {
        Log.e("OverlayService", "crash at $where", e)
        try {
            val dir = getExternalFilesDir(null) ?: filesDir
            val f = File(dir, "overlay_crash.log")
            PrintWriter(f, Charsets.UTF_8).use { pw ->
                pw.println(
                    "${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())} " +
                        "crash at $where"
                )
                e.printStackTrace(pw)
            }
        } catch (_: Exception) {
            // 写日志失败也别再抛异常
        }
    }

    companion object {
        const val NOTIFICATION_ID = 1001
    }
}
