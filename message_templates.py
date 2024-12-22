# message_templates.py

MESSAGE_TEMPLATES = {
    "welcome": "🎉 ¡Hola! Soy Yayarecetas, tu asistente de cocina 👩‍🍳✨\n\n🎙️ Envíame un mensaje de voz con tu receta y la escribiré para ti! Te llegará por WhatsApp y además podrás verla en ayarecetas.com 📝",
    "welcome_with_transcription": "👋 ¡Bienvenido/a a Yayarecetas! Veo que ya has enviado un mensaje de voz. ¡Genial! Estoy preparando tu receta ahora mismo. Te llegará por WhatsApp y además podrás verla en ayarecetas.com 📝",
    "processing_confirmation": "🎙️ ¡Receta recibida! La estoy escribiendo ahora mismo. En un momento te la envío. ⏳✨",
    "unsupported_media": "¡Ups! 😅 Por ahora solo puedo procesar mensajes de voz. Por favor, cuéntame tu receta en un mensaje de voz y ¡estaré encantada de organizarla! 🎙️✨",
    "transcription": "🧑‍🍳 ```TU RECETA DE YAYARECETAS:```\n\n{transcription}\n--------------\n```¿TE GUSTÓ ESTA RECETA? ¡PRUEBA YAYARECETAS! https://bit.ly/Yayarecetas\u200B```",
    "long_transcription_initial": "📝 ¡Aquí está tu receta!\n\n✨ Puedes verla completa aquí: {transcription_url}\n\nY ahora te la enviaré por WhatsApp ❤️:",
    "long_transcription_summary": "```[RECETA ORGANIZADA CON YAYARECETAS 👩‍🍳]```\n\n{summary}\n\n--------------\n```¿TE GUSTÓ ESTA RECETA? ¡PRUEBA YAYARECETAS! https://bit.ly/Yayarecetas\u200B```",
    "split_transcription_initial": "Te la paso en {total_parts} partes:",
    "split_transcription_part": "Parte {part_number}/{total_parts}:\n\n{transcription}",
    "subscription_confirmation": "🔗 ¡Bienvenido/a! Tu suscripción está confirmada. Disfruta organizando tus recetas sin límites. Si tienes alguna pregunta, ¡no dudes en preguntarme!\n\n```GESTIONA TU SUSCRIPCIÓN: https://billing.stripe.com/p/login/test_28o001fdu2lo0iQ8ww\u200B``` ⁠",
    "subscription_cancelled": "¡Lamento que te vayas! 😢 Tu suscripción ha sido cancelada. Si cambias de opinión o tienes algún comentario, no dudes en contactarnos. ¡Gracias por probar Yayarecetas! 🙏",
    "subscription_reminder": "🔗 {message}",
    "ai_response": "{response}"
}

def get_message_template(template_key: str) -> str:
    """Get message template by key"""
    return MESSAGE_TEMPLATES.get(template_key, "Template not found")