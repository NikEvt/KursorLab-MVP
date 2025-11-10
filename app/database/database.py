import datetime
import os

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =======================================================
# Определения моделей
# =======================================================

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_nick = Column(String, unique=True, nullable=False, index=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    last_online = Column(DateTime, default=datetime.datetime.utcnow)

    # Отношения с шаблонами и уроками, созданными пользователем
    templates = relationship("Template", back_populates="author", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="author", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_nick='{self.telegram_nick}')>"


class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Курс содержит модули
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course(id={self.id}, title='{self.title}')>"


class Module(Base):
    __tablename__ = 'modules'

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=True, index=True)
    title = Column(String, nullable=False)
    order = Column(Integer, nullable=True)  # для упорядочивания модулей

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Module(id={self.id}, title='{self.title}', course_id={self.course_id})>"


class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    s3_key = Column(String, nullable=False)  # ссылка на HTML-файл шаблона, хранящийся в S3
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    author = relationship("User", back_populates="templates")
    # Связь с уроками, использующими шаблон (при необходимости)
    lessons = relationship("Lesson", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Template(id={self.id}, title='{self.title}', s3_key='{self.s3_key}')>"


class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey('modules.id'), nullable=True, index=True)
    title = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    s3_key = Column(String, nullable=False)  # Ссылка на HTML-файл урока в S3
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    creation_prompt = Column(Text)
    template_id = Column(Integer, ForeignKey('templates.id'), nullable=False, index=True)

    module = relationship("Module", back_populates="lessons")
    author = relationship("User", back_populates="lessons")
    template = relationship("Template", back_populates="lessons")
    prompt_history = relationship("LessonPromptHistory", back_populates="lesson", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lesson(id={self.id}, title='{self.title}', module_id={self.module_id})>"


class LessonPromptHistory(Base):
    __tablename__ = 'lesson_prompt_history'

    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    lesson = relationship("Lesson", back_populates="prompt_history")

    def __repr__(self):
        return f"<LessonPromptHistory(id={self.id}, lesson_id={self.lesson_id}, updated_at={self.updated_at})>"


# =======================================================
# Инициализация базы данных, создание индексов и представлений
# =======================================================
def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        # Создание дополнительных индексов
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lessons_author ON lessons (author_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lessons_template ON lessons (template_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_modules_course ON modules (course_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_templates_author ON templates (author_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_lesson ON lesson_prompt_history (lesson_id)"))

        # Пример представления для получения подробной информации по урокам
        conn.execute(text("DROP VIEW IF EXISTS view_lessons_detailed"))
        conn.execute(text("""
            CREATE VIEW view_lessons_detailed AS
            SELECT l.id AS lesson_id,
                   l.title AS lesson_title,
                   l.created_at,
                   u.telegram_nick AS author_nick,
                   m.title AS module_title,
                   c.title AS course_title,
                   t.title AS template_title
            FROM lessons l
            JOIN users u ON l.author_id = u.id
            JOIN modules m ON l.module_id = m.id
            JOIN courses c ON m.course_id = c.id
            JOIN templates t ON l.template_id = t.id
        """))
        conn.commit()
