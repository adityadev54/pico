import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../components/capsule_input.dart';
import '../components/account_submit.dart';
import '../components/screen_chrome.dart';
import '../services/config.dart';
import '../services/pico_store.dart';
import '../theme/app_theme.dart';

class PasswordResetScreen extends StatefulWidget {
  const PasswordResetScreen({
    super.key,
    required this.store,
    this.email = '',
    this.recovery = false,
  });
  final PicoStore store;
  final String email;
  final bool recovery;
  @override
  State<PasswordResetScreen> createState() => _PasswordResetScreenState();
}

class _PasswordResetScreenState extends State<PasswordResetScreen> {
  final _form = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.email);
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _message;
  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    if (widget.store.client == null) {
      setState(
        () => _message = 'Account service is not configured for this build.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      if (widget.recovery) {
        await widget.store.client!.auth.updateUser(
          UserAttributes(password: _password.text),
        );
        widget.store.completeRecovery();
      } else {
        await widget.store.client!.auth.resetPasswordForEmail(
          _email.text.trim(),
          redirectTo: Config.authRedirect,
        );
        if (mounted) {
          setState(() => _message = 'Check your email for a reset link.');
        }
      }
    } on AuthException catch (e) {
      if (mounted) setState(() => _message = e.message);
    } catch (_) {
      if (mounted) {
        setState(() => _message = 'Couldn’t connect. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _back() async {
    if (widget.recovery) {
      await widget.store.client?.auth.signOut();
      widget.store.completeRecovery();
    } else if (mounted) {
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Stack(
        children: [
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(12, 80, 12, 28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Form(
                  key: _form,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 12, bottom: 24),
                        child: Text(
                          widget.recovery ? 'New password' : 'Reset password',
                          style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -.7,
                          ),
                        ),
                      ),
                      if (!widget.recovery)
                        CapsuleInput(
                          controller: _email,
                          hint: 'Email',
                          icon: HeroIcons.envelope,
                          keyboardType: TextInputType.emailAddress,
                          enabled: !_busy,
                          validator: (v) =>
                              v != null &&
                                  RegExp(r'^\S+@\S+\.\S+$').hasMatch(v.trim())
                              ? null
                              : 'Enter a valid email',
                        ),
                      if (widget.recovery) ...[
                        CapsuleInput(
                          controller: _password,
                          hint: 'New password',
                          icon: HeroIcons.lockClosed,
                          obscure: true,
                          enabled: !_busy,
                          validator: (v) => (v?.length ?? 0) >= 8
                              ? null
                              : 'Use at least 8 characters',
                        ),
                        const SizedBox(height: 10),
                        CapsuleInput(
                          controller: _confirm,
                          hint: 'Confirm password',
                          icon: HeroIcons.lockClosed,
                          obscure: true,
                          enabled: !_busy,
                          validator: (v) => v == _password.text
                              ? null
                              : 'Passwords don’t match',
                        ),
                      ],
                      if (_message != null)
                        Padding(
                          padding: const EdgeInsets.all(12),
                          child: Semantics(
                            liveRegion: true,
                            child: Text(
                              _message!,
                              style: const TextStyle(
                                fontSize: 13,
                                color: PicoTheme.accent,
                              ),
                            ),
                          ),
                        ),
                      const SizedBox(height: 16),
                      AccountSubmit(
                        label: widget.recovery
                            ? 'Save password'
                            : 'Send reset link',
                        busy: _busy,
                        onSubmit: _submit,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            top: 8,
            left: 12,
            child: CircleControl(
              icon: HeroIcons.chevronLeft,
              label: 'Back',
              onTap: _back,
            ),
          ),
        ],
      ),
    ),
  );
}
