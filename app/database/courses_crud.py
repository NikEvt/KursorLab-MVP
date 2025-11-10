from database import *

# ----- Курсы (Course) -----
def create_course(db: Session, title: str, description: str = None) -> Course:
    course = Course(title=title, description=description)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_course(db: Session, course_id: int) -> Course:
    return db.query(Course).filter(Course.id == course_id).first()


def update_course(db: Session, course_id: int, **kwargs) -> Course:
    course = get_course(db, course_id)
    if course:
        for key, value in kwargs.items():
            setattr(course, key, value)
        db.commit()
        db.refresh(course)
    return course


def delete_course(db: Session, course_id: int) -> None:
    course = get_course(db, course_id)
    if course:
        db.delete(course)
        db.commit()