import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';
import 'models.dart';

/// 只讀公開 API 的用戶端。後台功能走網頁後台，不在 App 內。
class Api {
  final String baseUrl;
  final http.Client _client;

  Api({String? baseUrl, http.Client? client})
      : baseUrl = (baseUrl ?? Config.apiBaseUrl).replaceAll(RegExp(r'/+$'), ''),
        _client = client ?? http.Client();

  Uri _u(String path) => Uri.parse('$baseUrl$path');

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
    final res = await _client.get(uri).timeout(const Duration(seconds: 15));
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
    final res = await _client
        .get(_u('/api/articles/latest'))
        .timeout(const Duration(seconds: 15));
    if (res.statusCode == 404) return null;
    if (res.statusCode != 200) {
      throw ApiException('最新文章載入失敗 (${res.statusCode})');
    }
    return Article.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  /// 單篇全文（含 Markdown body）。
  Future<Article> fetchArticle(String slug) async {
    final res = await _client
        .get(_u('/api/articles/$slug'))
        .timeout(const Duration(seconds: 15));
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
