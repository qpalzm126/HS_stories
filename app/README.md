# 聖靈故事 App（Phase B）— Flutter + iOS/Android Widget

顯示**最新一篇聖靈故事**的手機 App 與桌面 widget。內容全部來自後端 API
（`/api/articles`、`/api/articles/latest`、`/api/articles/{slug}`）。

> **整站需登入**：App 啟動先進登入畫面，用 **HeavensBride / TCGM 論壇帳密**
> 向後端 `/api/login` 換 token（見專案根 `docs/login-plan.md`）。之後每個 API
> 請求帶 `Authorization: Bearer <token>`；token 存 `flutter_secure_storage`，
> 並鏡射到 home_widget 共享儲存讓背景 isolate 讀取。

> 狀態：登入功能（`auth_service.dart` / `login_screen.dart`）為新增，Dart 程式碼
> 依現有風格撰寫；**尚未在真機/模擬器編譯**（本機缺 Flutter SDK / Android SDK /
> Xcode——補裝後即可 `flutter test` 與 `flutter run`）。
> iOS 的 Widget Extension 需在 Xcode GUI 建立（步驟 4），這步無法預先寫進 repo。

## 這裡有什麼

```
app/
├── pubspec.yaml                     依賴（http / flutter_secure_storage / home_widget / workmanager / url_launcher / flutter_markdown）
├── lib/
│   ├── config.dart                  API base、App Group id、共享儲存 key（先改這裡）
│   ├── models.dart                  Article 資料模型（對應後端輸出）
│   ├── auth_service.dart            登入：/api/login 換 token、存 secure storage、登出
│   ├── api.dart                     API 用戶端（每個請求帶 Bearer token、401 導回登入）
│   ├── login_screen.dart            登入畫面：選 server（HeavensBride/TCGM）+ 論壇帳密
│   ├── widget_service.dart          背景抓 latest → 寫共享儲存 → 更新 widget（workmanager 進入點）
│   ├── home_screen.dart             首頁：故事列表（下拉重整）＋ 登出
│   ├── article_screen.dart          文章詳情（Markdown 呈現）
│   └── main.dart                    App 進入點、登入狀態 gate、背景任務、widget 點擊處理
├── ios/HSStoryWidget/HSStoryWidget.swift     iOS WidgetKit（SwiftUI）
└── android/app/src/main/
    ├── kotlin/com/hsstory/app/HSStoryWidgetProvider.kt   Android widget provider
    └── res/{layout,drawable,xml}/…                        widget 版面與設定
```

## 前置：補齊工具鏈

Flutter 本體已裝。還缺的（`flutter doctor` 會列出）：

- **Android**：裝 Android Studio → SDK + 一個模擬器（AVD）。裝完 `flutter doctor --android-licenses`。
- **iOS**：裝完整 **Xcode** + `sudo gem install cocoapods`（上架另需 Apple 開發者帳號 $99/年）。

## 步驟 1：取得依賴

平台骨架（`flutter create` 的產物）與 `applicationId=com.hsstory.app`、Kotlin 於
`android/app/src/main/kotlin/com/hsstory/app/` **都已在 repo 內**，只需：

```bash
cd /Users/leon.chen/code/hs-story/app
flutter pub get
```

## 步驟 2：設定後端網址

編輯 `lib/config.dart` 的 `apiBaseUrl`，或每次執行時用 `--dart-define` 帶入。

- **連本機後端**（後端跑在 8010，見主 repo README）：
  - Android 模擬器：`--dart-define=API_BASE_URL=http://10.0.2.2:8010`
  - iOS 模擬器：`--dart-define=API_BASE_URL=http://127.0.0.1:8010`
- **連已部署後端**（Phase C 之後）：把 `apiBaseUrl` 改成正式網址（https）。

> 用 http 連本機時需允許明文流量：
> - Android：`android/app/src/main/AndroidManifest.xml` 的 `<application>` 加 `android:usesCleartextTraffic="true"`（僅測試用）。
> - iOS：`ios/Runner/Info.plist` 暫時加 ATS 例外（僅測試用）。正式用 https 就不需要。

## 步驟 3：Android widget（已接好，無需動作）

`AndroidManifest.xml` 的 `<receiver>` 註冊、`res/{layout,drawable,xml}` 版面、Kotlin provider
**都已在 repo 內**。`home_widget` / `workmanager` 的 Android 設定由套件自動處理。裝好 Android SDK 後
即可直接跑，桌面長按加入小工具即會出現「聖靈故事」。

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

## 登入與背景更新（login-plan §7）

- 啟動先進登入頁；輸入 HeavensBride / TCGM 帳密 → `/api/login` 換 token。登出在首頁右上角。
- token 存 `flutter_secure_storage`（前景），並鏡射到 home_widget 共享儲存供**背景 isolate**
  （workmanager widget 更新）讀取——因 secure storage 在背景 isolate 可能受限，token
  為簽章字串非密碼，此後備風險可接受。
- 未登入 / token 失效時，背景更新會因 401 跳過，widget **維持舊資料不崩潰**。
- 真機/模擬器實測時需再驗證：背景 isolate 讀 token 是否穩定、iOS widget extension 帶 token。

## 已知限制

- Widget 非即時：iOS 一天約數十次刷新、Android 最短 ~15 分鐘 → 發佈到 widget 顯示最多約 30–60 分延遲（對每日故事可接受）。
- `apiBaseUrl` 預設指向已部署後端，**未設定會抓不到資料**，務必於步驟 2 設定。
- iOS 實機/上架需 Apple 開發者帳號與簽章設定。
- 邊界情況：文章詳情頁載入中 token 剛好過期時，會先顯示錯誤再由根層導回登入頁（非致命，實測時可再優化為直接彈回）。
