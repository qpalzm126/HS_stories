/// 對應後端 `backend/articles.py::public_article` 的輸出。
///
/// 列表（/api/articles）沒有 body/tags；latest 與單篇（full=True）才有。
class Article {
  final String slug;
  final String title;
  final String? excerpt;
  final String? coverUrl;
  final String? publishedAt;

  /// 後端已組好的絕對網址（PUBLIC_BASE_URL + /article/{slug}）。
  final String? url;

  /// 完整內文（Markdown）；列表項目為 null。
  final String? body;
  final List<String> tags;

  const Article({
    required this.slug,
    required this.title,
    this.excerpt,
    this.coverUrl,
    this.publishedAt,
    this.url,
    this.body,
    this.tags = const [],
  });

  factory Article.fromJson(Map<String, dynamic> json) {
    final rawTags = json['tags'];
    return Article(
      slug: json['slug'] as String? ?? '',
      title: json['title'] as String? ?? '(無標題)',
      excerpt: json['excerpt'] as String?,
      coverUrl: json['cover_url'] as String?,
      publishedAt: json['published_at'] as String?,
      url: json['url'] as String?,
      body: json['body'] as String?,
      tags: rawTags is List
          ? rawTags.map((e) => e.toString()).toList()
          : const [],
    );
  }
}
