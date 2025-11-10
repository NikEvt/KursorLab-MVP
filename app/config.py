import streamlit as st

def load_config_and_styles():
    st.set_page_config(page_title="Курсор", layout="wide")

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 0rem !important;
            }
            div[data-testid="stRadio"] {
                margin-top: 0rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 0rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>
            MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display: none !important;}
        </style>
        """,
        unsafe_allow_html=True
    )