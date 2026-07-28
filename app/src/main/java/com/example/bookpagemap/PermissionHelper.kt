package com.example.bookpagemap

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings

/**
 * 悬浮窗权限工具类。
 * SYSTEM_ALERT_WINDOW 属于特殊权限，不能运行时直接申请，
 * 必须跳转到系统设置页由用户手动开启。
 */
object PermissionHelper {

    /** 是否已获得“在其他应用上层显示”权限 */
    fun hasOverlayPermission(context: Context): Boolean =
        Settings.canDrawOverlays(context)

    /** 构造跳转到本应用悬浮窗授权页的 Intent */
    fun overlayPermissionIntent(context: Context): Intent =
        Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${context.packageName}")
        )
}
