import 'package:flutter/material.dart';
import 'package:home_widget/home_widget.dart';
import 'package:url_launcher/url_launcher.dart';

import 'article_screen.dart';
import 'auth_service.dart';
import 'config.dart';
import 'home_screen.dart';
import 'login_screen.dart';
import 'theme.dart';
import 'widget_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await HomeWidget.setAppGroupId(Config.appGroupId);

  // 背景定時更新 widget（失敗不擋 App 啟動）。
  try {
    await registerBackgroundRefresh();
  } catch (_) {}

  runApp(const HSStoryApp());
}

class HSStoryApp extends StatefulWidget {
  const HSStoryApp({super.key});

  @override
  State<HSStoryApp> createState() => _HSStoryAppState();
}

class _HSStoryAppState extends State<HSStoryApp> {
  final _navKey = GlobalKey<NavigatorState>();

  @override
  void initState() {
    super.initState();
    // 從 widget 點擊喚醒 App 時的處理（🔊 朗讀 → 開該篇並自動朗讀）。
    HomeWidget.widgetClicked.listen(_onWidgetClicked);
    HomeWidget.initiallyLaunchedFromHomeWidget().then(_onWidgetClicked);
  }

  void _onWidgetClicked(Uri? uri) {
    if (uri == null) return;
    // widget 的 🔊：hsstory://speak?slug=xxx → 開該篇文章並自動朗讀。
    // 未登入時 ArticleScreen 會因 401 導回登入頁。
    if (uri.host == 'speak') {
      final slug = uri.queryParameters['slug'];
      if (slug != null && slug.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _navKey.currentState?.push(
            MaterialPageRoute(
                builder: (_) => ArticleScreen(slug: slug, autoPlay: true)),
          );
        });
      }
      return;
    }
    // 相容：帶 url query 則以外部瀏覽器開啟。
    final target = uri.queryParameters['url'];
    if (target != null && target.isNotEmpty) {
      launchUrl(Uri.parse(target), mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '聖靈故事',
      navigatorKey: _navKey,
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(Brightness.light),
      darkTheme: buildAppTheme(Brightness.dark),
      home: const _AuthGate(),
    );
  }
}

/// 依登入狀態決定進首頁或登入頁；監聽 [AuthService.loggedIn]，
/// 登入/登出/token 失效（401）時自動切換。
class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  final _auth = AuthService();
  bool _checking = true;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final logged = await _auth.isLoggedIn();
    AuthService.loggedIn.value = logged;
    if (mounted) setState(() => _checking = false);
    // 已登入才更新 widget（帶 token）；未登入不打 API 以免無謂 401。
    if (logged) updateHomeWidget().catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return ValueListenableBuilder<bool>(
      valueListenable: AuthService.loggedIn,
      builder: (context, logged, _) =>
          logged ? const HomeScreen() : const LoginScreen(),
    );
  }
}
