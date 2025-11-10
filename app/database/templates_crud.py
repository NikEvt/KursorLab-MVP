import os
import sys
import uuid
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# ---------------------------
# Adjust imports for local vs Docker
# ---------------------------
# When running as a script, ensure project root is on PYTHONPATH
dir_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if dir_root not in sys.path:
    sys.path.insert(0, dir_root)

try:
    from database.database import Template, User, SessionLocal
except ImportError:
    from app.database.database import Template, User, SessionLocal

from database.s3.s3 import s3_client

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
# Helper: verify author exists
# ---------------------------
def ensure_author(db: Session, author_id: int):
    if not db.get(User, author_id):
        raise ValueError(f"Author with id={author_id} not found in users table.")

# ---------------------------
# S3 helpers
# ---------------------------
def upload_html_to_s3(html: str, folder: str) -> str:
    """Upload HTML string to S3 and return the generated object key."""
    unique_id = uuid.uuid4()
    key = f"{folder}/{unique_id}.html"
    s3_client.put_object(
        object_key=key,
        body=html.encode('utf-8'),
        content_type='text/html'
    )
    return key

def delete_from_s3(key: str) -> None:
    """Delete object by key from S3."""
    s3_client.client.delete_object(Bucket=s3_client.bucket_name, Key=key)

# ---------------------------
# Templates CRUD
# ---------------------------

def create_template_with_s3(db: Session, title: str, author_id: int, html: str) -> Template:
    ensure_author(db, author_id)
    s3_key = upload_html_to_s3(html, folder='templates')
    tmpl = Template(title=title, author_id=author_id, s3_key=s3_key)
    db.add(tmpl)
    try:
        db.commit()
        db.refresh(tmpl)
        logger.info(f"Template created id={tmpl.id}")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"DB error: {e}")
        raise
    return tmpl


def get_template(db: Session, template_id: int) -> Template | None:
    return db.get(Template, template_id)


def list_templates_by_author(db: Session, author_id: int) -> list[Template]:
    return db.query(Template).filter_by(author_id=author_id).all()


def update_template_with_s3(db: Session, template_id: int, **fields) -> Template | None:
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None
    if 'html' in fields:
        new_html = fields.pop('html')
        old_key = tmpl.s3_key
        tmpl.s3_key = upload_html_to_s3(new_html, folder='templates')
        delete_from_s3(old_key)
    for k, v in fields.items():
        setattr(tmpl, k, v)
    db.commit()
    db.refresh(tmpl)
    logger.info(f"Template id={tmpl.id} updated")
    return tmpl


def delete_template_with_s3(db: Session, template_id: int) -> None:
    tmpl = get_template(db, template_id)
    if not tmpl:
        return
    delete_from_s3(tmpl.s3_key)
    db.delete(tmpl)
    db.commit()
    logger.info(f"Template id={template_id} deleted")

# ---------------------------
# Usage examples
# ---------------------------
if __name__ == '__main__':
    db = SessionLocal()
    try:

        # Create
        tmpl = create_template_with_s3(
            db, title='Test Tmpl', author_id=3,
            html='<html><body><h1>Hello</h1></body></html>'
        )

        # List
        all_by_author = list_templates_by_author(db, author_id=1)
        logger.info(f"Author 1 templates: {[t.id for t in all_by_author]}")

        # Update
        updated = update_template_with_s3(
            db, tmpl.id, title='Updated', html='<p>New</p>'
        )

        # Download from S3
        data = s3_client.get_object(updated.s3_key)
        with open('download.html', 'wb') as f:
            f.write(data)

        # Delete
        # delete_template_with_s3(db, updated.id)
    finally:
        db.close()
