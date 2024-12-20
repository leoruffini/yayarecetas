# handlers/voice_message_processor.py

import logging
import requests
import io
from openai import OpenAI
from handlers.llm_handler import LLMHandler
from config import LLM_MODEL, TRANSCRIPTION_MODEL

class VoiceMessageProcessor:
    def __init__(self, openai_client: OpenAI, llm_handler: LLMHandler, logger: logging.Logger):
        self.openai_client = openai_client
        self.llm_handler = llm_handler
        self.logger = logger

    async def process_voice_message(self, voice_message_url: str, account_sid: str, auth_token: str) -> str:
        try:
            audio_data = await self.download_voice_message(voice_message_url, account_sid, auth_token)
            raw_transcription = await self.transcribe_voice_message(audio_data)
            post_processed_transcript = await self.post_process_transcription(raw_transcription)
            return post_processed_transcript
        except Exception as e:
            self.logger.exception("Error processing voice message")
            return f"Error processing voice message: {str(e)}"

    async def download_voice_message(self, voice_message_url: str, account_sid: str, auth_token: str) -> bytes:
        self.logger.info(f"Downloading voice message from URL: {voice_message_url}")
        response = requests.get(voice_message_url, auth=(account_sid, auth_token))
        response.raise_for_status()
        self.logger.info("Voice message downloaded successfully")
        return response.content

    async def transcribe_voice_message(self, audio_data: bytes) -> str:
        self.logger.info("Transcribing voice message using OpenAI")
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "voice_message.ogg"
        transcript = self.openai_client.audio.transcriptions.create(model=TRANSCRIPTION_MODEL, file=audio_file)
        self.logger.info("Transcription successful")
        return transcript.text

    async def post_process_transcription(self, transcription: str) -> str:
        try:
            response = self.openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": """Eres un asistente especializado en estructurar recetas de cocina familiares manteniendo su carácter personal y casero. Tu tarea es organizar recetas transmitidas por mensajes de voz (normalmente de abuelas o cocineros caseros) en un formato claro y fácil de seguir.

FORMATO DE SALIDA:
# [Nombre de la Receta]

## Ingredientes
- [ingrediente 1 con cantidad]
- [ingrediente 2 con cantidad]
- ...

## Preparación
1. [Primer paso]
2. [Segundo paso]
3. ...

## Notas
- [Nota 1]
- [Nota 2]
- ...

REGLAS ESENCIALES PARA PRESERVAR LA AUTENTICIDAD:
1. Mantén TODAS las expresiones exactamente como fueron dichas
2. Conserva las medidas imprecisas tal cual ("un puñado", "al ojo", "un chorrito", etc.)
3. Preserva los comentarios personales y la sabiduría familiar
4. Mantén el tono cálido y conversacional
5. Incluye todos los trucos, consejos o variaciones como notas
6. NUNCA añadas información que no estaba en el mensaje original

REGLAS DE FORMATO:
1. Usa exactamente los encabezados mostrados arriba con '#' y '##'
2. Usa viñetas (-) para ingredientes y notas
3. Usa números para los pasos de preparación
4. Separa las secciones con una línea en blanco
5. Omite la sección "Notas" si no se mencionaron

EJEMPLOS DE CÓMO MANTENER LA AUTENTICIDAD:
❌ "Añadir una cucharada de aceite"
✅ "Echar un chorrito de aceite"

❌ "Mezclar hasta que esté homogéneo"
✅ "Remover con cariño hasta que esté todo bien mezclado"

❌ "Sazonar al gusto"
✅ "Le echas sal al gusto, yo siempre le pongo un puñadito generoso"

EJEMPLOS DE EXPRESIONES A MANTENER:
- "Un pellizco de..."
- "Cuando veas que ya está en su punto..."
- "Hasta que esté doradito..."

Recuerda: El objetivo es organizar la receta manteniendo su carácter casero y personal. La receta debe sonar como si la estuviera contando la persona que la compartió."""},
                    {"role": "user", "content": f"Por favor, convierte este mensaje de voz en una receta estructurada, manteniendo su carácter auténtico y personal:\n\n{transcription}"}
                ],
                max_tokens=1500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error post-processing transcription: {str(e)}")
            return transcription