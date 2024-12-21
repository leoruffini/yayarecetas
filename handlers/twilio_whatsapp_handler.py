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
from handlers.stripe_handler import StripeHandler
from handlers.message_sender import MessageSender
from handlers.user_manager import UserManager

from database import User, WhitelistedNumber, Message
from config import (
    BASE_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY,
    TWILIO_WHATSAPP_NUMBER, MAX_WHATSAPP_MESSAGE_LENGTH, ADMIN_PHONE_NUMBER
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
        self.logger.debug("Received WhatsApp request")
        try:
            form_data = await request.form()
            url = str(request.url)
            signature = request.headers.get('X-Twilio-Signature', '')

            self.logger.debug(f"Form data: {form_data}")
            self.logger.debug(f"Request URL: {url}")
            self.logger.debug(f"Signature: {signature}")

            if not self.validator.validate(url, form_data, signature):
                self.logger.warning("Invalid request signature")
                return JSONResponse(content={"message": "Invalid request"}, status_code=400)

            phone_number = form_data.get('From', '').replace('whatsapp:', '')
            user = self.user_manager.get_user_by_phone(phone_number)
            is_subscribed = self.user_manager.is_whitelisted(phone_number)

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

            self.logger.info(f"User found: {user.phone_number}, Free trials remaining: {user.free_trial_remaining}, Subscribed: {is_subscribed}")

            if not media_type:
                # Handle text message
                user_message = form_data.get('Body', '')

                if is_subscribed:
                    context = "User is subscribed. Encourage them to use the service."
                elif user.free_trial_remaining > 0:
                    context = f"User has {user.free_trial_remaining} free trials remaining. Encourage them to use a trial."
                else:
                    context = "User has no free trials left and is not subscribed. Acknowledge their message, and gently encourage subscription."

                ai_response = await self.llm_handler.generate_response(user_message, context)

                if not is_subscribed and user.free_trial_remaining == 0:
                    ai_response += f"\n\n🔗 Subscribe here: Please subscribe now:\n{self.stripe_handler.payment_link}"

                await self.send_templated_message(phone_number, "ai_response", response=ai_response)
                return JSONResponse(content={"message": "Text message handled"}, status_code=200)

            if is_subscribed or user.free_trial_remaining > 0:
                if is_voice_message:
                    voice_message_url = form_data.get('MediaUrl0')
                    self.logger.info(f"Media type: {media_type}")
                    self.logger.info(f"Voice message URL: {voice_message_url}")

                    try:
                        transcription = await self.process_voice_message(phone_number, voice_message_url, db)
                        await self.send_admin_notification(phone_number, len(transcription) > MAX_WHATSAPP_MESSAGE_LENGTH, db)
                    except ValueError as e:
                        return JSONResponse(content={"message": str(e)}, status_code=400)

                    if not is_subscribed and user.free_trial_remaining > 0:
                        self.user_manager.update_free_trial(user)
                        self.logger.info(f"User {phone_number} has {user.free_trial_remaining} free trials remaining")

                        if user.free_trial_remaining == 0:
                            await self.send_last_free_trial_message(phone_number)

                    return JSONResponse(content={"message": "Voice message processed successfully", "transcription": transcription}, status_code=200)
                else:
                    await self.send_templated_message(phone_number, "unsupported_media", media_type=media_type)
                    return JSONResponse(content={"message": f"Unsupported media type: {media_type}"}, status_code=400)
            else:
                self.logger.info(f"User {phone_number} has no free trials remaining and is not subscribed")
                await self.send_subscription_reminder(phone_number)
                try:
                    await self.send_admin_notification(phone_number, False, db)
                except Exception as e:
                    self.logger.error(f"Admin notification failed: {str(e)}")
                return JSONResponse(content={"message": "User not subscribed"}, status_code=403)

        except HTTPException as http_exception:
            self.logger.error(f"HTTP Exception: {str(http_exception)}")
            return JSONResponse(content={"message": str(http_exception)}, status_code=http_exception.status_code)
        except Exception as e:
            self.logger.exception("Error handling WhatsApp request")
            db.rollback()
            return JSONResponse(content={"message": "Internal server error"}, status_code=500)

    async def send_admin_notification(self, user_phone: str, is_split_message: bool, db: Session):
        try:
            # Get user status info from db (reuse existing session)
            user = self.user_manager.get_user_by_phone(user_phone)
            whitelisted = self.user_manager.is_whitelisted(user_phone)

            # Build status message
            status_parts = []

            if not user:
                status_parts.append("📥 NEW USER")
            elif isinstance(whitelisted, WhitelistedNumber) or whitelisted is True:
                whitelist_record = db.query(WhitelistedNumber).filter_by(phone_number=user_phone).first()
                if whitelist_record and whitelist_record.expires_at and whitelist_record.expires_at > datetime.now(timezone.utc):
                    status_parts.append(f"💳 PAYING CUSTOMER (expires: {whitelist_record.expires_at.strftime('%Y-%m-%d')})")
                else:
                    status_parts.append("💳 PAYING CUSTOMER (no expiration)")
            elif user.free_trial_remaining > 0:
                status_parts.append(f"🎁 FREE TRIAL USER ({user.free_trial_remaining - 1} remaining)")
            else:
                status_parts.append("🚫 BLOCKED USER (no trials/subscription)")

            message = (
                f"Transcription request from {user_phone}\n"
                f"Status: {' '.join(status_parts)}"
            )

            if is_split_message:
                message += "\nℹ️ Long message split into multiple parts"

            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_whatsapp_number,
                to=ADMIN_PHONE_NUMBER
            )
            self.logger.info(f"Admin notification sent for user {user_phone}")
        except Exception as e:
            self.logger.error(f"Failed to send admin notification: {str(e)}")

    async def send_transcription(self, to_number: str, transcription: str, embedding: list[float], db: Session):
        try:
            # Get user from database
            user = self.user_manager.get_user_by_phone(to_number)
            user_id = user.id if user else '0'
            
            # Get recipe slug
            recipe_slug = self.get_recipe_slug(transcription, db)
            
            # Create message record with slug instead of random hash
            db_message = Message(phone_number=to_number, embedding=embedding)
            db_message.text = transcription
            db_message.hash = recipe_slug  # Using hash column for the slug
            
            # Save to database
            db.add(db_message)
            db.commit()
            
            # Generate URL
            transcription_url = f"{self.base_url}/yaya{user_id}/{recipe_slug}"
            
            # 2. Send user messages
            is_split_message = len(transcription) > MAX_WHATSAPP_MESSAGE_LENGTH

            # 2. Send user messages
            if not is_split_message:
                await self.send_templated_message(to_number, "transcription", transcription=transcription)
            else:
                # First send the web link
                await self.send_templated_message(
                    to_number,
                    "long_transcription_initial",
                    transcription_url=transcription_url
                )
                
                # Then split and send the transcription in parts
                message_parts = self.split_message(transcription, MAX_WHATSAPP_MESSAGE_LENGTH)
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

            # 4. Send admin notification
            await self.send_admin_notification(to_number, is_split_message, db)

        except Exception as e:
            self.logger.error(f"Failed to send transcription to {to_number}: {str(e)}")
            raise

    async def send_templated_message(self, to_number: str, template_key: str, **kwargs):
        await self.message_sender.send_templated_message(to_number, template_key, **kwargs)

    async def send_last_free_trial_message(self, to_number: str):
        context = "User has just used their last free trial."
        message = "Last free trial used"
        response = await self.llm_handler.generate_response(message, context)
        response += f"\n\n🔗 Please subscribe now:\n{self.stripe_handler.payment_link}"
        await self.send_templated_message(to_number, "subscription_reminder", message=response)

    async def send_subscription_reminder(self, to_number: str):
        context = "User needs to subscribe to continue using the service."
        message = "Subscription reminder"
        response = await self.llm_handler.generate_response(message, context)
        response += f"\n\n🔗 {self.stripe_handler.payment_link}"
        await self.send_templated_message(to_number, "subscription_reminder", message=response)

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

    def get_recipe_slug(self, transcription: str, db: Session) -> str:
        """Extract recipe name from transcription and add counter if needed"""
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
                    base_slug = title.strip('-')            # Remove leading/trailing hyphens
                    
                    # Check if slug exists and add counter if needed
                    slug = base_slug
                    counter = 1
                    while True:
                        # Check if this slug exists for any user
                        existing_message = db.query(Message)\
                            .filter(Message.hash == slug)\
                            .first()
                        
                        if not existing_message:
                            return slug
                        
                        # If exists, add counter and try again
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                
            return "untitled-recipe"
            
        except Exception as e:
            self.logger.error(f"Error creating recipe slug: {str(e)}")
            return "untitled-recipe"