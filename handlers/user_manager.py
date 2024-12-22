from sqlalchemy.orm import Session
from database import User
from datetime import datetime, timezone

class UserManager:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_phone(self, phone_number: str) -> User:
        return self.db.query(User).filter_by(phone_number=phone_number).first()

    def create_user(self, phone_number: str) -> User:
        user = User(phone_number=phone_number)
        self.db.add(user)
        self.db.commit()
        return user