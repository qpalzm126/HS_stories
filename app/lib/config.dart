/// App 全域設定。
///
/// [apiBaseUrl] 指向已部署的後端（Phase C 部署後填入實際網址）。
/// 開發時可用 `--dart-define` 覆寫，例如：
///
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010
///
/// 注意：
/// - Android 模擬器連本機用 `10.0.2.2`（不是 localhost）。
/// - iOS 模擬器連本機用 `http://127.0.0.1:8010`。
/// - 用 http（非 https）連本機時，需在 iOS Info.plist 開 ATS、
///   Android 設 `usesCleartextTraffic`（見 app/README.md）。
class Config {
  /// 後端公開網址。預設留空字串代表「尚未設定」。
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://hs-story.onrender.com',
  );

  /// iOS App Group / Android widget provider 共用的識別碼。
  /// 必須與 iOS 專案的 App Group、Android widget provider 設定一致。
  static const String appGroupId = 'group.com.hsstory.app';

  /// iOS widget 的 kind（對應 Swift 端 `IntentConfiguration/StaticConfiguration` 的 kind）。
  static const String iOSWidgetName = 'HSStoryWidget';

  /// Android widget provider 類別名稱（對應 Kotlin 端 AppWidgetProvider）。
  static const String androidWidgetName = 'HSStoryWidgetProvider';

  /// home_widget 共享儲存使用的鍵。iOS/Android 原生端讀取同一組鍵。
  static const String kTitle = 'hs_title';
  static const String kExcerpt = 'hs_excerpt';
  static const String kUrl = 'hs_url';
  static const String kPublishedAt = 'hs_published_at';

  /// Android widget 左右切換用：最新 N 篇的 JSON 陣列
  /// （每筆 title/excerpt/url/slug/date）。iOS 仍讀上面的單篇 key。
  static const String kArticles = 'hs_articles';
}
