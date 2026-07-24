import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:hs_story_app/api.dart';
import 'package:hs_story_app/auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // 以記憶體 map 模擬 flutter_secure_storage 與 home_widget 的平台通道，
  // 讓 AuthService 的儲存/讀取在測試中可運作。
  final secureStore = <String, String>{};
  final widgetStore = <String, String>{};

  setUp(() {
    secureStore.clear();
    widgetStore.clear();
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

    messenger.setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async {
        final args = (call.arguments as Map?)?.cast<String, dynamic>() ?? {};
        switch (call.method) {
          case 'write':
            secureStore[args['key'] as String] = args['value'] as String;
            return null;
          case 'read':
            return secureStore[args['key'] as String];
          case 'delete':
            secureStore.remove(args['key'] as String);
            return null;
          case 'readAll':
            return Map<String, String>.from(secureStore);
          case 'deleteAll':
            secureStore.clear();
            return null;
          case 'containsKey':
            return secureStore.containsKey(args['key'] as String);
        }
        return null;
      },
    );

    messenger.setMockMethodCallHandler(
      const MethodChannel('home_widget'),
      (call) async {
        final args = (call.arguments as Map?)?.cast<String, dynamic>() ?? {};
        switch (call.method) {
          case 'saveWidgetData':
            widgetStore[args['id'] as String] = '${args['data']}';
            return true;
          case 'getWidgetData':
            return widgetStore[args['id'] as String] ?? args['defaultValue'];
          case 'setAppGroupId':
          case 'updateWidget':
            return true;
        }
        return null;
      },
    );
  });

  group('AuthUser', () {
    test('fromJson / toJson 往返', () {
      final u = AuthUser.fromJson({
        'username': 'alice',
        'server': 'heavensbride',
        'is_admin': true,
      });
      expect(u.username, 'alice');
      expect(u.server, 'heavensbride');
      expect(u.isAdmin, true);
      expect(u.toJson(), {
        'username': 'alice',
        'server': 'heavensbride',
        'is_admin': true,
      });
    });

    test('缺欄位採安全預設', () {
      final u = AuthUser.fromJson({});
      expect(u.username, '');
      expect(u.server, '');
      expect(u.isAdmin, false);
    });
  });

  group('Api 帶 token', () {
    test('請求帶 Authorization: Bearer', () async {
      String? seenAuth;
      final client = MockClient((req) async {
        seenAuth = req.headers['Authorization'];
        return http.Response(jsonEncode([]), 200);
      });
      final api = Api(baseUrl: 'https://x', client: client, token: 'tok123');
      await api.fetchArticles();
      expect(seenAuth, 'Bearer tok123');
    });

    test('401 丟 UnauthorizedException', () async {
      final client = MockClient((req) async => http.Response('unauth', 401));
      final api = Api(baseUrl: 'https://x', client: client, token: 'bad');
      expect(
        () => api.fetchArticles(),
        throwsA(isA<UnauthorizedException>()),
      );
    });
  });

  group('AuthService.login', () {
    test('成功回傳身分並翻 loggedIn 旗標', () async {
      final client = MockClient((req) async {
        expect(req.url.path, '/api/login');
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        expect(body['server'], 'tcgm');
        expect(body['username'], 'bob');
        expect(body['password'], 'pw');
        return http.Response(
          jsonEncode({
            'token': 'signed-token',
            'username': 'bob',
            'server': 'tcgm',
            'is_admin': false,
          }),
          200,
        );
      });
      AuthService.loggedIn.value = false;
      final auth = AuthService(baseUrl: 'https://x', client: client);
      final user = await auth.login('tcgm', 'bob', 'pw');
      expect(user.username, 'bob');
      expect(user.isAdmin, false);
      expect(AuthService.loggedIn.value, true);
    });

    test('401 丟帳密錯誤', () async {
      final client =
          MockClient((req) async => http.Response('{"detail":"x"}', 401));
      final auth = AuthService(baseUrl: 'https://x', client: client);
      expect(
        () => auth.login('tcgm', 'bob', 'wrong'),
        throwsA(isA<AuthException>()),
      );
    });

    test('400 丟來源不支援', () async {
      final client = MockClient((req) async => http.Response('{}', 400));
      final auth = AuthService(baseUrl: 'https://x', client: client);
      expect(
        () => auth.login('facebook', 'bob', 'pw'),
        throwsA(isA<AuthException>()),
      );
    });
  });
}
