from database.database import User, SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime

# ----- Пользователи (User) -----
def create_user(db: Session, telegram_nick: str, telegram_id: str, password_hash: str, last_online: datetime = None) -> User:
    if last_online is None:
        last_online = datetime.utcnow()
    user = User(telegram_nick=telegram_nick, telegram_id=telegram_id, password_hash=password_hash, last_online=last_online)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_telegram_id(db: Session, telegram_id: str) -> User:
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def get_user_by_nick(db: Session, telegram_nick: str) -> User:
    return db.query(User).filter(User.telegram_nick == telegram_nick).first()


def update_user(db: Session, user_id: int, **kwargs) -> User:
    user = get_user(db, user_id)
    if user:
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    if user:
        db.delete(user)
        db.commit()

def main():
    db = SessionLocal()

    try:
        # Example: Create user
        new_user = create_user(db, telegram_nick="john_doe", telegram_id="123456", password_hash="hashed_pw")
        print("User created:", new_user)

        # Example: Get user by ID
        fetched_user = get_user(db, new_user.id)
        print("Fetched by ID:", fetched_user)

        # Example: Get user by Telegram ID
        user_by_telegram_id = get_user_by_telegram_id(db, "123456")
        print("Fetched by Telegram ID:", user_by_telegram_id)

        # Example: Get user by nickname
        user_by_nick = get_user_by_nick(db, "john_doe")
        print("Fetched by Nick:", user_by_nick)

        # Example: Update user
        updated_user = update_user(db, new_user.id, telegram_nick="jane_doe", last_online=datetime.utcnow())
        print("Updated User:", updated_user)

        # Example: Delete user
        #delete_user(db, updated_user.id)
        #print("User deleted.")

    finally:
        db.close()

if __name__ == "__main__":
    main()