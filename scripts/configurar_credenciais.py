#!/usr/bin/env python
"""
Script para configurar as credenciais do Google Sheets
"""

import os
import sys
import django
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')
django.setup()

from django.conf import settings

def configurar_credenciais():
    print("🔧 Configurando credenciais do Google Sheets...")
    
    # Caminho onde deve ficar o arquivo de credenciais
    credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")
    
    print(f"📁 Caminho esperado: {credentials_path}")
    
    if os.path.exists(credentials_path):
        print("✅ Arquivo credentials.json encontrado!")
        
        # Tenta ler e validar o arquivo
        try:
            with open(credentials_path, 'r') as f:
                credentials = json.load(f)
            
            # Verifica se tem as chaves necessárias
            required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_keys = [key for key in required_keys if key not in credentials]
            
            if missing_keys:
                print(f"❌ Arquivo inválido. Chaves faltando: {', '.join(missing_keys)}")
            else:
                print("✅ Arquivo de credenciais válido!")
                print(f"📧 Email da conta de serviço: {credentials.get('client_email')}")
                print(f"🆔 Project ID: {credentials.get('project_id')}")
                
        except json.JSONDecodeError:
            print("❌ Erro: Arquivo não é um JSON válido")
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {str(e)}")
    else:
        print("❌ Arquivo credentials.json não encontrado!")
        print("\n📋 Para configurar:")
        print("1. Baixe o arquivo JSON de credenciais do Google Cloud Console")
        print("2. Renomeie para 'credentials.json'")
        print(f"3. Coloque no diretório: {settings.BASE_DIR}")
        print("4. Execute este script novamente")
        
        # Cria um arquivo de exemplo
        exemplo_path = os.path.join(settings.BASE_DIR, "credentials_exemplo.json")
        exemplo = {
            "type": "service_account",
            "project_id": "seu-projeto-id",
            "private_key_id": "sua-private-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nsua-private-key\n-----END PRIVATE KEY-----\n",
            "client_email": "sua-conta-servico@seu-projeto.iam.gserviceaccount.com",
            "client_id": "seu-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sua-conta-servico%40seu-projeto.iam.gserviceaccount.com"
        }
        
        with open(exemplo_path, 'w') as f:
            json.dump(exemplo, f, indent=2)
        
        print(f"📄 Arquivo de exemplo criado: {exemplo_path}")

if __name__ == '__main__':
    configurar_credenciais()
