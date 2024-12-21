# Standard library imports
import logging

# Third-party imports
import stripe
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import markdown2

# Local imports
from handlers.stripe_handler import StripeHandler
from handlers.twilio_whatsapp_handler import TwilioWhatsAppHandler
from database import DATABASE_URL, Message, User, get_db
from config import (
    BASE_URL, STRIPE_PAYMENT_LINK, STRIPE_CUSTOMER_PORTAL_URL,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY,
    TWILIO_WHATSAPP_NUMBER, LOG_LEVEL, MAX_WHATSAPP_MESSAGE_LENGTH,
    STRIPE_WEBHOOK_SECRET, STRIPE_API_KEY,
    ADMIN_PHONE_NUMBER
)

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Add markdown filter to Jinja2
def markdown_to_html(text):
    if not text:
        return ""
    # Configure markdown2 with the features we need
    return markdown2.markdown(text, extras=[
        "break-on-newline",   # Convert newlines to <br>
        "cuddled-lists",      # Allow lists to be cuddled to the preceding paragraph
        "fenced-code-blocks"  # Support for ```code blocks```
    ])

templates.env.filters["markdown"] = markdown_to_html

# Create an instance of TwilioWhatsAppHandler with dependency injection
@app.post("/whatsapp", response_model=None)
async def whatsapp(request: Request, db: Session = Depends(get_db)):
    twilio_whatsapp_handler = TwilioWhatsAppHandler(db)
    logger.debug("Received request to /whatsapp endpoint")
    return await twilio_whatsapp_handler.handle_whatsapp_request(request, db)

logger.info(f"TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID[:8]}...")
logger.info(f"TWILIO_AUTH_TOKEN: {TWILIO_AUTH_TOKEN[:8]}...")
logger.info(f"OPENAI_API_KEY: {OPENAI_API_KEY[:8]}...")
logger.info(f"STRIPE_WEBHOOK_SECRET: {STRIPE_WEBHOOK_SECRET[:16]}...")
logger.info(f"DEBUG MODE: {LOG_LEVEL}")

# Initialize StripeHandler with TwilioWhatsAppHandler
twilio_whatsapp_handler = TwilioWhatsAppHandler(get_db())
stripe_handler = StripeHandler(twilio_handler=twilio_whatsapp_handler)

@app.post("/create-checkout-session")
async def create_checkout_session():
    return stripe_handler.create_checkout_session()

@app.post("/webhook")
async def webhook_received(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe_handler.construct_event(payload, sig_header)
        logger.info(f"Received Stripe event: {event['type']}")

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            await stripe_handler.handle_checkout_completed(session, db)
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            await stripe_handler.handle_subscription_deleted(subscription, db)
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            await stripe_handler.handle_subscription_updated(subscription, db)
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return {"status": "success"}
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail='Invalid payload')
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail='Invalid signature')
    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe authentication error: {e}")
        raise HTTPException(status_code=500, detail='Stripe authentication error')
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail='Stripe error')
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail='Internal server error')

@app.get("/success")
async def success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/cancel")
async def cancel(request: Request):
    return templates.TemplateResponse("cancel.html", {"request": request})

@app.get("/yaya{user_id}/{recipe_slug}")
async def get_transcription_by_slug(
    user_id: int, 
    recipe_slug: str, 
    request: Request, 
    db: Session = Depends(get_db)
):
    logger.info(f"Attempting to retrieve recipe for user {user_id}: {recipe_slug}")
    
    # Format title from slug for display
    display_title = recipe_slug.replace('-', ' ').title()
    
    # Get the User-Agent header
    user_agent = request.headers.get('User-Agent', '')
    logger.debug(f"User-Agent: {user_agent}")
    
    # Check for pre-fetchers (reuse existing code)
    prefetch_user_agents = [
        'WhatsApp',
        'facebookexternalhit',
        'Facebot',
    ]
    
    if any(agent in user_agent for agent in prefetch_user_agents):
        logger.info(f"Detected pre-fetch request from {user_agent}")
        return Response(status_code=200)
    
    try:
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User not found: ID {user_id}")
            return templates.TemplateResponse("transcript.html", {
                "request": request,
                "transcription": None,
                "error_message": "🚨 Error: User not found",
                "title": "Error"
            })
            
        logger.debug(f"Found user: {user.phone_number}")
            
        # Get latest message for this user
        message = db.query(Message)\
            .filter(Message.phone_number == user.phone_number)\
            .order_by(Message.created_at.desc())\
            .first()
            
        if not message:
            logger.warning(f"No messages found for user {user_id} (phone: {user.phone_number})")
            return templates.TemplateResponse("transcript.html", {
                "request": request,
                "transcription": None,
                "error_message": "🚨 Error: Recipe not found",
                "title": "Error"
            })
            
        # Extract actual title from message content if possible
        try:
            lines = message.text.split('\n')
            for line in lines:
                if line.startswith('# '):
                    display_title = line[2:].strip()
                    logger.debug(f"Extracted title from message: {display_title}")
                    break
        except Exception as e:
            logger.warning(
                f"Could not extract title from message for user {user_id}: {str(e)}\n"
                f"First 100 chars of message: {message.text[:100]}"
            )
            # Keep using the slug-based title as fallback
            
        logger.info(f"Successfully retrieved recipe '{display_title}' for user {user_id}")
        return templates.TemplateResponse("transcript.html", {
            "request": request,
            "transcription": message.text,
            "error_message": None,
            "title": display_title
        })
        
    except Exception as e:
        logger.error(
            f"Error retrieving recipe for user {user_id} - {recipe_slug}\n"
            f"Error type: {type(e).__name__}\n"
            f"Error details: {str(e)}\n"
            f"User-Agent: {user_agent}"
        )
        return templates.TemplateResponse("transcript.html", {
            "request": request,
            "transcription": None,
            "error_message": "An error occurred while retrieving the recipe",
            "title": "Error"
        })

# Retrieve database info
print(f"CONNECTED TO DATABASE: {DATABASE_URL}")