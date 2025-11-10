from streamlit_javascript import st_javascript
import streamlit as st

COOKIE_NAME = "tg_login_token"

def set_login_cookie(token: str):
    st_javascript(f"""
        document.cookie = "{COOKIE_NAME}={token}; path=/; max-age=31536000";
    """)

def get_login_cookie():
    js_code = """
        const cookies = document.cookie.split(';').map(c => c.trim());
        const token = cookies.find(c => c.startsWith('tg_login_token='));
        if (token) {
            return token.split('=')[1];
        } else {
            return null;
        }
    """
    return st_javascript(js_code)