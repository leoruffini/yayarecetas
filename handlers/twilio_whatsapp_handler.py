import logging
import uuid
from datetime import datetime, timezone

from openai import OpenAI
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from handlers.llm_handler import LLMHandler
from handlers.voice_message_processor import VoiceMessageProcessor
from handlers.message_sender import MessageSender
from handlers.user_manager import UserManager
from handlers.stripe_handler import StripeHandler

from database import Message
from config import (
    BASE_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY,
    TWILIO_WHATSAPP_NUMBER, MAX_WHATSAPP_MESSAGE_LENGTH, ADMIN_PHONE_NUMBER,
    STRIPE_API_KEY, STRIPE_PAYMENT_LINK, STRIPE_CUSTOMER_PORTAL_URL
)
from message_templates import get_message_template

class TwilioWhatsAppHandler:
    def __init__(self, db: Session):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.openai_api_key = OPENAI_API_KEY
        self.twilio_whatsapp_number = TWILIO_WHATSAPP_NUMBER
        self.base_url = BASE_URL
        self.validator = RequestValidator(self.auth_token)
        self.twilio_client = Client(self.account_sid, self.auth_token)
        self.llm_handler = LLMHandler(api_key=self.openai_api_key)
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.logger = logging.getLogger(f"{__name__}.TwilioWhatsAppHandler")
        self.stripe_handler = StripeHandler(twilio_handler=self)
        self.voice_message_processor = VoiceMessageProcessor(
            openai_client=self.openai_client,
            llm_handler=self.llm_handler,
            logger=self.logger
        )
        self.message_sender = MessageSender(
            account_sid=self.account_sid,
            auth_token=self.auth_token
        )
        self.user_manager = UserManager(db)
        if not all([self.account_sid, self.auth_token, self.openai_api_key, self.twilio_whatsapp_number]):
            raise ValueError("Missing required environment variables for TwilioWhatsAppHandler")

    async def handle_whatsapp_request(self, request: Request, db: Session) -> JSONResponse:
        try:
            form_data = await request.form()
            url = str(request.url)
            signature = request.headers.get('X-Twilio-Signature', '')
            
            if not self.validator.validate(url, form_data, signature):
                self.logger.warning("Invalid request signature")
                return JSONResponse(content={"message": "Invalid request"}, status_code=400)

            phone_number = form_data.get('From', '').replace('whatsapp:', '')
            user = self.user_manager.get_user_by_phone(phone_number)

            media_type = form_data.get('MediaContentType0', '')
            is_voice_message = media_type.startswith('audio/')

            if not user:
                # New user
                user = self.user_manager.create_user(phone_number)
                if is_voice_message:
                    await self.send_templated_message(phone_number, "welcome_with_transcription")
                else:
                    await self.send_templated_message(phone_number, "welcome")
                if not is_voice_message:
                    return JSONResponse(content={"message": "Welcome message sent"}, status_code=200)

            if not media_type:
                # Handle text message
                user_message = form_data.get('Body', '')
                context = "User sent a text message. Encourage them to send a voice message with a recipe."
                ai_response = await self.llm_handler.generate_response(user_message, context)
                await self.send_templated_message(phone_number, "ai_response", response=ai_response)
                return JSONResponse(content={"message": "Text message handled"}, status_code=200)

            if is_voice_message:
                voice_message_url = form_data.get('MediaUrl0')
                try:
                    transcription = await self.process_voice_message(phone_number, voice_message_url, db)
                except ValueError as e:
                    return JSONResponse(content={"message": str(e)}, status_code=400)
                return JSONResponse(content={"message": "Voice message processed successfully"}, status_code=200)
            else:
                await self.send_templated_message(phone_number, "unsupported_media")
                return JSONResponse(content={"message": f"Unsupported media type: {media_type}"}, status_code=400)

        except Exception as e:
            self.logger.exception("Error handling WhatsApp request")
            db.rollback()
            return JSONResponse(content={"message": "Internal server error"}, status_code=500)

    async def send_admin_notification(self, user_phone: str, is_split_message: bool, db: Session):
        try:
            user = self.user_manager.get_user_by_phone(user_phone)
            
            status = "📥 NEW USER" if not user else "👤 USER"
            
            message = (
                f"Recipe request from {user_phone}\n"
                f"Status: {status}"
            )

            if is_split_message:
                message += "\nℹ️ Long message split into multiple parts"

            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_whatsapp_number,
                to=ADMIN_PHONE_NUMBER
            )
        except Exception as e:
            self.logger.error(f"Failed to send admin notification: {str(e)}")

    async def send_transcription(self, to_number: str, transcription: str, embedding: list[float], db: Session):
        try:
            # Get user from database
            user = self.user_manager.get_user_by_phone(to_number)
            user_id = user.id if user else '0'
            
            # Get recipe slug
            recipe_slug = self.get_recipe_slug(transcription, datetime.now(timezone.utc))
            
            # Create message record
            db_message = Message(
                phone_number=to_number, 
                embedding=embedding,
                hash=uuid.uuid4().hex,
                slug=recipe_slug
            )
            db_message.text = transcription
            
            # Save to database
            db.add(db_message)
            db.commit()
            
            # Generate URL using slug
            transcription_url = f"{self.base_url}/yaya{user_id}/{recipe_slug}"
            
            # Always send the web link first
            await self.send_templated_message(
                to_number,
                "long_transcription_initial",
                transcription_url=transcription_url
            )
            
            # Then send the transcription (either full or split)
            message_parts = self.split_message(transcription, MAX_WHATSAPP_MESSAGE_LENGTH)
            is_split_message = len(message_parts) > 1
            
            if not is_split_message:
                await self.send_templated_message(
                    to_number, 
                    "transcription", 
                    transcription=transcription
                )
            else:
                await self.send_templated_message(
                    to_number, 
                    "split_transcription_initial", 
                    total_parts=len(message_parts)
                )
                
                for i, part in enumerate(message_parts, 1):
                    await self.send_templated_message(
                        to_number,
                        "split_transcription_part",
                        part_number=i,
                        total_parts=len(message_parts),
                        transcription=part
                    )
            
            # Send admin notification
            await self.send_admin_notification(to_number, is_split_message, db)
            
        except Exception as e:
            self.logger.error(f"Failed to send transcription to {to_number}: {str(e)}")
            raise

    async def send_templated_message(self, to_number: str, template_key: str, **kwargs):
        await self.message_sender.send_templated_message(to_number, template_key, **kwargs)

    async def process_voice_message(self, phone_number: str, voice_message_url: str, db: Session) -> str:
        try:
            await self.send_templated_message(phone_number, "processing_confirmation")

            if not voice_message_url:
                self.logger.error("No media found")
                raise ValueError("No media found")

            # Log the start of transcription
            self.logger.info(f"Starting transcription for {phone_number}")

            transcription = await self.voice_message_processor.process_voice_message(
                voice_message_url,
                self.account_sid,
                self.auth_token
            )
            
            # Log the transcription length and first few characters
            self.logger.info(f"Transcription length: {len(transcription)}")
            self.logger.info(f"Transcription start: {transcription[:100]}")

            # Generate embedding
            embedding = self.llm_handler.generate_embedding(transcription)

            # Send transcription with more detailed logging
            self.logger.info("Sending transcription to user...")
            await self.send_transcription(phone_number, transcription, embedding, db)
            self.logger.info("Transcription sent successfully")

            return transcription

        except Exception as e:
            self.logger.error(f"Error in process_voice_message: {str(e)}")
            raise

    def split_message(self, text: str, max_length: int) -> list[str]:
        """
        Split a long message into parts that don't exceed max_length.
        Tries to split at sentence boundaries when possible.
        """
        if len(text) <= max_length:
            return [text]
        
        parts = []
        while text:
            if len(text) <= max_length:
                parts.append(text)
                break
                
            # Try to find a sentence boundary
            split_point = max_length
            for separator in ['. ', '! ', '? ', '\n']:
                last_separator = text[:max_length].rfind(separator)
                if last_separator != -1:
                    split_point = last_separator + len(separator)
                    break
                
            # If no sentence boundary found, try to split at last space
            if split_point == max_length:
                last_space = text[:max_length].rfind(' ')
                if last_space != -1:
                    split_point = last_space + 1
            
            parts.append(text[:split_point].strip())
            text = text[split_point:].strip()
        
        return parts

    def get_recipe_slug(self, transcription: str, created_at: datetime) -> str:
        """Extract recipe name from transcription and convert to URL-friendly slug with timestamp"""
        try:
            import unicodedata
            import re
            
            # Find the first line that starts with # (recipe title)
            lines = transcription.split('\n')
            for line in lines:
                if line.startswith('# '):
                    # Remove the # and trim whitespace
                    title = line[2:].strip()
                    
                    # Convert to lowercase and handle Spanish characters
                    title = title.lower()
                    title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode()
                    
                    # Replace spaces and invalid characters with hyphens
                    title = re.sub(r'[^\w\s-]', '', title)  # Remove special characters
                    title = re.sub(r'[-\s]+', '-', title)   # Replace spaces with single hyphen
                    title = title.strip('-')                 # Remove leading/trailing hyphens
                    
                    # Add timestamp to make the slug unique (YYYYMMDDHHmmss)
                    timestamp = created_at.strftime('%Y%m%d%H%M%S')
                    return f"{title}-{timestamp}"
                
            return f"untitled-recipe-{created_at.strftime('%Y%m%d%H%M%S')}"
            
        except Exception as e:
            self.logger.error(f"Error creating recipe slug: {str(e)}")
            return f"untitled-recipe-{created_at.strftime('%Y%m%d%H%M%S')}"