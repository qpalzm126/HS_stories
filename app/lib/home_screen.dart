import 'dart:async';

import 'package:flutter/material.dart';

import 'api.dart';
import 'article_screen.dart';
import 'models.dart';
import 'theme.dart';
import 'widget_service.dart';

/// 首頁：標語 + 關鍵字搜尋 + 故事列表（最新一篇做成 hero）。
/// 下拉可重整並同步更新 widget。
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = Api();
  final _searchCtrl = TextEditingController();
  Timer? _debounce;
  String _q = ''; // 已套用的關鍵字
  String _sort = 'published_desc'; // 排序：最新在前 / 最舊在前（對齊後端白名單）
  late Future<List<Article>> _future;

  @override
  void initState() {
    super.initState();
    _future = _api.fetchArticles();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  // 上限 200：對齊後端 limit 的 le 上限，且 > 全站文章數，搜尋能抓齊符合的。
  Future<List<Article>> _load() =>
      _api.fetchArticles(q: _q.isEmpty ? null : _q, limit: 200, sort: _sort);

  // 切換排序（最新在前 ⇄ 最舊在前）並重載。
  void _toggleSort() {
    setState(() {
      _sort = _sort == 'published_desc' ? 'published_asc' : 'published_desc';
      _future = _load();
    });
  }

  // 打字時 debounce，避免每個字都打 API（對齊 web）。
  void _onQueryChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () {
      final next = value.trim();
      if (next == _q) return;
      setState(() {
        _q = next;
        _future = _load();
      });
    });
  }

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _future = next);
    await next;
    // 順手把 widget 也更新成最新。
    updateHomeWidget(api: _api).catchError((_) {});
  }

  void _open(Article a) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => ArticleScreen(slug: a.slug, preview: a)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('聖靈故事')),
      body: Column(
        children: [
          const SizedBox(height: 6),
          _SearchField(controller: _searchCtrl, onChanged: _onQueryChanged),
          _SortBar(sort: _sort, onToggle: _toggleSort),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refresh,
              child: FutureBuilder<List<Article>>(
                future: _future,
                builder: (context, snap) {
                  if (snap.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  if (snap.hasError) {
                    return _ErrorView(message: '${snap.error}', onRetry: _refresh);
                  }
                  final items = snap.data ?? const <Article>[];
                  if (items.isEmpty) return _EmptyView(query: _q);
                  return _ArticleList(
                    items: items,
                    query: _q,
                    onOpen: _open,
                    // 只有「最新在前」時才把第一篇做成「最新」hero。
                    heroEnabled: _sort == 'published_desc',
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SearchField extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  const _SearchField({required this.controller, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final p = Palette.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: TextField(
        controller: controller,
        onChanged: onChanged,
        textInputAction: TextInputAction.search,
        style: TextStyle(color: p.text, fontSize: 15),
        decoration: InputDecoration(
          hintText: '搜尋標題或內文關鍵字…',
          hintStyle: TextStyle(color: p.muted),
          prefixIcon: Icon(Icons.search, color: p.muted, size: 20),
          isDense: true,
          filled: true,
          fillColor: p.panel,
          contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(999),
            borderSide: BorderSide(color: p.border),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(999),
            borderSide: BorderSide(color: p.accent, width: 1.4),
          ),
        ),
      ),
    );
  }
}

/// 排序切換列：右對齊，一鍵在「最新在前 / 最舊在前」間切換。
class _SortBar extends StatelessWidget {
  final String sort;
  final VoidCallback onToggle;
  const _SortBar({required this.sort, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final p = Palette.of(context);
    final isDesc = sort == 'published_desc';
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Align(
        alignment: Alignment.centerRight,
        child: TextButton.icon(
          onPressed: onToggle,
          icon: Icon(Icons.swap_vert, size: 18, color: p.muted),
          label: Text(
            isDesc ? '最新在前' : '最舊在前',
            style: TextStyle(color: p.text, fontSize: 13),
          ),
          style: TextButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
      ),
    );
  }
}

class _ArticleList extends StatelessWidget {
  final List<Article> items;
  final String query;
  final ValueChanged<Article> onOpen;
  final bool heroEnabled;
  const _ArticleList(
      {required this.items,
      required this.query,
      required this.onOpen,
      this.heroEnabled = true});

  @override
  Widget build(BuildContext context) {
    final searching = query.isNotEmpty;
    final header = searching ? 1 : 0;
    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 2, 16, 28),
      itemCount: items.length + header,
      itemBuilder: (context, idx) {
        if (searching && idx == 0) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 12, top: 2),
            child: Text('找到 ${items.length} 篇含「$query」的文章',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Palette.of(context).muted)),
          );
        }
        final i = idx - header;
        final a = items[i];
        return Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: _ArticleCard(
            article: a,
            hero: heroEnabled && !searching && i == 0,
            onTap: () => onOpen(a),
          ),
        );
      },
    );
  }
}

