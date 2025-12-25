import secrets
import aiohttp
from datetime import datetime, timedelta

from logger import LOGGER
from database_sqlite import db

PREMIUM_DOWNLOADS = 5
SESSION_VALIDITY_MINUTES = 30

class AdMonetization:
    def __init__(self):
        # All ads are on website only - no URL shorteners needed
        self.adsterra_smartlink = "https://www.effectivegatecpm.com/zn01rc1vt?key=78d0724d73f6154a582464c95c28210d"
        self.blog_url = "https://socialhub00.blogspot.com/"
        
        LOGGER(__name__).info("Ad Monetization initialized - using Adsterra SmartLink to blog")
    
    def create_ad_session(self, user_id: int) -> str:
        """Create a temporary session for ad watching"""
        session_id = secrets.token_hex(16)
        db.create_ad_session(session_id, user_id)
        
        LOGGER(__name__).info(f"Created ad session {session_id} for user {user_id}")
        return session_id
    
    def verify_ad_completion(self, session_id: str) -> tuple[bool, str, str]:
        """Verify that user clicked through URL shortener and generate verification code"""
        session_data = db.get_ad_session(session_id)
        
        if not session_data:
            return False, "", "❌ Invalid or expired session. Please start over with /watchad"
        
        # Check if session expired (30 minutes max)
        elapsed_time = datetime.now() - session_data['created_at']
        if elapsed_time > timedelta(minutes=SESSION_VALIDITY_MINUTES):
            db.delete_ad_session(session_id)
            return False, "", "⏰ Session expired. Please start over with /watchad"
        
        # Atomically mark session as used (prevents race condition)
        success = db.mark_ad_session_used(session_id)
        if not success:
            return False, "", "❌ This session has already been used. Please use /watchad to get a new link."
        
        # Generate verification code
        verification_code = self._generate_verification_code(session_data['user_id'])
        
        # Delete session after successful verification
        db.delete_ad_session(session_id)
        
        LOGGER(__name__).info(f"User {session_data['user_id']} completed ad session {session_id}, generated code {verification_code}")
        return True, verification_code, "✅ Ad completed! Here's your verification code"
    
    def _generate_verification_code(self, user_id: int) -> str:
        """Generate verification code after ad is watched"""
        code = secrets.token_hex(4).upper()
        db.create_verification_code(code, user_id)
        
        LOGGER(__name__).info(f"Generated verification code {code} for user {user_id}")
        return code
    
    def verify_code(self, code: str, user_id: int) -> tuple[bool, str]:
        """Verify user's code and grant free downloads"""
        code = code.upper().strip()
        
        verification_data = db.get_verification_code(code)
        
        if not verification_data:
            return False, "❌ **Invalid verification code.**\n\nPlease make sure you entered the code correctly or get a new one with `/watchad`"
        
        if verification_data['user_id'] != user_id:
            return False, "❌ **This verification code belongs to another user.**"
        
        created_at = verification_data['created_at']
        if datetime.now() - created_at > timedelta(minutes=30):
            db.delete_verification_code(code)
            return False, "⏰ **Verification code has expired.**\n\nCodes expire after 30 minutes. Please get a new one with `/watchad`"
        
        db.delete_verification_code(code)
        
        # Grant ad downloads
        db.add_ad_downloads(user_id, PREMIUM_DOWNLOADS)
        
        # Only increment ad URL view counter after SUCCESSFUL verification
        # This way users don't waste a view if they fail to complete or enter wrong code
        db.increment_ad_url_views(user_id)
        
        LOGGER(__name__).info(f"User {user_id} successfully verified code {code}, granted {PREMIUM_DOWNLOADS} ad downloads")
        return True, f"✅ **Verification successful!**\n\nYou now have **{PREMIUM_DOWNLOADS} free download(s)**!"
    
    def can_show_ad_link(self, user_id: int) -> tuple[bool, str]:
        """Check if user can view ad URL today (max 2 per day)"""
        views_today = db.get_daily_ad_url_views(user_id)
        if views_today >= 2:
            return False, f"❌ **Daily ad limit reached!**\n\nYou can view ad URLs **2 times per day**.\n\nYou've already viewed {views_today} today.\n\n⏰ Try again tomorrow!"
        return True, ""
    
    def generate_ad_link(self, user_id: int, bot_domain: str | None = None) -> tuple[str, str]:
        """
        Generate ad link - sends user to blog homepage with session
        Blog's JavaScript will automatically redirect to first verification page
        This way you can change verification pages in theme without updating bot code
        
        NOTE: Ad URL view counter is incremented ONLY after successful verification in verify_code()
        This prevents wasting views if user fails to complete or enter wrong code
        """
        session_id = self.create_ad_session(user_id)
        
        # Send to blog homepage - theme will handle redirect to first page
        first_page_url = f"{self.blog_url}?session={session_id}"
        
        # Add app_url parameter if bot domain is available
        if bot_domain:
            from urllib.parse import quote
            first_page_url += f"&app_url={quote(bot_domain)}"
        
        LOGGER(__name__).info(f"User {user_id}: Sending to blog homepage for ad verification - app_url: {bot_domain}")
        
        return session_id, first_page_url
    
    def get_premium_downloads(self) -> int:
        """Get number of downloads given for watching ads"""
        return PREMIUM_DOWNLOADS


