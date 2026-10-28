import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../components/screen_chrome.dart';
import '../components/account_fields.dart';
import '../components/account_hero.dart';
import '../components/account_submit.dart';
import '../components/account_options.dart';
import '../components/account_switch.dart';
import '../services/account_access.dart';
import '../services/pico_store.dart';
import '../theme/app_theme.dart';
import 'password_reset_screen.dart';

class AccountScreen extends StatefulWidget {
  const AccountScreen({super.key, required this.store, this.firstRun = false});
  final PicoStore store;
  final bool firstRun;
  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _signUp = false, _busy = false;
  late bool _remember = widget.store.preferences.getBool('remember_me') ?? true;
  String? _message;
  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _rememberChanged(bool value) async {
    setState(() => _remember = value);
    await widget.store.preferences.setBool('remember_me', value);
    if (!value) {
      await RememberedSessionStorage(widget.store.preferences)
          .removePersistedSession();
    }
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
      await _rememberChanged(_remember);
      if (_signUp) {
        final result = await widget.store.client!.auth.signUp(
          email: _email.text.trim(),
          password: _password.text,
        );
        if (mounted && result.session == null) {
          setState(
            () => _message = 'Check your email to confirm your account.',
          );
        }
      } else {
        await widget.store.client!.auth.signInWithPassword(
          email: _email.text.trim(),
          password: _password.text,
        );
      }
      if (mounted && widget.store.signedIn && !widget.firstRun) {
        Navigator.pop(context);
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

  @override
  Widget build(BuildContext context) {
    final compact =
        MediaQuery.viewInsetsOf(context).bottom > 0 ||
        MediaQuery.sizeOf(context).height < 600;
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            LayoutBuilder(
              builder: (context, constraints) => SingleChildScrollView(
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                padding: EdgeInsets.fromLTRB(
                  12,
                  widget.firstRun ? 14 : 64,
                  12,
                  16,
                ),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Column(
                      children: [
                        // Brand identity.
                        AccountHero(compact: compact, signUp: _signUp),
                        SizedBox(height: compact ? 18 : 24),
                        // Middle: the complete form and everyday account controls.
                        Form(
                          key: _form,
                          child: Column(
                            children: [
                              AccountFields(
                                email: _email,
                                password: _password,
                                signUp: _signUp,
                                enabled: !_busy,
                                onSubmit: _submit,
                              ),
                              AccountOptions(
                                remember: _remember,
                                enabled: !_busy,
                                onRemember: _rememberChanged,
                                onForgot: () => Navigator.push(
                                  context,
                                  MaterialPageRoute<void>(
                                    builder: (_) => PasswordResetScreen(
                                      store: widget.store,
                                      email: _email.text.trim(),
                                    ),
                                  ),
                                ),
                              ),
                              if (_message != null)
                                Padding(
                                  padding: const EdgeInsets.fromLTRB(
                                    12,
                                    0,
                                    12,
                                    12,
                                  ),
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
                              AccountSubmit(
                                label: _signUp ? 'Create account' : 'Sign in',
                                busy: _busy,
                                onSubmit: _submit,
                              ),
                            ],
                          ),
                        ),
                        SizedBox(height: compact ? 22 : 30),
                        // Account-mode switching.
                        AccountSwitch(
                          signUp: _signUp,
                          onToggle: () {
                            if (!_busy) {
                              setState(() {
                                _signUp = !_signUp;
                                _message = null;
                              });
                            }
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            if (!widget.firstRun)
              Positioned(
                top: 8,
                left: 12,
                child: CircleControl(
                  icon: HeroIcons.chevronLeft,
                  label: 'Back',
                  onTap: () => Navigator.pop(context),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
