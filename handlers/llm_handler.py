# handlers/llm_handler.py

import logging
from typing import List
from openai import OpenAI
from config import LLM_MODEL, EMBEDDING_MODEL

class LLMHandler:
    """
    Handles interactions with the Language Learning Model (LLM) API.
    """

    def __init__(self, api_key: str, model: str = LLM_MODEL):
        """
        Initializes the LLMHandler.

        :param api_key: The API key for OpenAI.
        :param model: The model name to use.
        """
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logging.getLogger(f"{__name__}.LLMHandler")

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generates an embedding vector for the given text.

        :param text: The text to generate an embedding for.
        :return: A list of floats representing the embedding vector.
        """
        try:
            response = self.client.embeddings.create(
                input=text, 
                model=EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise

    async def generate_response(self, message: str, context: str) -> str:
        """
        Generates a response using the LLM.

        :param message: The user's message.
        :param context: Contextual information to guide the response.
        :return: The AI-generated response as a string.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Eres Yayarecetas, una asistente de cocina amigable e inteligente.
Mantén conversaciones breves y amistosas en español, guiando sutilmente a los usuarios 
hacia el uso del servicio de recetas.

Reglas:
- Mantén las respuestas cortas (menos de 50 palabras)
- Responde siempre en español de España.
- Sé amable y entusiasta sobre la cocina
- No ofrezcas pruebas gratuitas a usuarios que ya las han usado
- Para usuarios con pruebas gratuitas, anima a usar el servicio
- Para usuarios suscritos, recuerda los beneficios
- Para usuarios sin pruebas ni suscripción, enfócate en los beneficios de suscribirse

Ejemplo de respuestas:
✅ "¡Qué bueno verte! ¿Tienes alguna receta familiar que quieras guardar? ¡Estoy lista para ayudarte!"
✅ "¡Me encanta esa receta! Recuerda que puedo organizarla para ti de forma clara y fácil de seguir."
❌ "I can help you with your recipe" (no inglés)
❌ "Let me transcribe that for you" (no mencionar transcripción)"""
                    },
                    {
                        "role": "user",
                        "content": f"Contexto: {context}\nMensaje del usuario: {message}\nResponde como Yayarecetas en menos de 50 palabras:"
                    }
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error generando respuesta AI: {str(e)}")
            return "¡Hola! Estoy aquí para ayudarte con tus recetas. ¿Cómo puedo ayudarte hoy?"
