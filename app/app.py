from config import load_config_and_styles
from database.database import init_db
from ui_components import render_sidebar, render_navigation, render_login_page
from pages import render_style_sample_page, render_lesson_page
import streamlit as st
import os
from utils.auth import get_user_from_token

load_config_and_styles()

init_db()

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "lessons" not in st.session_state:
    st.session_state.lessons = {}
if "templates" not in st.session_state:
    st.session_state.templates = {}
if "generated_sample" not in st.session_state:
    st.session_state.generated_sample = ">"
if "generated_lesson" not in st.session_state:
    st.session_state.generated_lesson = ""
if "current_lesson" not in st.session_state:
    st.session_state.current_lesson = None
if "nav_option" not in st.session_state:
    st.session_state.nav_option = "Generate Style Sample"

if "user_id" not in st.session_state or st.session_state.user_id is None:
    user = get_user_from_token()
    if user:
        st.session_state.user_id = user.id

if st.session_state.user_id is None:
    render_login_page()
    st.stop()  # Stop further execution until user logs in.

# If logged in, render the main app interface.
render_sidebar()
render_navigation()

if st.session_state.nav_option == "Generate Style Sample":
    render_style_sample_page()
elif st.session_state.nav_option == "Generate Lesson":
    render_lesson_page()