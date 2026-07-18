import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'models.dart';
import 'theme.dart';

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
          final theme = Theme.of(context);
          final p = Palette.of(context);
          final cover = a.coverUrl ?? widget.preview?.coverUrl;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(a.title,
                    style: theme.textTheme.headlineSmall
                        ?.copyWith(fontWeight: FontWeight.w700, height: 1.35)),
                if (a.publishedAt != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(Icons.schedule, size: 14, color: p.muted),
                      const SizedBox(width: 5),
                      Text(
                        a.publishedAt!.split('T').first,
                        style:
                            theme.textTheme.labelMedium?.copyWith(color: p.muted),
                      ),
                    ],
                  ),
                ],
                if (cover != null && cover.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      cover,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                    ),
                  ),
                ],
                const SizedBox(height: 18),
                MarkdownBody(
                  data: a.body ?? (a.excerpt ?? ''),
                  // 單一換行也視為換行（對齊 web 的 marked breaks:true）。
                  softLineBreak: true,
                  styleSheet: _markdownStyle(theme, p),
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

/// 閱讀排版：對齊 web 的 .prose（段距、金色左邊框引言、連結色）。
MarkdownStyleSheet _markdownStyle(ThemeData theme, Palette p) {
  final body = theme.textTheme.bodyLarge
      ?.copyWith(fontSize: 17, height: 1.85, color: p.text);
  return MarkdownStyleSheet.fromTheme(theme).copyWith(
    p: body,
    pPadding: EdgeInsets.zero,
    blockSpacing: 14,
    h2: theme.textTheme.titleLarge
        ?.copyWith(fontWeight: FontWeight.w700, fontSize: 21, height: 1.4),
    h2Padding: const EdgeInsets.only(top: 14, bottom: 2),
    h3: theme.textTheme.titleMedium
        ?.copyWith(fontWeight: FontWeight.w700, fontSize: 18),
    h3Padding: const EdgeInsets.only(top: 10, bottom: 2),
    strong: const TextStyle(fontWeight: FontWeight.w700),
    a: TextStyle(color: p.accentText, decoration: TextDecoration.underline),
    listBullet: body,
    blockquote:
        body?.copyWith(fontSize: 16, height: 1.7, color: p.muted),
    blockquotePadding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
    blockquoteDecoration: BoxDecoration(
      color: p.chip,
      borderRadius: const BorderRadius.horizontal(right: Radius.circular(8)),
      border: Border(left: BorderSide(color: p.accent, width: 3)),
    ),
    horizontalRuleDecoration: BoxDecoration(
      border: Border(top: BorderSide(color: p.border, width: 1)),
    ),
  );
}
