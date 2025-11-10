import os
from datetime import datetime
import hashlib
import datetime
import random
from streamlit_telegram_login import TelegramLoginWidgetComponent

from database.lessons_crud import *

import streamlit as st
import streamlit.components.v1 as components

from database.database import SessionLocal, init_db
from database.users_crud import get_user_by_nick, create_user, update_user
from utils.auth import set_persistent_login_token
from dotenv import load_dotenv

load_dotenv()

BOT_USERNAME = os.getenv("BOT_USERNAME")
BOT_TOKEN = os.getenv("BOT_TOKEN")

def render_editable_iframe(html_content, height=700):
    iframe_html = f"""
    <html>
      <head>
        <style>
          body {{
            margin: 0;
            padding: 1rem;
            font-family: comfortaa; 
          }}
        </style>
      </head>
      <body contenteditable="true">
        {html_content}
        <script>
          document.designMode = "on";
        </script>
      </body>
    </html>
    """
    components.html(iframe_html, height=height, scrolling=True)

def render_sidebar():
    st.sidebar.header("Сохраненные уроки")

    # Получаем все уроки текущего пользователя
    db = SessionLocal()
    try:
        user_id = st.session_state.user_id
        lessons = list_lessons_by_author_id(db, user_id)
    finally:
        db.close()

    if not lessons:
        st.sidebar.info("Пока нет сохраненных уроков.")
        return

    # Отображаем каждую запись с кнопками загрузки и удаления
    for lesson in lessons:
        st.sidebar.markdown(f"**{lesson.title}**")

        cols = st.sidebar.columns(2)
        with cols[0]:  # Кнопка загрузки
            if st.button("Загрузить", key=f"load_{lesson.id}"):
                try:
                    raw = s3_client.get_object(lesson.s3_key)
                    html = raw.decode("utf-8", errors="replace")

                    st.session_state.generated_lesson = html
                    st.session_state.current_lesson = {
                        "content": html,
                        "prompt": lesson.creation_prompt,
                        "selected_template": lesson.template.title if lesson.template else None,
                        "db_id": lesson.id
                    }
                    st.session_state.nav_option = "Generate Lesson"
                    st.rerun()
                    # Сохраняем загруженный урок в сессии
                    st.session_state.current_lesson = {
                        "content": html,
                        "prompt": lesson.creation_prompt,
                        "selected_template": lesson.template.title if lesson.template else None,
                        "db_id": lesson.id
                    }
                    st.session_state.nav_option = "Generate Lesson"
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Ошибка при загрузке: {e}")

        with cols[1]:  # Кнопка удаления
            if st.button("Удалить", key=f"delete_{lesson.id}"):
                db2 = SessionLocal()
                try:
                    delete_lesson_with_s3(db2, lesson.id)
                finally:
                    db2.close()
                st.sidebar.success(f"Урок \"{lesson.title}\" удалён")
                st.rerun()


def render_navigation():
    st.markdown(
        """
        <style>
            .nav-header {
                background-color: #f5f5f5;
                padding: 1rem;
                margin-bottom: 1.5rem;
                text-align: center;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            }
            .nav-button {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 1.2rem;
                margin: 0 1rem;
                padding: 0.5rem 1rem;
                transition: background 0.3s, color 0.3s;
            }
            .nav-button:hover {
                background-color: #e0e0e0;
            }
            .active-nav {
                font-weight: bold;
                color: #007BFF;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="nav-header">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Шаблоны", key="nav_sample"):
            st.session_state.nav_option = "Generate Style Sample"
            st.rerun()

    with col2:
        if st.button("Уроки", key="nav_lesson"):
            st.session_state.nav_option = "Generate Lesson"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def render_login_page():
    telegram_login = TelegramLoginWidgetComponent(
        bot_username=BOT_USERNAME,
        secret_key=BOT_TOKEN
    )
    auth_data = telegram_login.button

    if auth_data:
        st.success("Успешная авторизация!")
        telegram_id = auth_data.get("id")
        telegram_nick = auth_data.get("username") or auth_data.get("first_name")

        db = SessionLocal()
        user = get_user_by_nick(db, telegram_nick)

        if user:
            update_user(db, user.id, last_online=datetime.datetime.utcnow())
            st.success(f"Рады снова вас видеть, {user.telegram_nick}!")
        else:
            random_password = str(random.randint(100000, 999999))
            password_hash = hashlib.sha256(random_password.encode()).hexdigest()
            user = create_user(db, telegram_nick, telegram_id, password_hash)
            st.success(f"Выполнен вход как {user.telegram_nick}!")

        st.session_state.user_id = user.id
        # 🌟 Save token for persistent login
        set_persistent_login_token(user.telegram_id)
        