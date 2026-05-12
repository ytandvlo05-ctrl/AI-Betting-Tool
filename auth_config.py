import streamlit_authenticator as stauth

# 1. Definiujemy dane użytkowników z "czystymi" hasłami
config = {
    "credentials": {
        "usernames": {
            "admin": {
                "name": "Admin",
                "password": "admin123"
            },
            "tester": {
                "name": "Tester",
                "password": "start123"
            }
        }
    },
    "cookie": {
        "expiry_days": 30,
        "key": "some_signature_key",
        "name": "betting_center_cookie"
    }
}

# 2. MAGIA: Przesyłamy CAŁY słownik 'credentials' do zahaszowania.
# Biblioteka sama znajdzie hasła i zamieni je na bezpieczne kody.
stauth.Hasher.hash_passwords(config['credentials'])