"""Never capture sensitive apps, even when a user enables window previews."""
NEVER_SNAPSHOT = frozenset({'com.apple.MobileSMS', 'com.apple.mail', 'com.apple.Passwords',
    'com.apple.keychainaccess', 'com.agilebits.onepassword7', 'com.1password.1password',
    'org.whispersystems.signal-desktop', 'net.whatsapp.WhatsApp', 'com.tinyspeck.slackmacgap'})

def private_context(info, excluded):
    return (info.get('bundle') in NEVER_SNAPSHOT
        or any(app.get('bundle') == info.get('bundle') for app in excluded)
        or any(word in info.get('title','').lower() for word in ('incognito','private browsing','inprivate')))
