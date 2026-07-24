import 'package:flutter/material.dart';

import 'auth_service.dart';
import 'theme.dart';
import 'widget_service.dart';

/// 全站登入畫面：選登入來源（HeavensBride / TCGM）+ 論壇帳密。
/// 登入成功後 [AuthService.loggedIn] 翻為 true，根畫面切到首頁。
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const _servers = [
    ('heavensbride', 'HeavensBride'),
    ('tcgm', 'TCGM'),
  ];

  final _auth = AuthService();
  final _userCtrl = TextEditingController();
  final _pwCtrl = TextEditingController();
  String _server = 'heavensbride';
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _userCtrl.dispose();
    _pwCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final username = _userCtrl.text.trim();
    final password = _pwCtrl.text;
    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = '請輸入帳號與密碼');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _auth.login(_server, username, password);
      // 登入後順手更新 widget（帶新 token），失敗不擋。
      updateHomeWidget().catchError((_) {});
      // 畫面切換由根層監聽 AuthService.loggedIn 處理。
    } on AuthException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) setState(() => _error = '登入失敗：$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = Palette.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 360),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    '聖靈故事',
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '請用論壇帳密登入',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: p.muted, fontSize: 13),
                  ),
                  const SizedBox(height: 22),
                  _ServerSelector(
                    servers: _servers,
                    selected: _server,
                    onChanged: _busy
                        ? null
                        : (v) => setState(() => _server = v),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _userCtrl,
                    enabled: !_busy,
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.username],
                    decoration: _dec(p, '帳號', Icons.person_outline),
                    style: TextStyle(color: p.text),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _pwCtrl,
                    enabled: !_busy,
                    obscureText: true,
                    textInputAction: TextInputAction.done,
                    autofillHints: const [AutofillHints.password],
                    onSubmitted: (_) => _busy ? null : _submit(),
                    decoration: _dec(p, '密碼', Icons.lock_outline),
                    style: TextStyle(color: p.text),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      style: const TextStyle(color: Color(0xFFC0392B), fontSize: 13),
                    ),
                  ],
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: _busy ? null : _submit,
                    style: FilledButton.styleFrom(
                      backgroundColor: p.accent,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: _busy
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('登入'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _dec(Palette p, String hint, IconData icon) => InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: p.muted),
        prefixIcon: Icon(icon, color: p.muted, size: 20),
        isDense: true,
        filled: true,
        fillColor: p.panel,
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: p.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: p.accent, width: 1.4),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: p.border),
        ),
      );
}

/// 登入來源單選（分段按鈕外觀）。
class _ServerSelector extends StatelessWidget {
  final List<(String, String)> servers;
  final String selected;
  final ValueChanged<String>? onChanged;
  const _ServerSelector({
    required this.servers,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final p = Palette.of(context);
    return Row(
      children: [
        for (final s in servers)
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(right: s == servers.last ? 0 : 8),
              child: _serverChip(p, s.$1, s.$2),
            ),
          ),
      ],
    );
  }

  Widget _serverChip(Palette p, String value, String label) {
    final active = value == selected;
    return InkWell(
      onTap: onChanged == null ? null : () => onChanged!(value),
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 11),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: active ? p.chip : p.panel,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: active ? p.accent : p.border,
            width: active ? 1.4 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? p.accentText : p.text,
            fontWeight: active ? FontWeight.w700 : FontWeight.w500,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}
