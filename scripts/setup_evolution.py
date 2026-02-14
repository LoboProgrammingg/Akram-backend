import requests
import time
import sys
import qrcode
import base64

def setup_evolution():
    print("🚀 Configuração Assistida da Evolution API 🚀")
    print("---------------------------------------------")
    
    # 1. Get Configuration
    api_url = input("\n1. Digite a URL da sua Evolution API (ex: https://evolution-xxx.up.railway.app): ").strip()
    if api_url.endswith("/"):
        api_url = api_url[:-1]
        
    api_key = input("2. Digite sua Global API Key (AUTHENTICATION_API_KEY definida no Railway): ").strip()
    
    instance_name = "akram-bot"
    print(f"\nTentando criar/conectar na instância '{instance_name}'...")
    
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }
    
    # 2. Check/Create Instance
    create_url = f"{api_url}/instance/create"
    payload = {
        "instanceName": instance_name,
        "token": "", # Optional, can be same as global or generated
        "qrcode": True,
        "webhook": "", # Can configure later
        "events": ["APPLICATION_STARTUP", "MESSAGES_UPSERT"] 
    }
    
    try:
        # Try to fetch first to see if exists
        check_url = f"{api_url}/instance/fetchInstances"
        resp = requests.get(check_url, headers=headers)
        
        exists = False
        if resp.status_code == 200:
            instances = resp.json()
            if isinstance(instances, list):
                for inst in instances:
                   if inst.get('instance', {}).get('instanceName') == instance_name:
                       exists = True
                       print(f"✅ Instância '{instance_name}' já existe!")
                       break
            # Evolution v2 might return differently, handling generic check
        
        if not exists:
            print("Criando nova instância...")
            resp = requests.post(create_url, json=payload, headers=headers)
            if resp.status_code == 201 or resp.status_code == 200:
                print("✅ Instância criada com sucesso!")
                data = resp.json()
                # Check for QR in creation response
                if 'qrcode' in data and data['qrcode']:
                     print_qr(data['qrcode'])
                     return
            else:
                # If error is "already exists" (403/409), ignore
                if "already exists" not in resp.text:
                    print(f"❌ Erro ao criar instância: {resp.text}")
                    # Keep going to try fetching QR anyway
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return

    # 3. Connect / Get QR
    print("\n🔄 Buscando QR Code para conexão...")
    connect_url = f"{api_url}/instance/connect/{instance_name}"
    
    try:
        resp = requests.get(connect_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            # Evolution v2 return format for base64
            if 'base64' in data and data['base64']:
                 print_qr(data['base64'])
            elif 'code' in data:
                 print(f"\n🔗 Código de Pareamento: {data['code']}")
            else:
                 print(f"\n⚠️ Resposta inesperada: {data}")
                 print("Tente abrir a URL diretamente no navegador para ver o status.")
        else:
            print(f"❌ Falha ao buscar QR Code: {resp.text}")
            
    except Exception as e:
        print(f"Erro: {e}")

def print_qr(base64_str):
    # Remove prefix if present
    if "base64," in base64_str:
        base64_str = base64_str.split("base64,")[1]
        
    print("\n📱 ESCANEIE O QR CODE ABAIXO NO SEU WHATSAPP:")
    print("(Se não aparecer corretamente, maximize o terminal)\n")
    
    qr = qrcode.QRCode()
    qr.add_data(base64.b64decode(base64_str))
    qr.print_ascii(invert=True)
    
    print("\n✅ Assim que escanear, configure as variáveis no Backend!")

if __name__ == "__main__":
    try:
        setup_evolution()
    except KeyboardInterrupt:
        print("\nCancelado.")
