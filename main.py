# Standard library imports
import logging
from datetime import datetime, timedelta
from cachetools import TTLCache

# Third-party imports
import stripe
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import markdown2
from starlette.middleware.sessions import SessionMiddleware

# Local imports
from handlers.stripe_handler import StripeHandler
from handlers.twilio_whatsapp_handler import TwilioWhatsAppHandler
from database import DATABASE_URL, Message, User, get_db
from config import (
    BASE_URL, STRIPE_PAYMENT_LINK, STRIPE_CUSTOMER_PORTAL_URL,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY,
    TWILIO_WHATSAPP_NUMBER, LOG_LEVEL, MAX_WHATSAPP_MESSAGE_LENGTH,
    STRIPE_WEBHOOK_SECRET, STRIPE_API_KEY,
    ADMIN_PHONE_NUMBER, WHATSAPP_LINK
)
from data.sample_data import get_sample_recipes
from handlers.auth_handler import AuthHandler

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
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

# Add this near the top of main.py with other initializations
auth_handler = AuthHandler()

RATE_LIMIT_WINDOW = timedelta(minutes=5)

# Create a cache that expires entries after 5 minutes
verification_cache = TTLCache(maxsize=100, ttl=300)  # 300 seconds = 5 minutes

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
async def get_transcription(
    user_id: int,
    recipe_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        message = db.query(Message).filter(Message.slug == recipe_slug).first()
        if not message:
            raise HTTPException(status_code=404, detail="Recipe not found")
            
        if message.is_private:
            is_verified = request.session.get(f"verified_{user_id}", False)
            if not is_verified:
                return templates.TemplateResponse("transcript.html", {
                    "request": request,
                    "error_message": "Esta es una receta privada. Para verla, necesitas verificar que eres el propietario.",
                    "user_id": user_id,
                    "recipe_slug": recipe_slug
                })
        
        return templates.TemplateResponse("transcript.html", {
            "request": request,
            "transcription": message.text,
            "is_private": message.is_private,
            "user_id": user_id,
            "recipe_slug": recipe_slug,
            "hash": message.hash,
            "error_message": None
        })
            
    except Exception as e:
        logger.error(f"Error getting transcription: {str(e)}")
        return templates.TemplateResponse("transcript.html", {
            "request": request,
            "error_message": "Error cargando la receta"
        })

@app.get("/")
@app.get("/home.html")
async def home(request: Request, db: Session = Depends(get_db)):
    sample_recipes = get_sample_recipes(db)
    recent_recipes = []
    
    for recipe in sample_recipes:
        recent_recipes.append({
            "title": recipe["title"],
            "description": recipe["description"],
            "url": f"/yaya{recipe['user_id']}/{recipe['slug']}"  # Use actual user_id
        })
    
    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request, 
            "recent_recipes": recent_recipes,
            "whatsapp_link": WHATSAPP_LINK
        }
    )