class RichAdsMonetization:
    """RichAds Telegram Bot Message Integration"""
    
    def __init__(self):
        self.api_url = "http://15068.xml.adx1.com/telegram-mb"
        from config import PyroConf
        self.publisher_id = getattr(PyroConf, 'RICHADS_PUBLISHER_ID', '')
        self.widget_id = getattr(PyroConf, 'RICHADS_WIDGET_ID', '')
        self.cooldown = getattr(PyroConf, 'RICHADS_AD_COOLDOWN', 300)
        self.user_last_ad = {}  # Track when users last saw an ad
        LOGGER(__name__).info("RichAds Monetization initialized")
    
    def can_show_ad(self, user_id: int) -> bool:
        """Check if enough time passed since last ad"""
        if user_id not in self.user_last_ad:
            return True
        elapsed = (datetime.now() - self.user_last_ad[user_id]).total_seconds()
        return elapsed >= self.cooldown
    
    def mark_ad_shown(self, user_id: int):
        """Mark that user just saw an ad"""
        self.user_last_ad[user_id] = datetime.now()
    
    async def get_ad(self, user_id: int, language_code: str = "en", production: bool = True):
        """Fetch ad from RichAds API"""
        if not self.publisher_id:
            return None
        
        payload = {
            "language_code": language_code[:2],
            "publisher_id": self.publisher_id,
            "telegram_id": str(user_id),
            "production": production
        }
        
        if self.widget_id:
            payload["widget_id"] = self.widget_id
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        ads = await resp.json()
                        if ads and len(ads) > 0:
                            LOGGER(__name__).info(f"RichAds: Got ad for user {user_id}")
                            return ads[0]
                    return None
        except Exception as e:
            LOGGER(__name__).error(f"RichAds API error: {e}")
            return None
    
    async def report_impression(self, notification_url: str):
        """Report impression to RichAds"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(notification_url, timeout=5) as resp:
                    pass
        except:
            pass
    
    async def show_ad(self, client, chat_id: int, user_id: int, lang_code: str = "en"):
        """
        Show RichAds ad to user. Returns True if ad was shown.
        """
        # Skip if on cooldown
        if not self.can_show_ad(user_id):
            return False
        
        # Fetch ad
        ad = await self.get_ad(user_id, lang_code, production=True)
        if not ad:
            return False
        
        # Report impression
        if ad.get('notification_url'):
            await self.report_impression(ad['notification_url'])
        
        # Build keyboard with ad link
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                text=ad.get('button', '🔗 Visit'),
                url=ad.get('link', '')
            )]
        ])
        
        try:
            image_url = ad.get('image_preload') or ad.get('image')
            caption = f"📢 **{ad.get('title', 'Sponsored')}**\n\n{ad.get('message', '')}"
            
            if ad.get('brand'):
                caption += f"\n\n_Sponsored by {ad.get('brand')}_"
            
            await client.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=caption,
                reply_markup=keyboard
            )
            
            self.mark_ad_shown(user_id)
            LOGGER(__name__).info(f"RichAd shown to user {user_id}")
            return True
            
        except Exception as e:
            LOGGER(__name__).error(f"Error showing RichAd: {e}")
            return False


ad_monetization = AdMonetization()
richads = RichAdsMonetization()
