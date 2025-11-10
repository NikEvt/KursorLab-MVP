import streamlit as st

from streamlit_telegram_login import TelegramLoginWidgetComponent

telegram_login = TelegramLoginWidgetComponent(bot_username="kursor_auth_bot", secret_key="7747907503:AAF1MShodThrjVjwgXK4CpxV7qFDOEga7lc")
value = telegram_login.button
st.write(value)