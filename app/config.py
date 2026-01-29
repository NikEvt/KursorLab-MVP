# config.py
import streamlit as st


def load_config_and_styles():
    st.set_page_config(
        page_title="Курсор", layout="wide"
    )  # единственный set_page_config в app.py [web:17]

    st.markdown(
        """
        <style>
            .block-container { padding-top: 0rem !important; }
            div[data-testid="stRadio"] { margin-top: 0rem; }

            #MainMenu, footer, header { visibility: hidden; }
            .stDeployButton { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
