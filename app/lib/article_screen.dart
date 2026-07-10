import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'models.dart';

/// 文章詳情：抓 /api/articles/{slug} 全文，以 Markdown 呈現。
///
/// [preview] 為列表帶入的部分資料，讓標題/封面先顯示，內文載入中不空白。
class ArticleScreen extends StatefulWidget {
  final String slug;
  final Article? preview;
  const ArticleScreen({super.key, required this.slug, this.preview});

  @override
  State<ArticleScreen> createState() => _ArticleScreenState();
}

class _ArticleScreenState extends State<ArticleScreen> {
  final _api = Api();
  late Future<Article> _future;

  @override
  void initState() {
    super.initState();
    _future = _api.fetchArticle(widget.slug);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.preview?.title ?? '聖靈故事'),
      ),
      body: FutureBuilder<Article>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('${snap.error}', textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => setState(
                          () => _future = _api.fetchArticle(widget.slug)),
                      child: const Text('重試'),
                    ),
                  ],
                ),
              ),
            );
          }
          final a = snap.data!;
          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(a.title,
                    style: Theme.of(context).textTheme.headlineSmall),
                if (a.publishedAt != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    a.publishedAt!.split('T').first,
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: Theme.of(context).colorScheme.outline),
                  ),
                ],
                const SizedBox(height: 16),
                MarkdownBody(
                  data: a.body ?? (a.excerpt ?? ''),
                  onTapLink: (text, href, title) {
                    if (href != null) {
                      launchUrl(Uri.parse(href),
                          mode: LaunchMode.externalApplication);
                    }
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