class _ArticleCard extends StatelessWidget {
  final Article article;
  final bool hero;
  final VoidCallback onTap;
  const _ArticleCard(
      {required this.article, required this.onTap, this.hero = false});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final p = Palette.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final radius = hero ? 18.0 : 14.0;
    final hasCover =
        article.coverUrl != null && article.coverUrl!.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        color: p.panel,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: p.border),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: const Color(0x0F000000),
                  blurRadius: hero ? 16 : 8,
                  offset: const Offset(0, 3),
                ),
              ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (hasCover)
                Stack(
                  children: [
                    AspectRatio(
                      aspectRatio: hero ? 3 / 2 : 16 / 9,
                      child: _CoverImage(url: article.coverUrl!, chip: p.chip),
                    ),
                    if (hero)
                      Positioned(
                        left: 12,
                        top: 12,
                        child: _Pill(color: p.accent, text: '最新'),
                      ),
                  ],
                ),
              Padding(
                padding: EdgeInsets.all(hero ? 18 : 15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (hero && !hasCover) ...[
                      _Pill(color: p.accent, text: '最新'),
                      const SizedBox(height: 10),
                    ],
                    Text(
                      article.title,
                      style: (hero
                              ? theme.textTheme.titleLarge
                              : theme.textTheme.titleMedium)
                          ?.copyWith(fontWeight: FontWeight.w700, height: 1.3),
                    ),
                    if (article.excerpt != null &&
                        article.excerpt!.isNotEmpty) ...[
                      const SizedBox(height: 7),
                      Text(
                        article.excerpt!,
                        maxLines: hero ? 3 : 2,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.bodyMedium
                            ?.copyWith(color: p.muted, height: 1.55),
                      ),
                    ],
                    if (article.publishedAt != null) ...[
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Icon(Icons.schedule, size: 13, color: p.muted),
                          const SizedBox(width: 5),
                          Text(
                            _fmtDate(article.publishedAt!),
                            style: theme.textTheme.labelSmall
                                ?.copyWith(color: p.muted),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 封面圖：載入中顯示淡底、載入失敗則收合（不留破圖）。
class _CoverImage extends StatelessWidget {
  final String url;
  final Color chip;
  const _CoverImage({required this.url, required this.chip});

  @override
  Widget build(BuildContext context) {
    return Image.network(
      url,
      fit: BoxFit.cover,
      loadingBuilder: (context, child, progress) =>
          progress == null ? child : Container(color: chip),
      errorBuilder: (_, __, ___) => const SizedBox.shrink(),
    );
  }
}

class _Pill extends StatelessWidget {
  final Color color;
  final String text;
  const _Pill({required this.color, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(text,
          style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 1)),
    );
  }
}

String _fmtDate(String iso) {
  final dt = DateTime.tryParse(iso);
  if (dt == null) return iso;
  final l = dt.toLocal();
  return '${l.year}/${l.month.toString().padLeft(2, '0')}/${l.day.toString().padLeft(2, '0')}';
}

class _EmptyView extends StatelessWidget {
  final String query;
  const _EmptyView({this.query = ''});
  @override
  Widget build(BuildContext context) {
    final msg = query.isEmpty
        ? '還沒有已發佈的故事'
        : '找不到含「$query」的文章';
    return ListView(
      children: [
        const SizedBox(height: 120),
        Center(
          child: Text(msg,
              style: TextStyle(color: Palette.of(context).muted)),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});
  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 100),
        Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const Icon(Icons.cloud_off, size: 48),
                const SizedBox(height: 12),
                Text(message, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                FilledButton(onPressed: onRetry, child: const Text('重試')),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
