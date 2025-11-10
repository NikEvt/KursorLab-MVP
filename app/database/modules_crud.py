from database import *

# ----- Модули (Module) -----
def create_module(db: Session, course_id: int, title: str, order: int = None) -> Module:
    module = Module(course_id=course_id, title=title, order=order)
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def get_module(db: Session, module_id: int) -> Module:
    return db.query(Module).filter(Module.id == module_id).first()


def update_module(db: Session, module_id: int, **kwargs) -> Module:
    module = get_module(db, module_id)
    if module:
        for key, value in kwargs.items():
            setattr(module, key, value)
        db.commit()
        db.refresh(module)
    return module


def delete_module(db: Session, module_id: int) -> None:
    module = get_module(db, module_id)
    if module:
        db.delete(module)
        db.commit()
