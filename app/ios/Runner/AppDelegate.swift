import Flutter
import UIKit
import workmanager_apple

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // 讓 workmanager 的背景 isolate 能用其他插件（home_widget 需寫 App Group）。
    WorkmanagerPlugin.setPluginRegistrantCallback { registry in
      GeneratedPluginRegistrant.register(with: registry)
    }
    // 註冊定時更新 widget 的 BGTask。identifier 必須三處一致：
    // 這裡、Info.plist 的 BGTaskSchedulerPermittedIdentifiers、
    // 以及 Dart 端 registerPeriodicTask 的 uniqueName（widget_service.dart）。
    // frequency 為每次執行後重新排程的最短間隔（秒），對齊 Dart 的 30 分鐘。
    WorkmanagerPlugin.registerPeriodicTask(
      withIdentifier: "hs-story.refresh-latest.periodic",
      frequency: NSNumber(value: 30 * 60)
    )
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }
}
