import streamlit as st
import hashlib
from database.database import SessionLocal
from database.users_crud import get_user_by_telegram_id
from utils.cookies import set_login_cookie, get_login_cookie
PERSISTENT_KEY = "tg_user_token"

def set_persistent_login_token(telegram_id: int):
    token = hashlib.sha256(str(telegram_id).encode()).hexdigest()
    st.session_state[PERSISTENT_KEY] = token
    set_login_cookie(token)

def get_user_from_token():
    token = st.session_state.get(PERSISTENT_KEY)
    if not token:
        token = get_login_cookie()

    if not token:
        return None

    db = SessionLocal()
    users = db.query(get_user_by_telegram_id.__annotations__['return']).all()
    for user in users:
        expected_token = hashlib.sha256(str(user.telegram_id).encode()).hexdigest()
        if token == expected_token:
            return user
    return None