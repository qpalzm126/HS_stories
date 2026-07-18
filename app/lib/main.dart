import 'package:flutter/material.dart';
import 'package:home_widget/home_widget.dart';
import 'package:url_launcher/url_launcher.dart';

import 'config.dart';
import 'home_screen.dart';
import 'theme.dart';
import 'widget_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await HomeWidget.setAppGroupId(Config.appGroupId);

  // 背景定時更新 widget（失敗不擋 App 啟動）。
  try {
    await registerBackgroundRefresh();
  } catch (_) {}

  // App 一開就抓一次最新，讓 widget 立即有資料。
  updateHomeWidget().catchError((_) {});

  runApp(const HSStoryApp());
}

class HSStoryApp extends StatefulWidget {
  const HSStoryApp({super.key});

  @override
  State<HSStoryApp> createState() => _HSStoryAppState();
}

class _HSStoryAppState extends State<HSStoryApp> {
  @override
  void initState() {
    super.initState();
    // 從 widget 點擊喚醒 App 時，開啟對應文章網址。
    HomeWidget.widgetClicked.listen(_onWidgetClicked);
    HomeWidget.initiallyLaunchedFromHomeWidget().then(_onWidgetClicked);
  }

  void _onWidgetClicked(Uri? uri) {
    if (uri == null) return;
    final target = uri.queryParameters['url'];
    if (target != null && target.isNotEmpty) {
      launchUrl(Uri.parse(target), mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '聖靈故事',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(Brightness.light),
      darkTheme: buildAppTheme(Brightness.dark),
      home: const HomeScreen(),
    );
  }
}
