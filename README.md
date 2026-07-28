# 书页笔记地图助手 — 第一阶段 Demo

验证 Android 系统级透明悬浮覆盖层（Overlay）能力。

> 本阶段**只做一件事**：打开 App → 点“开启地图覆盖” → 一张半透明地图 PNG 浮在任意 App（如第五人格）画面上方；点“关闭地图覆盖”即消失。
> 未实现：悬浮球、菜单、截图、OCR、OpenCV、AI、地图匹配、路线规划、网络请求。

---

## 一、功能对照（需求 → 实现）

| 需求 | 实现 |
|------|------|
| 原生 WindowManager | `OverlayService` 用 `WindowManager.addView()` |
| `TYPE_APPLICATION_OVERLAY` | `OverlayService.kt` LayoutParams 指定 |
| `SYSTEM_ALERT_WINDOW` 权限 | `AndroidManifest.xml` 声明 + `PermissionHelper` 跳系统授权页 |
| 参考 Quasar 的 OverlayService 结构 | Service 管理 Overlay，前台服务保活，`removeView` 关闭 |
| 显示本地 PNG | `res/drawable/map_overlay.png` → `OverlayView` 内 `ImageView` |
| 透明覆盖 | `FLAG_NOT_FOCUSABLE` or `FLAG_NOT_TOUCH_MODAL` + `PixelFormat.TRANSLUCENT` |
| 默认透明度 0.5 | `OverlayView` 中 `ivMap.alpha = 0.5f` |
| 可拖动 | `OverlayView` 内 `ImageView` 的 `OnTouchListener` 更新 `LayoutParams.x/y` |
| 可调透明度 | `OverlayView` 内 `SeekBar` 调整 `ivMap.alpha`（不缩放） |

---

## 二、环境要求

- Android Studio（Hedgehog / Iguana / Jellyfish 均可）
- JDK 17（Android Studio 自带，无需单独装）
- 一台 Android 8.0（API 26）及以上真机 **（模拟器默认无“显示在其他应用上层”权限且难验证覆盖效果，建议真机）**
- 数据线 / adb

---

## 三、构建 APK（两种方式）

### 方式 A：Android Studio 直接打开（推荐）
1. 打开 Android Studio → `File → Open` → 选择本目录 `BookPageMapAssistant`。
2. 等待 Gradle Sync 完成（首次会下载 Gradle 8.7 与 AGP 8.5，需联网）。
3. `Build → Build Bundle(s) / APK → Build APK(s)`。
4. 完成后右下角弹窗 `locate` 找到 `app/build/outputs/apk/debug/app-debug.apk`。

### 方式 B：命令行（需配好 Android SDK 与 JDK 17）
```bash
cd BookPageMapAssistant
./gradlew assembleDebug        # Windows 用 gradlew.bat
# 产物：app/build/outputs/apk/debug/app-debug.apk
```
> 已内置 `gradle-wrapper.jar`，无需本机预装 Gradle。

---

## 四、安装与测试步骤

1. 把 `app-debug.apk` 装到手机（双击或用 `adb install app-debug.apk`）。
2. 打开「书页笔记地图助手」。
3. 点 **开启地图覆盖**：
   - 若首次，会跳到系统“在其他应用上层显示”设置页 → 找到本应用 → 打开开关 → 返回。
   - 返回后再次点 **开启地图覆盖**，状态栏出现“地图覆盖层运行中”通知，屏幕上出现半透明地图。
4. 按 Home 回桌面，打开 **第五人格（或其他任意 App）**：游戏画面正常，地图覆盖在其上方。
5. 在覆盖层上：
   - **拖动**图片可移动位置；
   - 拖动下方 **滑条** 调整透明度（0.1~1.0，默认 0.5）。
6. 回到「书页笔记地图助手」，点 **关闭地图覆盖** → 覆盖层立即消失，通知清除。

---

## 五、常见问题

- **点开启没反应 / 提示需权限**：Android 8+ 必须手动授权 `SYSTEM_ALERT_WINDOW`，App 内无法直接授予，会跳转系统设置页。
- **覆盖层一切到后台就没了**：已用前台服务保活；若仍消失，检查是否系统“电池优化”把本应用限制了，加白名单即可。
- **看不到地图图片**：确认 `res/drawable/map_overlay.png` 存在；默认是占位地图，可替换为真实第五人格地图 PNG（建议 560×400 左右、带透明通道）。

---

## 六、下一步（第二阶段，待启动）

截图匹配 + 地图定位（不在本阶段范围内）。
