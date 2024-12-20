# message_templates.py

MESSAGE_TEMPLATES = {
    "welcome": "🎉 Hi! I'm Ada, your voice-to-text fairy! ✨🧚‍♀️\n\nYou've got 3 free transcription spells. Ready to try?\n\n🎙️ Send a voice message and watch the magic happen! 🚀",
    "welcome_with_transcription": "👋 Welcome to Ada! I see you've already sent a voice message. Great start! I'm transcribing it now and will send you the result in a moment. You have 2 more free transcriptions to try out. Enjoy the service!",
    "processing_confirmation": "🎙️ Voice message received! I'm processing it now. Your transcription will be ready in a moment. ⏳✨",
    "unsupported_media": "Oops! 😅 I can't handle {media_type} files just yet. Please send me a voice message, and I'll be happy to transcribe it for you! 🎙️✨",
    "transcription": "🎙️✨ ```YOUR TRANSCRIPT FROM ADA:```\n\n{transcription}\n--------------\n```GOT THIS FROM SOMEONE? TRY ADA! https://bit.ly/Free_Ada\u200B```",
    "long_transcription_initial": "📝 Here's your transcription!\n\n✨ You can view it on the web here: {transcription_url}\n\nI'll also send it to you in parts:",
    "long_transcription_summary": "```[SUMMARIZED WITH ADA 🧚‍♂️]```\n\n{summary}\n\n--------------\n```GOT THIS FROM SOMEONE? TRY ADA! https://bit.ly/Free_Ada\u200B```",
    "subscription_confirmation": "🔗 Great to have you on board! Your subscription is confirmed. Enjoy seamless voice transcription and all its benefits. If you have any questions or need assistance, just let me know!\n\n```MANAGE YOUR SUBSCRIPTION: https://billing.stripe.com/p/login/test_28o001fdu2lo0iQ8ww\u200B``` ⁠",
    "subscription_cancelled": "I'm sorry to see you go! 😢 Your subscription has been cancelled. If you change your mind or have any feedback, please don't hesitate to reach out. Thank you for trying me out! 🙏 - Ada",
    "subscription_reminder": "🔗 {message}",
    "ai_response": "{response}",
    "split_transcription_initial": {
        "text": "Your transcription will be sent in {total_parts} parts:"
    },
    "split_transcription_part": {
        "text": "Part {part_number}/{total_parts}:\n\n{transcription}"
    }
}

def get_message_template(template_key: str) -> str:
    templates = {
        "processing_confirmation": "🎙️ Voice message received! I'm processing it now. Your transcription will be ready in a moment. ⏳✨",
        "split_transcription_initial": "Your transcription will be sent in {total_parts} parts:",
        "split_transcription_part": "Part {part_number}/{total_parts}:\n\n{transcription}",
        "transcription": "{transcription}",
        "welcome": "👋 Welcome! I'm your voice message transcription assistant. Send me a voice message and I'll convert it to text for you! You have 3 free trials to test the service.",
        "welcome_with_transcription": "👋 Welcome! I see you've sent a voice message. I'll transcribe it for you right away! You have 3 free trials to test the service.",
        "subscription_reminder": "{message}",
        "unsupported_media": "Sorry, I can only process voice messages. The media type you sent ({media_type}) is not supported.",
        "ai_response": "{response}",
        "long_transcription_initial": "📝 Here's your transcription!\n\n✨ You can view it on the web here: {transcription_url}\n\nI'll also send it to you in parts:"
    }
    return templates.get(template_key, "Template not found")