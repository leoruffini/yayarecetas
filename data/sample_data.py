from datetime import datetime
from sqlalchemy.orm import Session
from database import Message, User

def get_sample_recipes(db: Session = None) -> list:
    if not db:
        # Fallback to static samples if no db provided
        return [
            {
                "title": "Tortilla de Patatas de la yaya Alba",
                "description": "Primero, pela las patatas con cuidadito y córtalas en rodajas finitas...",
                "text": """# Tortilla de Patatas de la yaya Alba...""",
                "created_at": datetime.now(),
                "slug": "tortilla-patatas",
                "user_id": 1
            }
        ]
    
    # Get latest 3 recipes from database with their users
    latest_recipes = db.query(Message, Message.phone_number)\
        .order_by(Message.created_at.desc())\
        .limit(3)\
        .all()
    
    samples = []
    for recipe, phone_number in latest_recipes:
        # Get user_id from phone_number
        user = db.query(User).filter_by(phone_number=phone_number).first()
        user_id = user.id if user else 1
        
        # Extract title from first line of text
        title = recipe.text.splitlines()[0].replace('# ', '') if recipe.text else "Sin título"
        
        # Extract first steps from Preparación section
        description = ""
        in_preparation = False
        lines = recipe.text.splitlines()
        for line in lines:
            if '## Preparación' in line:
                in_preparation = True
                continue
            if in_preparation and line.strip():
                if line.startswith('##'):  # Next section started
                    break
                if line.strip().startswith('1.'):  # First step
                    description = line.strip()[2:].strip()  # Remove "1." and whitespace
                    break
        
        if not description:  # Fallback if no preparation section found
            description = "Una receta familiar llena de sabor..."
        
        # Limit description to 80 chars and add ellipsis
        if len(description) > 80:
            description = description[:80].rstrip() + "..."
        
        samples.append({
            "title": title,
            "description": description,
            "text": recipe.text,
            "created_at": recipe.created_at,
            "slug": recipe.slug,
            "user_id": user_id
        })
    
    return samples