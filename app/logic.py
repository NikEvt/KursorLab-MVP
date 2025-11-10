import os
import sys
import uuid
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# HTTP clients
import requests
import httpx

# ---------------------------
# Adjust imports for local vs Docker
# ---------------------------
dir_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if dir_root not in sys.path:
    sys.path.insert(0, dir_root)

try:
    from database.database import SessionLocal
    from database.templates_crud import list_templates_by_author, create_template_with_s3
except ImportError:
    from app.database.database import SessionLocal
    from app.database.templates_crud import list_templates_by_author, create_template_with_s3


# ---------------------------
# Logging setup
# ---------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------
# AI generation helpers
# ---------------------------

def generate_style_sample(style_prompt: str, structure_prompt: str = None) -> str:
    payload = {
        "style": f"Запрос оформления: {style_prompt}, Запрос структуризации: {structure_prompt}",
    }
    try:
        response = requests.post("http://localhost:8000/generate_style/", json=payload)
        response.raise_for_status()
        data = response.json()
        html = data.get("html_code", "")
        if not html:
            error = data.get("error", "No HTML returned.")
            logger.error(f"Style API error: {error}")
            return f"<p>Error: {error}</p>"
        return html
    except Exception as e:
        logger.error(f"generate_style_sample failed: {e}")
        return f"<p>Generation error: {e}</p>"


def generate_lesson(selected_style: str, lesson_prompt: str) -> str:
    url = "http://localhost:8000/generate_content/"
    payload = {"content": lesson_prompt, "html_code": selected_style}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        lesson = response.json().get("lesson", "")
        return lesson or "<p>No lesson content returned.</p>"
    except Exception as e:
        logger.error(f"generate_lesson failed: {e}")
        return f"<div>Error generating lesson: {e}</div>"


async def pdf_upload(user_id: int,
                     pdf_file,
                     url: str = "http://localhost:8000/upload_pdf/") -> dict:
    """
    Асинхронно загружает PDF-файл на указанный сервер.
    """
    try:
        pdf_content = pdf_file.getvalue()
        files = {"pdf_file": (pdf_file.name, pdf_content, pdf_file.type)}
        headers = {"user_id": str(user_id)}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, files=files)
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return {"success": False, "message": "Non-JSON response"}
    except Exception as e:
        logger.error(f"pdf_upload error: {e}")
        return {"success": False, "message": str(e)}


def get_styles(user_id: int) -> list:
    """Возвращает список шаблонов пользователя из БД"""
    db = SessionLocal()
    try:
        return list_templates_by_author(db, user_id)
    finally:
        db.close()
