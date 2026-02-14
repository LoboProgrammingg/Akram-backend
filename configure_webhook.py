import asyncio
import httpx
import os

# Configuration (matching docker-compose defaults)
EVOLUTION_URL = "http://evolution-api:8080" # Internal Docker URL
# Hostname 'backend' is the service name in docker-compose
WEBHOOK_URL = "http://backend:8000/webhooks/evolution" 

API_KEY = "akram-evolution-key-2026" # From .env
INSTANCE_NAME = "akram" # From .env

async def configure_webhook():
    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"Configuring webhook for instance: {INSTANCE_NAME}")
    print(f"Target Webhook URL: {WEBHOOK_URL}")

    async with httpx.AsyncClient() as client:
        # 1. Check/Create instance
        try:
            resp = await client.get(f"{EVOLUTION_URL}/instance/fetchInstances", headers=headers)
            if resp.status_code != 200:
                print(f"Error fetching instances: {resp.text}")
                # Try creating anyway if fetch fails? No, usually auth error.
                if resp.status_code == 401:
                    print("Auth failed. Check API_KEY.")
                    return
            
            instances = resp.json()
            exists = any(i.get("instance", {}).get("instanceName") == INSTANCE_NAME for i in instances)
            
            if not exists:
                print(f"Instance {INSTANCE_NAME} not found. Creating...")
                create_resp = await client.post(
                    f"{EVOLUTION_URL}/instance/create", 
                    headers=headers,
                    json={
                        "instanceName": INSTANCE_NAME,
                        "token": "", 
                        "qrcode": True
                    }
                )
                print(f"Create result: {create_resp.text}")
        except Exception as e:
            print(f"Connection error: {e}")
            return

        # 2. Set Webhook
        # Ensure enabled is boolean true
        webhook_payload = {
            "url": WEBHOOK_URL,
            "webhook_by_events": True,
            "webhook_base64": False,
            "events": [
                "MESSAGES_UPSERT" 
            ],
            "enabled": True
        }

        print("Setting webhook...")
        resp = await client.post(
            f"{EVOLUTION_URL}/webhook/set/{INSTANCE_NAME}",
            headers=headers,
            json=webhook_payload
        )
        print(f"Webhook configuration result: {resp.status_code} - {resp.text}")

        # 3. Settings 
        # Added sync_full_history as required by v1.8.2
        print("Updating settings...")
        settings_payload = {
            "reject_call": False,
            "groups_ignore": True,
            "always_online": True,
            "read_messages": True,
            "read_status": False,
            "sync_full_history": False
        }
        resp = await client.post(
            f"{EVOLUTION_URL}/settings/set/{INSTANCE_NAME}",
             headers=headers,
             json=settings_payload
        )
        print(f"Settings update result: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    asyncio.run(configure_webhook())
