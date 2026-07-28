package com.example.bookpagemap

import android.content.Context
import android.util.AttributeSet
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.SeekBar
import com.example.bookpagemap.databinding.OverlayViewBinding

/**
 * 覆盖层内容 View：
 * - ImageView 显示本地地图 PNG，默认透明度 0.5，支持拖动
 * - SeekBar 调整透明度（不缩放）
 */
class OverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : FrameLayout(context, attrs, defStyleAttr) {

    // 由 OverlayService 注入，用于拖动时更新位置 / 从窗口移除
    var windowManager: WindowManager? = null
    var overlayLayoutParams: WindowManager.LayoutParams? = null

    private val binding: OverlayViewBinding =
        OverlayViewBinding.inflate(LayoutInflater.from(context), this, true)

    init {
        // 默认透明度 0.5
        binding.ivMap.alpha = 0.5f
        binding.sbOpacity.progress = 50
        binding.sbOpacity.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                // 只调图片透明度，控件本身保持清晰
                binding.ivMap.alpha = progress / 100f
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
        setupDrag()
    }

    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    /** 在图片上拖动即可移动整个覆盖层窗口 */
    private fun setupDrag() {
        binding.ivMap.setOnTouchListener { _, event ->
            val wm = windowManager ?: return@setOnTouchListener false
            val lp = overlayLayoutParams ?: return@setOnTouchListener false
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = lp.x
                    initialY = lp.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    lp.x = initialX + (event.rawX - initialTouchX).toInt()
                    lp.y = initialY + (event.rawY - initialTouchY).toInt()
                    wm.updateViewLayout(this@OverlayView, lp)
                    true
                }
                else -> false
            }
        }
    }
}
