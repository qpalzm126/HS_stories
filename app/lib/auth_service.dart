import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:home_widget/home_widget.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

/// 登入使用者身分（非敏感：username / server / is_admin）。
class AuthUser {
  final String username;
  final String server;
  final bool isAdmin;

  const AuthUser({
    required this.username,
    required this.server,
    required this.isAdmin,
  });

  factory AuthUser.fromJson(Map<String, dynamic> j) => AuthUser(
        username: (j['username'] ?? '') as String,
        server: (j['server'] ?? '') as String,
        isAdmin: (j['is_admin'] ?? false) as bool,
      );

  Map<String, dynamic> toJson() =>
      {'username': username, 'server': server, 'is_admin': isAdmin};
}

/// 登入狀態管理：以外部論壇帳密向後端 `/api/login` 換取簽章 token。
///
/// - token 存 `flutter_secure_storage`（前景）；同時鏡射到 home_widget 共享儲存，
///   讓背景 isolate（widget 更新）也能讀到（見 login-plan §7.3）。
/// - **絕不儲存使用者的論壇密碼**，密碼只在登入當下送後端驗證。
class AuthService {
  AuthService({String? baseUrl, http.Client? client})
      : baseUrl = (baseUrl ?? Config.apiBaseUrl).replaceAll(RegExp(r'/+$'), ''),
        _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _kTokenKey = 'hs_token';
  static const String _kUserKey = 'hs_user';

  /// 全域登入旗標：登入/登出/401 失效時更新，讓 App 根畫面切換登入頁/首頁。
  static final ValueNotifier<bool> loggedIn = ValueNotifier<bool>(false);

  /// 用外部論壇帳密登入。成功則存 token 與身分；失敗丟 [AuthException]。
  Future<AuthUser> login(String server, String username, String password) async {
    late http.Response res;
    try {
      res = await _client
          .post(
            Uri.parse('$baseUrl/api/login'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'server': server,
              'username': username,
              'password': password,
            }),
          )
          .timeout(const Duration(seconds: 20));
    } catch (_) {
      throw AuthException('無法連線到伺服器，請稍後再試');
    }

    if (res.statusCode == 401) throw AuthException('帳號或密碼錯誤');
    if (res.statusCode == 400) throw AuthException('登入來源不支援');
    if (res.statusCode == 502 || res.statusCode == 503) {
      throw AuthException('論壇伺服器暫時無法連線，請稍後再試');
    }
    if (res.statusCode != 200) throw AuthException('登入失敗 (${res.statusCode})');

    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    final token = (data['token'] ?? '') as String;
    if (token.isEmpty) throw AuthException('登入回應缺少 token');

    final user = AuthUser.fromJson(data);
    await _persist(token, user);
    loggedIn.value = true;
    return user;
  }

  Future<void> _persist(String token, AuthUser user) async {
    await _storage.write(key: _kTokenKey, value: token);
    await _storage.write(key: _kUserKey, value: jsonEncode(user.toJson()));
    // 鏡射 token 到 home_widget 共享儲存，供背景 isolate 讀取。
    await HomeWidget.setAppGroupId(Config.appGroupId);
    await HomeWidget.saveWidgetData<String>(Config.kToken, token);
  }

  Future<String?> token() async {
    final t = await _storage.read(key: _kTokenKey);
    return (t != null && t.isNotEmpty) ? t : null;
  }

  Future<AuthUser?> currentUser() async {
    final raw = await _storage.read(key: _kUserKey);
    if (raw == null) return null;
    try {
      return AuthUser.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<bool> isLoggedIn() async => (await token()) != null;

  Future<void> logout() async {
    await _clearStored();
    loggedIn.value = false;
  }

  static Future<void> _clearStored() async {
    try {
      await _storage.delete(key: _kTokenKey);
      await _storage.delete(key: _kUserKey);
    } catch (_) {/* 背景 isolate 可能受限，忽略 */}
    try {
      await HomeWidget.setAppGroupId(Config.appGroupId);
      await HomeWidget.saveWidgetData<String>(Config.kToken, '');
    } catch (_) {/* 忽略 */}
  }

  /// token 失效（後端回 401）時呼叫：清掉本地憑證並通知 UI 導回登入頁。
  /// 前景與背景 isolate 都可能呼叫，故清除失敗一律吞掉。
  static Future<void> handleUnauthorized() async {
    await _clearStored();
    loggedIn.value = false;
  }
}

class AuthException implements Exception {
  final String message;
  AuthException(this.message);
  @override
  String toString() => message;
}
