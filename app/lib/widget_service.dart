import 'package:home_widget/home_widget.dart';
import 'package:workmanager/workmanager.dart';

import 'api.dart';
import 'config.dart';

/// 背景任務名稱（workmanager）。
const String kRefreshTaskName = 'hs-story.refresh-latest';
const String kRefreshUniqueName = 'hs-story.refresh-latest.periodic';

/// 抓最新一篇 → 寫入 home_widget 共享儲存 → 觸發原生 widget 重繪。
///
/// 前景（App 開啟）與背景（workmanager）都呼叫同一支，行為一致。
Future<void> updateHomeWidget({Api? api}) async {
  await HomeWidget.setAppGroupId(Config.appGroupId);

  final article = await (api ?? Api()).fetchLatest();
  if (article == null) return; // 尚無已發佈文章，維持現狀

  await HomeWidget.saveWidgetData<String>(Config.kTitle, article.title);
  await HomeWidget.saveWidgetData<String>(
      Config.kExcerpt, article.excerpt ?? '');
  await HomeWidget.saveWidgetData<String>(Config.kUrl, article.url ?? '');
  await HomeWidget.saveWidgetData<String>(
      Config.kPublishedAt, article.publishedAt ?? '');

  await HomeWidget.updateWidget(
    iOSName: Config.iOSWidgetName,
    androidName: Config.androidWidgetName,
  );
}

/// workmanager 背景進入點：必須是 top-level 且標註 vm:entry-point。
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((taskName, inputData) async {
    try {
      await updateHomeWidget();
      return true;
    } catch (_) {
      // 背景抓取失敗（如離線）→ 回 false 讓系統稍後重試，widget 維持舊資料。
      return false;
    }
  });
}

/// 在 App 啟動時初始化背景定時更新。
///
/// iOS 背景刷新頻率由系統決定（約一天數十次）；Android 最短 15 分鐘，
/// 這裡設 30 分鐘。對「每日一篇」的更新節奏足夠。
Future<void> registerBackgroundRefresh() async {
  await Workmanager().initialize(callbackDispatcher);
  await Workmanager().registerPeriodicTask(
    kRefreshUniqueName,
    kRefreshTaskName,
    frequency: const Duration(minutes: 30),
    existingWorkPolicy: ExistingPeriodicWorkPolicy.keep,
    constraints: Constraints(networkType: NetworkType.connected),
  );
}
