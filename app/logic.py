import logging
import os
import sys

import httpx
import requests
from dotenv import load_dotenv

# ---------------------------
# Adjust imports for local vs Docker
# ---------------------------
dir_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if dir_root not in sys.path:
    sys.path.insert(0, dir_root)

try:
    from database.database import SessionLocal
    from database.templates_crud import (
        create_template_with_s3,
        list_templates_by_author,
    )
except ImportError:
    from app.database.database import SessionLocal
    from app.database.templates_crud import (
        create_template_with_s3,
        list_templates_by_author,
    )

# ---------------------------
# Logging + env
# ---------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------
# Global URLs
# ---------------------------
# По умолчанию для Docker-контейнера логичнее host.docker.internal, а локально можно переопределить через .env
API_BASE_URL = os.getenv("API_BASE_URL", "http://host.docker.internal:8000").rstrip(
    "/"
)  # [web:22][web:44]

GENERATE_STYLE_URL = f"{API_BASE_URL}/generate_style/"
GENERATE_CONTENT_URL = f"{API_BASE_URL}/generate_content/"
UPLOAD_PDF_URL = f"{API_BASE_URL}/upload_pdf/"

DEFAULT_TIMEOUT_S = float(os.getenv("API_TIMEOUT", "30"))


# ---------------------------
# AI generation helpers
# ---------------------------
def generate_style_sample(
    style_prompt: str, structure_prompt: str | None = None
) -> str:
    payload = {
        "style": f"Запрос оформления: {style_prompt}, Запрос структуризации: {structure_prompt}",
    }
    try:
        response = requests.post(GENERATE_STYLE_URL, json=payload, timeout=300)
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


def generate_lesson(selected_style: str, lesson_prompt: str, search_params: dict):
    payload = {
        "content": lesson_prompt,
        "html_code": selected_style,
    }
    payload["search_params"] = {
        "user_id": str(search_params["user_id"]),
        "doc_id": ["112263"],
    }

    try:
        logger.info(
            "generate_content payload: content_len=%s html_len=%s",
            None if lesson_prompt is None else len(lesson_prompt),
            None if selected_style is None else len(selected_style),
        )
        r = requests.post(GENERATE_CONTENT_URL, json=payload, timeout=300)
        if r.status_code >= 400:
            logger.error(
                "generate_content failed: %s %s", r.status_code, r.text
            )  # тело ответа [web:72]
        r.raise_for_status()  # на 4xx/5xx выбросит HTTPError [web:63]

        lesson = r.json().get("lesson", "")
        return lesson or "<p>No lesson content returned.</p>"

    except requests.HTTPError as e:
        resp = e.response
        if resp is not None:
            logger.error(
                "HTTPError: %s %s", resp.status_code, resp.text
            )  # как вытащить текст [web:72]
        return f"<div>Error generating lesson: {e}</div>"

    except Exception as e:
        logger.error(f"generate_lesson failed: {e}")
        return f"<div>Error generating lesson: {e}</div>"


async def pdf_upload(user_id: int, pdf_file, url: str = UPLOAD_PDF_URL) -> dict:
    try:
        pdf_content = pdf_file.getvalue()
        files = {"pdf_file": (pdf_file.name, pdf_content, pdf_file.type)}
        headers = {"user_id": str(user_id)}
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
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
    db = SessionLocal()
    try:
        return list_templates_by_author(db, user_id)
    finally:
        db.close()
