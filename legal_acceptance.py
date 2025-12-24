# Copyright (C) @Wolfy004
# Channel: https://t.me/Wolfy004
# Legal acceptance handler for Terms & Conditions and Privacy Policy

import os
from functools import wraps
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from logger import LOGGER
from database_sqlite import db

LEGAL_DIR = "legal"
TERMS_FILE = os.path.join(LEGAL_DIR, "terms_and_conditions.txt")
PRIVACY_FILE = os.path.join(LEGAL_DIR, "privacy_policy.txt")

def load_legal_document(file_path: str) -> str:
    """Load legal document from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        LOGGER(__name__).error(f"Error loading legal document {file_path}: {e}")
        return ""

def get_legal_summary() -> str:
    """Get a summary of legal terms for display"""
    return (
        "⚖️ **TERMS & CONDITIONS AND PRIVACY POLICY**\n\n"
        "📜 **Before using this bot, you must accept our legal terms.**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔴 **IMPORTANT DISCLAIMERS:**\n\n"
        "1️⃣ **User Responsibility:**\n"
        "   • You are SOLELY responsible for the content you download\n"
        "   • You must ensure your use complies with all applicable laws\n"
        "   • The bot owner is NOT liable for your actions\n\n"
        "2️⃣ **Legal Compliance:**\n"
        "   • You must comply with copyright laws\n"
        "   • You must comply with the IT Act, 2000 (India)\n"
        "   • You must comply with GDPR (if applicable)\n"
        "   • You must NOT use the service for illegal purposes\n\n"
        "3️⃣ **Age Restriction:**\n"
        "   • You must be 18 years or older to use this service\n\n"
        "4️⃣ **Data Collection:**\n"
        "   • We collect: User ID, username, download logs\n"
        "   • Data is stored securely and not sold to third parties\n"
        "   • You have the right to request data deletion\n\n"
        "5️⃣ **No Warranty:**\n"
        "   • Service provided \"AS IS\" without warranties\n"
        "   • Bot owner not responsible for service availability\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📄 **Full Documents:**\n\n"
        "Click the buttons below to view complete documents:\n"
        "• Terms and Conditions\n"
        "• Privacy Policy\n\n"
        "⚠️ **By clicking 'I Accept', you confirm that:**\n"
        "   ✅ You have read and understood both documents\n"
        "   ✅ You are 18 years or older\n"
        "   ✅ You agree to all terms and conditions\n"
        "   ✅ You acknowledge sole responsibility for your actions\n\n"
        "❌ **Declining means you cannot use this bot.**"
    )

def get_terms_preview() -> str:
    """Get a preview of Terms and Conditions"""
    terms = load_legal_document(TERMS_FILE)
    if not terms:
        return "❌ Terms and Conditions document not found."
    lines = terms.split('\n')
    preview = '\n'.join(lines[:50])
    if len(lines) > 50:
        preview += "\n\n... (document continues)\n\nClick 'Full Terms' to read the complete document."
    return f"📜 **TERMS AND CONDITIONS**\n\n{preview}"

def get_privacy_preview() -> str:
    """Get a preview of Privacy Policy"""
    privacy = load_legal_document(PRIVACY_FILE)
    if not privacy:
        return "❌ Privacy Policy document not found."
    lines = privacy.split('\n')
    preview = '\n'.join(lines[:50])
    if len(lines) > 50:
        preview += "\n\n... (document continues)\n\nClick 'Full Privacy' to read the complete document."
    return f"🔒 **PRIVACY POLICY**\n\n{preview}"

def get_full_terms() -> str:
    """Get full Terms and Conditions"""
    terms = load_legal_document(TERMS_FILE)
    if not terms:
        return "❌ Terms and Conditions document not found."
    return f"📜 **TERMS AND CONDITIONS (FULL)**\n\n{terms}"

def get_full_privacy() -> str:
    """Get full Privacy Policy"""
    privacy = load_legal_document(PRIVACY_FILE)
    if not privacy:
        return "❌ Privacy Policy document not found."
    return f"🔒 **PRIVACY POLICY (FULL)**\n\n{privacy}"

async def show_legal_acceptance(client, message):
    """Show legal acceptance screen to user"""
    try:
        summary = get_legal_summary()
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📜 Terms", callback_data="legal_view_terms"),
                InlineKeyboardButton("🔒 Privacy", callback_data="legal_view_privacy")
            ],
            [
                InlineKeyboardButton("✅ I Accept (18+)", callback_data="legal_accept"),
                InlineKeyboardButton("❌ Decline", callback_data="legal_decline")
            ]
        ])
        await client.send_message(message.chat.id, summary, reply_markup=markup)
        LOGGER(__name__).info(f"Shown legal acceptance screen to user {message.from_user.id}")
    except Exception as e:
        LOGGER(__name__).error(f"Error showing legal acceptance: {e}")

def require_legal_acceptance(func):
    """Decorator to check if user has accepted legal terms before executing command"""
    @wraps(func)
    async def wrapper(client, message):
        user_id = message.from_user.id
        if db.check_legal_acceptance(user_id):
            return await func(client, message)
        
        LOGGER(__name__).info(f"User {user_id} needs to accept legal terms")
        await show_legal_acceptance(client, message)
    return wrapper
