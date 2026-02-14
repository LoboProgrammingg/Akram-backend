"""Evolution API 1.8.2 HTTP client."""

import asyncio
import logging
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EvolutionAPIClient:
    """Client for Evolution API 1.8.2 WhatsApp integration."""

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

    async def send_text(self, phone: str, message: str) -> dict:
        """
        Send a text message via Evolution API 1.8.2.
        Retries up to max_retries times on failure.
        """
        # Normalize phone number (remove +, spaces, dashes)
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Ensure country code (Brazil = 55)
        if not clean_phone.startswith("55"):
            clean_phone = f"55{clean_phone}"

        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": clean_phone,
            "textMessage": {"text": message},
            "options": {"delay": 1200, "presence": "composing"},
        }

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        url, json=payload, headers=self.headers
                    )
                    response.raise_for_status()
                    result = response.json()
                    logger.info(f"Message sent to {clean_phone} (attempt {attempt})")
                    return result
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"Evolution API error (attempt {attempt}/{self.max_retries}): "
                    f"{e.response.status_code} - {e.response.text}"
                )
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
