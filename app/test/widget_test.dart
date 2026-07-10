import 'package:flutter_test/flutter_test.dart';
import 'package:hs_story_app/models.dart';

void main() {
  group('Article.fromJson', () {
    test('列表項目（無 body/tags）', () {
      final a = Article.fromJson({
        'slug': 'my-story',
        'title': '一段見證',
        'excerpt': '摘錄…',
        'cover_url': null,
        'published_at': '2026-07-10T08:00:00',
        'url': 'https://example.com/article/my-story',
      });
      expect(a.slug, 'my-story');
      expect(a.title, '一段見證');
      expect(a.excerpt, '摘錄…');
      expect(a.url, 'https://example.com/article/my-story');
      expect(a.body, isNull);
      expect(a.tags, isEmpty);
    });

    test('單篇全文（含 body/tags）', () {
      final a = Article.fromJson({
        'slug': 'full',
        'title': '全文',
        'body': '# 標題\n內文',
        'tags': ['見證', '恩典'],
      });
      expect(a.body, '# 標題\n內文');
      expect(a.tags, ['見證', '恩典']);
    });

    test('缺欄位時採安全預設', () {
      final a = Article.fromJson({});
      expect(a.slug, '');
      expect(a.title, '(無標題)');
      expect(a.tags, isEmpty);
    });
  });
}
