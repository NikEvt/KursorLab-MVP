import streamlit as st
from ui_components import render_editable_iframe
from logic import generate_style_sample, generate_lesson, pdf_upload
import asyncio
from database.database import SessionLocal
from database.templates_crud import create_template_with_s3, list_templates_by_author
from database.lessons_crud import create_lesson_with_s3
from database.s3.s3 import s3_client
import logging

logger = logging.getLogger(__name__)


def render_style_sample_page():
    col_input, col_preview = st.columns(2)

    with col_input:
        style_prompt = st.text_input("Внешний вид", placeholder="Цвет, шрифт, размер, фон…")
        structure_prompt = st.text_input("Структура", placeholder="Порядок изложения, разбиение на части…")

        if st.button("Создать шаблон"):
            # Set defaults
            if not style_prompt:
                style_prompt = "Строгий, шрифт comfortaa"
            if not structure_prompt:
                structure_prompt = "Введение, основная часть с bullet списком и заключение"

            # Generate HTML
            with st.spinner("Создаём шаблон…"):
                sample_html = generate_style_sample(style_prompt, structure_prompt)

            st.session_state.generated_sample = sample_html

            # Persist to DB
            db = SessionLocal()
            try:
                author_id = st.session_state.user_id
                existing = list_templates_by_author(db, author_id)
                title = f"Сгенерированный шаблон {len(existing) + 1}"
                tmpl = create_template_with_s3(
                    db=db,
                    title=title,
                    author_id=author_id,
                    html=sample_html
                )
            finally:
                db.close()

            user_tpls = st.session_state.setdefault("user_templates", [])
            user_tpls.append({
                "db_id": tmpl.id,
                "title": tmpl.title,
                "html_content": sample_html,
                "s3_key": tmpl.s3_key
            })

            st.success(f"Шаблон сохранён {len(existing) + 1}")

    with col_preview:
        if st.session_state.get("generated_sample"):
            render_editable_iframe(st.session_state.generated_sample, height=500)


def render_lesson_page():
    pdf_upload_enabled = False
    col_input, col_preview = st.columns(2)

    db = SessionLocal()
    try:
        templates = list_templates_by_author(db, st.session_state.user_id)
    finally:
        db.close()
    titles = [tpl.title for tpl in templates]

    with col_input:
        current_lesson = st.session_state.get("current_lesson") or {}

        if not st.session_state.get("generated_lesson") and current_lesson.get("content"):
            st.session_state.generated_lesson = current_lesson["content"]
        default = current_lesson.get("prompt", "")
        lesson_prompt = st.text_area(
            "Запрос для урока", default, placeholder="Опишите ваш желаемый контент здесь"
        )

        if titles:
            idx = 0
            prev = current_lesson.get("selected_template")
            if prev in titles:
                idx = titles.index(prev)
            selected_title = st.selectbox("Выбор шаблона", titles, index=idx)
        else:
            st.error("Нет доступных шаблонов. Создайте хотя бы один шаблон.")
            selected_title = None

        if st.button("Создать урок"):
            if lesson_prompt and selected_title:
                tpl = next(t for t in templates if t.title == selected_title)
                try:
                    raw = s3_client.get_object(tpl.s3_key)
                    template_html = raw.decode('utf-8')
                except Exception as e:
                    st.error(f"Ошибка загрузки шаблона: {e}")
                    return
                with st.spinner("Генерация урока..."):
                    generated = generate_lesson(template_html, lesson_prompt)
                st.session_state.generated_lesson = generated
                st.session_state.current_lesson = {
                    "content": generated,
                    "prompt": lesson_prompt,
                    "selected_template": selected_title
                }
                st.success("Урок сгенерирован и готов к сохранению.")
            else:
                st.error("Введите запрос и выберите шаблон.")

        st.file_uploader(
            "Загрузить PDF",
            type=["pdf"],
            disabled=not pdf_upload_enabled,
            help="Скоро будет доступно." if not pdf_upload_enabled else None
        )

        col_save, col_export = st.columns(2)
        with col_save:
            if st.button("Сохранить урок"):
                if not st.session_state.get("current_lesson"):
                    st.error("Нет сгенерированного урока для сохранения.")
                else:
                    db2 = SessionLocal()
                    try:
                        lesson_name = st.session_state.current_lesson.get("prompt")[:20] or "Новый урок"
                        tpl = next(t for t in templates if t.title == st.session_state.current_lesson["selected_template"])
                        lesson_obj = create_lesson_with_s3(
                            db=db2,
                            title=lesson_name,
                            author_id=st.session_state.user_id,
                            html_content=st.session_state.generated_lesson,
                            creation_prompt=lesson_prompt,
                            template_id=tpl.id
                        )
                    finally:
                        db2.close()
                    st.success(f"Урок сохранён")
        with col_export:
            if st.session_state.get("generated_lesson"):
                st.download_button(
                    "Экспорт HTML",
                    data=st.session_state.generated_lesson,
                    file_name="lesson.html",
                    mime="text/html"
                )

    with col_preview:
        if st.session_state.get("generated_lesson"):
            render_editable_iframe(st.session_state.generated_lesson, height=500)