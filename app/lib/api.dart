import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:home_widget/home_widget.dart';
import 'package:http/http.dart' as http;

import 'auth_service.dart';
import 'config.dart';
import 'models.dart';

/// API 用戶端。整站需登入，每個請求帶 `Authorization: Bearer <token>`。
///
/// token 解析順序：建構時注入的 [token] → flutter_secure_storage（前景）→
/// home_widget 共享儲存（背景 isolate 後備，見 login-plan §7.3）。
class Api {
  final String baseUrl;
  final http.Client _client;
  final String? _token;

  Api({String? baseUrl, http.Client? client, String? token})
      : baseUrl = (baseUrl ?? Config.apiBaseUrl).replaceAll(RegExp(r'/+$'), ''),
        _client = client ?? http.Client(),
        _token = token;

  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  /// 取得目前 token（前景讀 secure storage，背景讀 home_widget 共享儲存）。
  Future<String?> _resolveToken() async {
    final injected = _token;
    if (injected != null && injected.isNotEmpty) return injected;
    try {
      final t = await _storage.read(key: 'hs_token');
      if (t != null && t.isNotEmpty) return t;
    } catch (_) {/* 背景 isolate 可能讀不到 secure storage，改走後備 */}
    try {
      await HomeWidget.setAppGroupId(Config.appGroupId);
      final t = await HomeWidget.getWidgetData<String>(Config.kToken);
      if (t != null && t.isNotEmpty) return t;
    } catch (_) {/* 忽略 */}
    return null;
  }

  Future<Map<String, String>> _authHeaders() async {
    final t = await _resolveToken();
    return {if (t != null && t.isNotEmpty) 'Authorization': 'Bearer $t'};
  }

  Future<http.Response> _get(Uri uri) async {
    final res = await _client
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 15));
    if (res.statusCode == 401) {
      // token 失效 → 清憑證並通知導回登入頁。
      await AuthService.handleUnauthorized();
      throw UnauthorizedException();
    }
    return res;
  }

  /// 已發佈文章列表；帶 [q] 則做標題/內文關鍵字搜尋，[sort] 指定排序
  /// （published_desc 最新在前／published_asc 最舊在前，對齊後端白名單）。
  Future<List<Article>> fetchArticles(
      {int limit = 50, int offset = 0, String? q, String? sort}) async {
    final query = <String, String>{
      'limit': '$limit',
      'offset': '$offset',
      if (q != null && q.trim().isNotEmpty) 'q': q.trim(),
      if (sort != null && sort.isNotEmpty) 'sort': sort,
    };
    final uri =
        Uri.parse('$baseUrl/api/articles').replace(queryParameters: query);
    final res = await _get(uri);
    if (res.statusCode != 200) {
      throw ApiException('列表載入失敗 (${res.statusCode})');
    }
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as List<dynamic>;
    return data
        .map((e) => Article.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 最新一篇（widget / 首頁 hero 用）。無文章時回 null（後端回 404）。
  Future<Article?> fetchLatest() async {
    final res = await _get(_u('/api/articles/latest'));
    if (res.statusCode == 404) return null;
    if (res.statusCode != 200) {
      throw ApiException('最新文章載入失敗 (${res.statusCode})');
    }
    return Article.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  /// 單篇全文（含 Markdown body）。
  Future<Article> fetchArticle(String slug) async {
    final res = await _get(_u('/api/articles/$slug'));
    if (res.statusCode != 200) {
      throw ApiException('文章載入失敗 (${res.statusCode})');
    }
    return Article.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

/// token 失效 / 未登入（後端 401）。UI 應導回登入頁。
class UnauthorizedException extends ApiException {
  UnauthorizedException() : super('請重新登入');
}
