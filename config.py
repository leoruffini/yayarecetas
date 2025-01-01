import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv('BASE_URL')

#STRIPE
STRIPE_PAYMENT_LINK = os.getenv('STRIPE_PAYMENT_LINK')
STRIPE_CUSTOMER_PORTAL_URL = os.getenv('STRIPE_CUSTOMER_PORTAL_URL')
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')


#TWILIO
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
WELCOME_MESSAGE = "¡Hola! 👋 Me gustaria guardar una receta familiar. 👩‍🍳"
WHATSAPP_LINK = f"https://api.whatsapp.com/send/?phone={TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '').replace('+', '')}&text={WELCOME_MESSAGE.replace(' ', '%20')}&type=phone_number&app_absent=0"

#OPENAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TRANSCRIPTION_MODEL = "whisper-1"
LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-ada-002"
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

MAX_WHATSAPP_MESSAGE_LENGTH = 1500
ADMIN_PHONE_NUMBER = os.getenv('ADMIN_PHONE_NUMBER')

VERIFICATION_TEMPLATE_SID = "HXcd4f6126f23f0e113c4fba5afc68f4a2"

if not all([BASE_URL, STRIPE_PAYMENT_LINK, STRIPE_CUSTOMER_PORTAL_URL]):
    raise ValueError("Missing required environment variables")