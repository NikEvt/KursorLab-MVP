import os
import sys
import uuid
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

# ---------------------------
# Adjust imports for local vs Docker
# ---------------------------
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)

try:
    from database.database import Lesson, User, Template, SessionLocal
except ImportError:
    from database import Lesson, User, Template, SessionLocal

try:
    from database.s3.s3 import s3_client
except ImportError:
    from s3.s3 import s3_client

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
# S3 helper functions
# ---------------------------

def upload_html_to_s3(html: str, folder: str) -> str:
    """Upload HTML string to S3 and return object key."""
    key = f"{folder}/{uuid.uuid4()}.html"
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
# Lesson CRUD operations (Module and Course entities are not required)
# ---------------------------

def create_lesson_with_s3(
    db: Session,
    title: str,
    author_id: int,
    html_content: str,
    creation_prompt: str,
    template_id: int
) -> Lesson:
    """Upload HTML to S3 and create a Lesson record."""
    # validate foreign keys
    if not db.get(User, author_id):
        raise ValueError(f"User id={author_id} not found")
    if not db.get(Template, template_id):
        raise ValueError(f"Template id={template_id} not found")

    s3_key = upload_html_to_s3(html_content, folder='lessons')
    lesson = Lesson(
        title=title,
        author_id=author_id,
        s3_key=s3_key,
        creation_prompt=creation_prompt,
        template_id=template_id
    )
    db.add(lesson)
    try:
        db.commit()
        db.refresh(lesson)
        logger.info(f"Lesson created id={lesson.id}")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"DB error: {e}")
        raise
    return lesson


def get_lesson(db: Session, lesson_id: int) -> Lesson | None:
    """Return a Lesson by ID or None."""
    return db.get(Lesson, lesson_id)


from sqlalchemy.orm import joinedload

def list_lessons_by_author_id(db: Session, author_id: int) -> list[Lesson]:
    return db.query(Lesson).options(joinedload(Lesson.template)).filter(Lesson.author_id == author_id).all()


def update_lesson_with_s3(
    db: Session,
    lesson_id: int,
    **fields
) -> Lesson | None:
    """Update Lesson fields; if html_content provided, re-upload and delete old."""
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        return None
    if 'html_content' in fields:
        new_html = fields.pop('html_content')
        old_key = lesson.s3_key
        lesson.s3_key = upload_html_to_s3(new_html, folder='lessons')
        delete_from_s3(old_key)
    for k, v in fields.items():
        setattr(lesson, k, v)
    db.commit()
    db.refresh(lesson)
    logger.info(f"Lesson id={lesson.id} updated")
    return lesson


def delete_lesson_with_s3(db: Session, lesson_id: int) -> None:
    """Delete a Lesson and its S3 file."""
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        return
    delete_from_s3(lesson.s3_key)
    db.delete(lesson)
    db.commit()
    logger.info(f"Lesson id={lesson_id} deleted")

# ---------------------------
# Usage examples
# ---------------------------
if __name__ == '__main__':
    db = SessionLocal()
    try:
        # Create a lesson
        lesson = create_lesson_with_s3(
            db=db,
            title='Sample Lesson',
            author_id=1,
            html_content='<h1>Lesson</h1>',
            creation_prompt='Generate lesson about AI',
            template_id=1
        )
        logger.info(f"Created lesson: {lesson.id}")

        # List lessons
        lessons = list_lessons(db)
        logger.info(f"Lessons: {[l.id for l in lessons]}")

        # Update lesson
        updated = update_lesson_with_s3(
            db, lesson.id, title='Updated Title', html_content='<p>New Content</p>'
        )
        logger.info(f"Updated lesson: {updated.id}")

        # Download content
        content = s3_client.get_object(updated.s3_key)
        with open('lesson_download.html', 'wb') as f:
            f.write(content)

        # Delete lesson
        # delete_lesson_with_s3(db, updated.id)
    finally:
        db.close()
