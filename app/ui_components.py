import base64
import hashlib
import os
import random
import textwrap
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from database.database import SessionLocal
from database.lessons_crud import delete_lesson_with_s3, list_lessons_by_author_id
from database.users_crud import create_user, get_user_by_nick, update_user
from dotenv import load_dotenv
from streamlit_telegram_login import TelegramLoginWidgetComponent
from utils.auth import set_persistent_login_token

# s3_client у вас, судя по всему, где-то глобально определён.
# Чтобы файл не падал импортом, делаем мягкую попытку.
try:
    from database.lessons_crud import s3_client  # type: ignore
except Exception:
    s3_client = None

load_dotenv()
BOT_USERNAME = os.getenv("BOT_USERNAME")
BOT_TOKEN = os.getenv("BOT_TOKEN")


def render_editable_iframe(html_content: str, height: int = 700) -> None:
    iframe_html = f"""
    <html>
      <head>
        <style>
          body {{
            margin: 0;
            padding: 1rem;
            font-family: comfortaa, sans-serif;
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


def render_sidebar() -> None:
    st.sidebar.header("Сохраненные уроки")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.sidebar.info("Войдите, чтобы увидеть сохраненные уроки.")
        return

    db = SessionLocal()
    try:
        lessons = list_lessons_by_author_id(db, user_id)
    finally:
        db.close()

    if not lessons:
        st.sidebar.info("Пока нет сохраненных уроков.")
        return

    if s3_client is None:
        st.sidebar.warning(
            "S3-клиент не инициализирован: загрузка HTML из S3 недоступна."
        )
        return

    for lesson in lessons:
        st.sidebar.markdown(f"**{lesson.title}**")

        col_load, col_del = st.sidebar.columns(2)

        with col_load:
            if st.button("Загрузить", key=f"load_{lesson.id}"):
                try:
                    raw = s3_client.get_object(lesson.s3_key)
                    html = raw.decode("utf-8", errors="replace")

                    st.session_state.generated_lesson = html
                    st.session_state.current_lesson = {
                        "content": html,
                        "prompt": lesson.creation_prompt,
                        "selected_template": lesson.template.title
                        if lesson.template
                        else None,
                        "db_id": lesson.id,
                    }
                    st.session_state.nav_option = "Generate Lesson"
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Ошибка при загрузке: {e}")

        with col_del:
            if st.button("Удалить", key=f"delete_{lesson.id}"):
                db2 = SessionLocal()
                try:
                    delete_lesson_with_s3(db2, lesson.id)
                finally:
                    db2.close()
                st.sidebar.success(f'Урок "{lesson.title}" удалён')
                st.rerun()


def render_navigation() -> None:
    st.markdown(
        """
        <style>
          .nav-wrap {
            background: rgba(0,0,0,0.03);
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 14px;
            padding: 0.75rem 1rem;
            margin: 0.25rem 0 1rem 0;
          }
          /* Чуть улучшаем вид horizontal radio */
          div[data-testid="stRadio"] > div {
            gap: 0.75rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)

    current = st.session_state.get("nav_option", "Generate Style Sample")
    current_label = "Шаблоны" if current == "Generate Style Sample" else "Уроки"

    choice = st.radio(
        "Навигация",
        ["Шаблоны", "Уроки"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if current_label == "Шаблоны" else 1,
        key="nav_radio_choice",
    )

    st.session_state.nav_option = (
        "Generate Style Sample" if choice == "Шаблоны" else "Generate Lesson"
    )

    st.markdown("</div>", unsafe_allow_html=True)


def inject_login_css() -> None:
    st.markdown(
        """
        <style>
          /* Логин в палитре основного сайта */
          .stApp {
            background:
              radial-gradient(900px 600px at 12% 12%, rgba(239,142,35,0.14) 0%, rgba(239,142,35,0.00) 60%),
              linear-gradient(180deg, #FAF7F5 0%, #FAF1E8 100%);
          }

          /* Возвращаем привычный отступ */
          .block-container { padding-top: 2rem !important; }

          /* Карточка логина (container(border=True)) — светлая, как в основной теме */
          div[data-testid="stContainer"] {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(77,77,77,0.12) !important;
            border-radius: 20px;
            padding: 34px 34px 26px 34px;
            backdrop-filter: blur(8px);
            box-shadow: 0 18px 55px rgba(14, 20, 40, 0.12);
          }

          .login-title, .login-subtitle, .login-hint { text-align: center; }

          .login-title {
            margin: 0 0 8px 0;
            font-size: 36px;
            font-weight: 780;
            color: #4d4d4d;
            letter-spacing: 0.2px;
          }

          .login-subtitle {
            margin: 0 auto 18px auto;
            max-width: 52ch;
            color: rgba(77,77,77,0.72);
            font-size: 15px;
            line-height: 1.55;
          }

          .login-hint {
            margin-top: 18px;
            color: rgba(77,77,77,0.55);
            font-size: 12px;
          }

          div[data-testid="stContainer"] iframe {
            display: block;
            margin: 10px auto 6px auto;
          }

          div[data-testid="stContainer"] > div {
            gap: 0.25rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login_page() -> None:
    inject_login_css()

    # Центруем карточку на широком layout через колонки [web:44]
    left, mid, right = st.columns([1, 1.35, 1])
    auth_data = None

    with mid:
        with st.container(border=True):
            st.markdown(
                '<div class="login-title">Вход в <span style="color:#EF8E23">kursorlab</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="login-subtitle">Авторизуйтесь через Telegram, чтобы продолжить.</div>',
                unsafe_allow_html=True,
            )

            if not BOT_USERNAME or not BOT_TOKEN:
                st.error("Не заданы BOT_USERNAME / BOT_TOKEN в переменных окружения.")
                return

            # Важно: не сужаем кнопку доп. колонками — иначе она выглядит “полосой”
            # Органичность делаем параметрами виджета (medium, без userpic, с radius) [page:0]
            telegram_login = TelegramLoginWidgetComponent(
                bot_username=BOT_USERNAME,
                secret_key=BOT_TOKEN,
                button_style="medium",
                userpic=False,
                corner_radius=14,
                request_access=True,
            )
            auth_data = telegram_login.button

            st.markdown(
                '<div class="login-hint">Мы не спрашиваем пароль — вход подтверждается вашим аккаунтом Telegram.</div>',
                unsafe_allow_html=True,
            )

    if not auth_data:
        return

    st.success("Успешная авторизация!")
    telegram_id = auth_data.get("id")
    telegram_nick = (
        auth_data.get("username")
        or auth_data.get("first_name")
        or (f"user_{telegram_id}" if telegram_id else None)
    )

    if not telegram_id or not telegram_nick:
        st.error("Не удалось получить данные Telegram (id/username).")
        return

    db = SessionLocal()
    try:
        user = get_user_by_nick(db, telegram_nick)

        if user:
            update_user(db, user.id, last_online=datetime.utcnow())
            st.success(f"Рады снова вас видеть, {user.telegram_nick}!")
        else:
            random_password = str(random.randint(100000, 999999))
            password_hash = hashlib.sha256(random_password.encode()).hexdigest()
            user = create_user(db, telegram_nick, telegram_id, password_hash)
            st.success(f"Выполнен вход как {user.telegram_nick}!")

        st.session_state.user_id = user.id
        set_persistent_login_token(user.telegram_id)
        st.rerun()
    finally:
        db.close()


def render_global_footer(
    contacts_text: str,
    logo_path: str,
    logo_link: str | None = None,
):
    # Нормализуем путь: абсолютный или относительный от папки /app (где лежит этот файл)
    p = Path(logo_path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parent / p).resolve()

    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = p.suffix.lower()
    mime = "image/svg+xml" if ext == ".svg" else "image/png"
    logo_src = f"data:{mime};base64,{b64}"

    # Контакты: переносы строк -> <br>, чтобы не зависеть от CSS white-space
    contacts_html = "<br>".join((contacts_text or "").splitlines())

    disclaimer_html = (
        "Демо-версия: при текущих доступных ресурсах генерация занимает "
        "от 30 секунд до 5 минут."
    )

    html = f"""
    <style>
      /* чтобы контент не уезжал под фиксированный футер */
      .block-container {{
        padding-bottom: 6.5rem !important;
      }}

      .app-footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        z-index: 99999;

        background: rgba(10, 14, 25, 0.72);
        border-top: 1px solid rgba(255,255,255,0.10);
        backdrop-filter: blur(10px);
      }}

      .app-footer__inner {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 12px 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        flex-wrap: wrap; /* чтобы на узких экранах не ломалось */
      }}

      .app-footer__disclaimer {{
        color: rgba(255,255,255,0.82);
        font-size: 12px;
        line-height: 1.35;
        white-space: normal;
      }}

      .app-footer__contacts {{
        color: rgba(255,255,255,0.72);
        font-size: 12px;
        line-height: 1.35;
      }}

      .app-footer__logo img {{
        height: 28px;
        width: auto;
        opacity: 0.92;
        display: block;
      }}

      .app-footer a {{
        color: rgba(180, 215, 255, 0.92);
        text-decoration: none;
      }}
      .app-footer a:hover {{
        text-decoration: underline;
      }}
    </style>

    <div class="app-footer">
      <div class="app-footer__inner">
        <div class="app-footer__disclaimer">{disclaimer_html}</div>
        <div class="app-footer__contacts">{contacts_html}</div>
        <div class="app-footer__logo">
          {"<a href='" + logo_link + "' target='_blank' rel='noopener'>" if logo_link else ""}
            <img src="{logo_src}" alt="Grant Foundation logo" />
          {"</a>" if logo_link else ""}
        </div>
      </div>
    </div>
    """

    st.markdown(textwrap.dedent(html), unsafe_allow_html=True)
