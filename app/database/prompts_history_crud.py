from database import *

# ----- История промптов (LessonPromptHistory) -----
def create_lesson_prompt_history(db: Session, lesson_id: int, prompt_text: str) -> LessonPromptHistory:
    history = LessonPromptHistory(lesson_id=lesson_id, prompt_text=prompt_text)
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def get_lesson_prompt_history(db: Session, history_id: int) -> LessonPromptHistory:
    return db.query(LessonPromptHistory).filter(LessonPromptHistory.id == history_id).first()


def update_lesson_prompt_history(db: Session, history_id: int, prompt_text: str) -> LessonPromptHistory:
    history = get_lesson_prompt_history(db, history_id)
    if history:
        history.prompt_text = prompt_text
        history.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(history)
    return history


def delete_lesson_prompt_history(db: Session, history_id: int) -> None:
    history = get_lesson_prompt_history(db, history_id)
    if history:
        db.delete(history)
        db.commit()