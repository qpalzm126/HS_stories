# 聖靈故事 App（Phase B）— Flutter + iOS/Android Widget

顯示**最新一篇聖靈故事**的手機 App 與桌面 widget。內容全部來自後端公開 API
（`/api/articles`、`/api/articles/latest`、`/api/articles/{slug}`）。

> ⚠️ 這個資料夾裡放的是**程式碼與設定**。因為開發機沒有 Flutter/Xcode/Android SDK，
> **尚未編譯執行過**。以下步驟是你裝好工具後，把這些檔案接進一個真正的 Flutter 專案。

## 這裡有什麼

```
app/
├── pubspec.yaml                     依賴（http / home_widget / workmanager / url_launcher / flutter_markdown）
├── lib/
│   ├── config.dart                  API base、App Group id、共享儲存 key（先改這裡）
│   ├── models.dart                  Article 資料模型（對應後端輸出）
│   ├── api.dart                     公開 API 用戶端
│   ├── widget_service.dart          背景抓 latest → 寫共享儲存 → 更新 widget（workmanager 進入點）
│   ├── home_screen.dart             首頁：故事列表（下拉重整）
│   ├── article_screen.dart          文章詳情（Markdown 呈現）
│   └── main.dart                    App 進入點、初始化背景任務、widget 點擊處理
├── ios/HSStoryWidget/HSStoryWidget.swift     iOS WidgetKit（SwiftUI）
└── android/app/src/main/
    ├── kotlin/com/hsstory/app/HSStoryWidgetProvider.kt   Android widget provider
    └── res/{layout,drawable,xml}/…                        widget 版面與設定
```

## 前置：安裝工具

```bash
# macOS 建議用官方安裝或 brew
brew install --cask flutter          # 或到 flutter.dev 下載 SDK
flutter doctor                       # 依提示補齊 Android Studio / Xcode / cocoapods
```

- Android：裝 Android Studio → SDK + 一個模擬器（AVD）。
- iOS：裝 Xcode + `sudo gem install cocoapods`（上架另需 Apple 開發者帳號 $99/年）。

## 步驟 1：建立 Flutter 專案骨架，疊入本資料夾

`flutter create` 會生成平台骨架（gradle、Xcode 專案等），這些沒放在 repo 裡，需你在本機生成：

```bash
cd /Users/leon.chen/code/hs-story/app

# 在「當前資料夾」生成骨架，套用固定 package/bundle id
flutter create . \
  --org com.hsstory \
  --project-name hs_story_app \
  --platforms=android,ios

# 生成後，我們寫好的 lib/ 會被保留；若 create 覆蓋了 main.dart，
# 用 git 還原我們的版本：
git checkout -- lib/ pubspec.yaml

flutter pub get
```

確認 `android/app/build.gradle` 的 `applicationId` 是 `com.hsstory.app`、
Kotlin 原始碼在 `android/app/src/main/kotlin/com/hsstory/app/`（本 repo 的 provider 已放這路徑）。

## 步驟 2：設定後端網址

編輯 `lib/config.dart` 的 `apiBaseUrl`，或每次執行時用 `--dart-define` 帶入。

- **連本機後端**（後端跑在 8010，見主 repo README）：
  - Android 模擬器：`--dart-define=API_BASE_URL=http://10.0.2.2:8010`
  - iOS 模擬器：`--dart-define=API_BASE_URL=http://127.0.0.1:8010`
- **連已部署後端**（Phase C 之後）：把 `apiBaseUrl` 改成正式網址（https）。

> 用 http 連本機時需允許明文流量：
> - Android：`android/app/src/main/AndroidManifest.xml` 的 `<application>` 加 `android:usesCleartextTraffic="true"`（僅測試用）。
> - iOS：`ios/Runner/Info.plist` 暫時加 ATS 例外（僅測試用）。正式用 https 就不需要。

## 步驟 3：Android widget 接線

1. **AndroidManifest.xml**（`android/app/src/main/AndroidManifest.xml`）在 `<application>` 內加：

   ```xml
   <receiver
       android:name=".HSStoryWidgetProvider"
       android:exported="true">
       <intent-filter>
           <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
       </intent-filter>
       <meta-data
           android:name="android.appwidget.provider"
           android:resource="@xml/hs_story_widget_info" />
   </receiver>
   ```

2. `res/layout/hs_story_widget.xml`、`res/drawable/hs_story_widget_background.xml`、
   `res/xml/hs_story_widget_info.xml`、Kotlin provider 都已放好，無需再改。

3. `home_widget` / `workmanager` 的 Android 設定由套件自動處理（`flutter pub get` 後即可）。

## 步驟 4：iOS widget 接線（需 Xcode）

1. `open ios/Runner.xcworkspace`。
2. **File → New → Target… → Widget Extension**，命名 `HSStoryWidget`，
   **取消勾選** Include Configuration Intent（用 StaticConfiguration）。
3. 用本 repo 的 `ios/HSStoryWidget/HSStoryWidget.swift` **取代** Xcode 自動生成的同名 Swift 檔內容
   （kind 必須是 `HSStoryWidget`，對應 `Config.iOSWidgetName`）。
4. **App Group**：在 **Runner** target 與 **HSStoryWidget** target 都到
   Signing & Capabilities → **+ Capability → App Groups**，加入
   `group.com.hsstory.app`（對應 `Config.appGroupId`）。
5. **背景刷新**：Runner target 的 Signing & Capabilities → **+ Background Modes** →
   勾 **Background fetch / Background processing**（workmanager iOS 需要）。

> iOS/Android 兩端讀的鍵（`hs_title / hs_excerpt / hs_url / hs_published_at`）
> 與 `lib/config.dart` 一致，改鍵名要三處一起改。

## 步驟 5：執行與驗證

先讓後端有一篇「已發佈」文章（用主 repo 後台 `/admin` 發佈一篇），再：

```bash
# 列出裝置
flutter devices

# Android 模擬器
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8010

# iOS 模擬器
flutter run -d "iPhone 15" --dart-define=API_BASE_URL=http://127.0.0.1:8010
```

驗證清單：
1. App 首頁出現故事列表，點一篇能看到 Markdown 全文。
2. 桌面**長按 → 加入小工具 → 聖靈故事**，widget 顯示最新文章標題+摘錄。
3. 後台發佈一篇「新的」文章後，等背景刷新（Android 最短 ~15–30 分；iOS 由系統排程），
   或重開 App（會立即 `updateHomeWidget`），widget 更新成新文章。
4. 點 widget → 開啟該篇文章網址。

## 已知限制

- Widget 非即時：iOS 一天約數十次刷新、Android 最短 ~15 分鐘 → 發佈到 widget 顯示最多約 30–60 分延遲（對每日故事可接受）。
- `apiBaseUrl` 預設是 `https://REPLACE_WITH_YOUR_DEPLOYED_URL`，**未設定會抓不到資料**，務必於步驟 2 設定。
- iOS 實機/上架需 Apple 開發者帳號與簽章設定。
