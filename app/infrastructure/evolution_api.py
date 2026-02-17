"""Evolution API 1.8.2 HTTP client.

Best practices for bulk messaging:
- Rate limiting: 1 message every 3-5 seconds minimum
- Random delays to appear more human-like
- Exponential backoff on errors
- Batch processing with pauses between batches
"""

import asyncio
import logging
import random
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Rate limiting constants for safe bulk messaging
MIN_DELAY_BETWEEN_MESSAGES = 3  # Minimum seconds between messages
MAX_DELAY_BETWEEN_MESSAGES = 7  # Maximum seconds for random delay
BATCH_SIZE = 10  # Messages per batch before longer pause
BATCH_PAUSE = 30  # Seconds to pause between batches


class EvolutionAPIClient:
    """Client for Evolution API 1.8.2 WhatsApp integration.
    
    Implements safe rate limiting for bulk messaging to avoid
    WhatsApp bans or blocks.
    """

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self._message_count = 0  # Track messages for batch control

    async def _apply_rate_limit(self):
        """Apply rate limiting between messages to avoid WhatsApp blocks.
        
        Uses random delays between MIN and MAX to appear more human-like.
        Every BATCH_SIZE messages, takes a longer BATCH_PAUSE.
        """
        self._message_count += 1
        
        # Check if we need a batch pause
        if self._message_count > 0 and self._message_count % BATCH_SIZE == 0:
            logger.info(f"Batch pause: {BATCH_PAUSE}s after {self._message_count} messages")
            await asyncio.sleep(BATCH_PAUSE)
        else:
            # Random delay between messages
            delay = random.uniform(MIN_DELAY_BETWEEN_MESSAGES, MAX_DELAY_BETWEEN_MESSAGES)
            logger.debug(f"Rate limit delay: {delay:.1f}s")
            await asyncio.sleep(delay)

    async def send_text(self, phone: str, message: str, apply_rate_limit: bool = True) -> dict:
        """
        Send a text message via Evolution API 1.8.2.
        
        Args:
            phone: Destination phone number
            message: Text message to send
            apply_rate_limit: If True, applies delay between messages (recommended for bulk)
        
        Retries up to max_retries times on failure with exponential backoff.
        """
        # Apply rate limiting before sending (for bulk safety)
        if apply_rate_limit:
            await self._apply_rate_limit()
        
        # Normalize phone number (remove +, spaces, dashes)
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Ensure country code (Brazil = 55)
        if not clean_phone.startswith("55"):
            clean_phone = f"55{clean_phone}"

        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": clean_phone,
            "textMessage": {"text": message},
            "options": {"delay": 1500, "presence": "composing"},
        }

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(
                        url, json=payload, headers=self.headers
                    )
                    response.raise_for_status()
                    result = response.json()
                    logger.info(f"Message sent to {clean_phone} (attempt {attempt}, total: {self._message_count})")
                    return result
            except httpx.HTTPStatusError as e:
                last_error = e
                error_text = e.response.text[:200] if e.response.text else "No response body"
                logger.warning(
                    f"Evolution API error (attempt {attempt}/{self.max_retries}): "
                    f"{e.response.status_code} - {error_text}"
                )
                # If rate limited (429) or server error (5xx), wait longer
                if e.response.status_code in (429, 500, 502, 503, 504):
                    extra_wait = 10 * attempt
                    logger.info(f"Rate limit/server error, waiting extra {extra_wait}s")
                    await asyncio.sleep(extra_wait)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Evolution API connection error (attempt {attempt}/{self.max_retries}): {e}"
                )

            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * attempt)

        raise Exception(
            f"Failed to send message after {self.max_retries} attempts: {last_error}"
        )

    def reset_message_count(self):
        """Reset the message counter (call at start of new bulk operation)."""
        self._message_count = 0

    async def check_instance_status(self) -> dict:
        """Check if the Evolution API instance is connected."""
        url = f"{self.base_url}/instance/connectionState/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to check instance status: {e}")
            return {"state": "error", "error": str(e)}

    async def get_instance_connect(self) -> dict:
        """Fetch the QR code for connection."""
        url = f"{self.base_url}/instance/connect/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get connection QR: {e}")
            return {"error": str(e)}