@app.get("/yaya{user_id}")
async def get_user_recipes(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return templates.TemplateResponse("recipe_index.html", {
                "request": request,
                "recipes": [],
                "error_message": "Usuario no encontrado",
                "whatsapp_link": WHATSAPP_LINK
            })

        # Get all messages for this user
        is_verified = request.session.get(f"verified_{user_id}", False)
        messages_query = db.query(Message)\
            .filter(Message.phone_number == user.phone_number)

        if not is_verified:
            messages_query = messages_query.filter(Message.is_private == False)

        messages = messages_query.order_by(Message.created_at.desc()).all()

        recipes = []
        for message in messages:
            first_line = message.text.splitlines()[0].replace('# ', '') if message.text else "Sin título"
            recipes.append({
                "title": first_line,
                "url": f"/yaya{user_id}/{message.slug}",
                "created_at": message.created_at
            })

        return templates.TemplateResponse("recipe_index.html", {
            "request": request,
            "recipes": recipes,
            "error_message": None,
            "whatsapp_link": WHATSAPP_LINK
        })
        
    except Exception as e:
        logger.error(f"Error retrieving recipes for user {user_id}: {str(e)}")
        return templates.TemplateResponse("recipe_index.html", {
            "request": request,
            "recipes": [],
            "error_message": "Ha ocurrido un error al recuperar las recetas",
            "whatsapp_link": WHATSAPP_LINK
        })

@app.get("/edit/{user_id}/{recipe_slug}")
async def edit_recipe_page(
    user_id: int,
    recipe_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Get recipe from database
        message = db.query(Message).filter(Message.slug == recipe_slug).first()
        if not message:
            raise HTTPException(status_code=404, detail="Recipe not found")
            
        # Check if user is verified
        is_verified = request.session.get(f"verified_{user_id}", False)
        
        if not is_verified:
            # Redirect to verification page
            return RedirectResponse(
                f"/verify/{user_id}/{recipe_slug}",
                status_code=302
            )
            
        return templates.TemplateResponse("edit_recipe.html", {
            "request": request,
            "recipe_text": message.text,
            "is_private": message.is_private,
            "user_id": user_id,
            "recipe_slug": recipe_slug,
            "error_message": None
        })
        
    except Exception as e:
        logger.error(f"Error loading edit page: {str(e)}")
        return templates.TemplateResponse("edit_recipe.html", {
            "request": request,
            "recipe_text": "",
            "is_private": False,
            "user_id": user_id,
            "recipe_slug": recipe_slug,
            "error_message": "Error cargando la receta"
        })

@app.post("/edit/{user_id}/{recipe_slug}")
async def update_recipe(
    user_id: int,
    recipe_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form = await request.form()
        recipe_text = form.get("recipe_text")
        is_private = form.get("is_private") == "true"  # Checkbox value
        
        # Get recipe from database
        message = db.query(Message).filter(Message.slug == recipe_slug).first()
        if not message:
            raise HTTPException(status_code=404, detail="Recipe not found")
            
        # Check if user is verified
        is_verified = request.session.get(f"verified_{user_id}", False)
        if not is_verified:
            # Redirect to verification page
            return RedirectResponse(
                f"/verify/{user_id}/{recipe_slug}",
                status_code=302
            )
        
        # Update recipe
        message.text = recipe_text
        message.is_private = is_private
        db.commit()
        
        # Redirect to view page
        return RedirectResponse(
            f"/yaya{user_id}/{recipe_slug}",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Error updating recipe: {str(e)}")
        return templates.TemplateResponse("edit_recipe.html", {
            "request": request,
            "recipe_text": recipe_text,
            "is_private": is_private,
            "user_id": user_id,
            "recipe_slug": recipe_slug,
            "error_message": "Error guardando los cambios"
        })

@app.get("/verify/{user_id}/{recipe_slug}")
async def verify_page(
    user_id: int,
    recipe_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Get user's phone number
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Use phone number as cache key
        cache_key = user.phone_number
        
        if cache_key in verification_cache:
            logger.info(f"Rate limit active for user {user_id}. Skipping code send.")
            return templates.TemplateResponse("verify.html", {
                "request": request,
                "error": None,
                "user_id": user_id,
                "recipe_slug": recipe_slug
            })
            
        logger.info(f"Sending verification code to user {user_id}")
        
        # Generate and send code
        code = auth_handler.generate_verification_code()
        request.session[f"pending_code_{user_id}"] = code
        
        # Add to rate limit cache
        verification_cache[cache_key] = datetime.now()
        
        await auth_handler.send_verification_code(user_id, code, db)
        
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "error": None,
            "user_id": user_id,
            "recipe_slug": recipe_slug
        })
        
    except Exception as e:
        logger.error(f"Error in verification page: {str(e)}")
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "error": "Error al enviar el código de verificación",
            "user_id": user_id,
            "recipe_slug": recipe_slug
        })

@app.post("/verify/{user_id}/{recipe_slug}")
async def verify_code(
    user_id: int,
    recipe_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    form = await request.form()
    submitted_code = form.get("code")
    stored_code = request.session.get(f"pending_code_{user_id}")
    
    if submitted_code == stored_code:
        request.session[f"verified_{user_id}"] = True
        return RedirectResponse(f"/edit/{user_id}/{recipe_slug}", status_code=302)
    else:
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "error": "Código incorrecto"
        })

@app.get("/shared/{hash}")
async def view_shared_recipe(
    hash: str,
    request: Request,
    db: Session = Depends(get_db)
):
    # Get recipe by hash
    message = db.query(Message).filter(Message.hash == hash).first()
    if not message:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    return templates.TemplateResponse("transcript.html", {
        "request": request,
        "transcription": message.text,
        "is_shared": True,
        "error_message": None
    })

# Retrieve database info
print(f"CONNECTED TO DATABASE: {DATABASE_URL}")

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key"  # Use environment variable in production
)