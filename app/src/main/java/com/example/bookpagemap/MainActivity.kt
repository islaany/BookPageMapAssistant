package com.example.bookpagemap

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.example.bookpagemap.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    // 跳转到系统“悬浮窗权限”设置页后，回到本页时回调
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        if (PermissionHelper.hasOverlayPermission(this)) {
            startOverlay()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Android 13+ 申请通知权限（让前台服务通知能显示，不授权也不影响覆盖层）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100)
        }

        binding.btnStart.setOnClickListener {
            if (PermissionHelper.hasOverlayPermission(this)) {
                startOverlay()
            } else {
                // 没有权限 -> 跳转系统授权页面
                permissionLauncher.launch(PermissionHelper.overlayPermissionIntent(this))
            }
        }

        binding.btnStop.setOnClickListener {
            stopOverlay()
        }
    }

    private fun startOverlay() {
        val intent = Intent(this, OverlayService::class.java)
        // API 26+ 必须以前台服务方式启动，否则切到后台会被系统回收
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopOverlay() {
        stopService(Intent(this, OverlayService::class.java))
    }
}
