import 'dart:convert';

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

  final client = api ?? Api();
  final articles = await client.fetchArticles(limit: 10);
  if (articles.isEmpty) return; // 尚無已發佈文章，維持現狀

  // 補上每篇全文（widget 顯示全文用）；平行抓、失敗則留空退回 excerpt。
  final bodies = await Future.wait(articles.map((a) async {
    try {
      return (await client.fetchArticle(a.slug)).body ?? '';
    } catch (_) {
      return '';
    }
  }));

  // Android widget 左右切換 + 顯示全文用：最新 N 篇。
  final list = [
    for (var i = 0; i < articles.length; i++)
      {
        'title': articles[i].title,
        'excerpt': articles[i].excerpt ?? '',
        'body': bodies[i],
        'url': articles[i].url ?? '',
        'slug': articles[i].slug,
        'date': articles[i].publishedAt ?? '',
      }
  ];
  await HomeWidget.saveWidgetData<String>(Config.kArticles, jsonEncode(list));

  // 保留單篇 key（iOS widget 讀這組；Android 空清單時的後備）＝最新一篇。
  final latest = articles.first;
  await HomeWidget.saveWidgetData<String>(Config.kTitle, latest.title);
  await HomeWidget.saveWidgetData<String>(
      Config.kExcerpt, latest.excerpt ?? '');
  await HomeWidget.saveWidgetData<String>(Config.kUrl, latest.url ?? '');
  await HomeWidget.saveWidgetData<String>(
      Config.kPublishedAt, latest.publishedAt ?? '');

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
