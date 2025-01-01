import random
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import User
from handlers.message_sender import MessageSender
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, VERIFICATION_TEMPLATE_SID

class AuthHandler:
    def __init__(self):
        self.message_sender = MessageSender(
            account_sid=TWILIO_ACCOUNT_SID,
            auth_token=TWILIO_AUTH_TOKEN
        )

    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        return str(random.randint(100000, 999999))
    
    def verify_ownership(self, user_id: int, phone_number: str, db: Session) -> bool:
        """Verify that the phone number owns the given user_id"""
        user = db.query(User).filter(User.id == user_id).first()
        return user and user.phone_number == phone_number
    
    async def send_verification_code(self, user_id: int, code: str, db: Session):
        """Send verification code via WhatsApp template"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        await self.message_sender.send_whatsapp_template(
            to_number=user.phone_number,
            template_name=VERIFICATION_TEMPLATE_SID,
            template_data={
                "1": code
            }
        )