# message_templates.py

MESSAGE_TEMPLATES = {
    "welcome": """🎉 ¡Hola! Soy Yayarecetas, tu asistente de cocina 👩‍🍳✨

🎙️ Envíame un mensaje de voz con tu receta y:
1. La escribiré para ti
2. Te enviaré el enlace a tu receta
3. Te daré una página con todas tus recetas guardadas 📝

¡Empieza enviándome tu primera receta! 🌟""",
    "welcome_with_transcription": "👋 ¡Bienvenido/a a Yayarecetas! Veo que ya has enviado un mensaje de voz. ¡Genial! Estoy preparando tu receta ahora mismo. Te llegará por WhatsApp y además podrás verla en ayarecetas.com 📝",
    "processing_confirmation": "🎙️ ¡Receta recibida! La estoy escribiendo ahora mismo. En un momento te la envío. ⏳✨",
    "unsupported_media": "¡Ups! 😅 Por ahora solo puedo procesar mensajes de voz. Por favor, cuéntame tu receta en un mensaje de voz y ¡estaré encantada de organizarla! 🎙️✨",
    "transcription": "🧑‍🍳 ```TU RECETA DE YAYARECETAS:```\n\n{transcription}\n--------------\n```¿TE GUSTÓ ESTA RECETA? ¡PRUEBA YAYARECETAS! https://bit.ly/Yayarecetas\u200B```",
    "long_transcription_initial": "📝 ¡Aquí está tu receta!\n\n✨ Puedes verla completa aquí: {transcription_url}\n\n👩‍🍳 Todas tus recetas las encontrarás aquí: {user_recipes_url}\n\nY ahora te la enviaré por WhatsApp ❤️:",
    "long_transcription_summary": "```[RECETA ORGANIZADA CON YAYARECETAS 👩‍🍳]```\n\n{summary}\n\n--------------\n```¿TE GUSTÓ ESTA RECETA? ¡PRUEBA YAYARECETAS! https://bit.ly/Yayarecetas\u200B```",
    "split_transcription_initial": "Te la paso en {total_parts} partes:",
    "split_transcription_part": "Parte {part_number}/{total_parts}:\n\n{transcription}",
    "ai_response": "{response}",
    "verification_code": """🔐 Tu código de verificación para Yayarecetas es:

*{code}*

Este código expira en 5 minutos.""",
}

def get_message_template(template_key: str) -> str:
    """Get message template by key"""
    return MESSAGE_TEMPLATES.get(template_key, "Template not found")