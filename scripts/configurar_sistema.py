#!/usr/bin/env python
"""
Script para configurar todo o sistema do zero
"""

import os
import sys
import django
import json

def configurar_sistema():
    print("🚀 Configurando sistema completo...")
    
    # 1. Configurar credenciais
    print("\n1️⃣ Configurando credenciais...")
    
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')
    django.setup()
    
    from django.conf import settings
    
    credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")
    
    if not os.path.exists(credentials_path):
        print("❌ Arquivo credentials.json não encontrado!")
        print(f"📁 Coloque o arquivo em: {credentials_path}")
        
        # Cria arquivo de exemplo
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
        
        exemplo_path = os.path.join(settings.BASE_DIR, "credentials_exemplo.json")
        with open(exemplo_path, 'w') as f:
            json.dump(exemplo, f, indent=2)
        
        print(f"📄 Arquivo de exemplo criado: {exemplo_path}")
        print("⚠️ Configure suas credenciais e execute novamente")
        return
    else:
        print("✅ Arquivo credentials.json encontrado!")
    
    # 2. Resetar banco
    print("\n2️⃣ Resetando banco de dados...")
    
    # Remove o banco SQLite se existir
    db_path = os.path.join(settings.BASE_DIR, "db.sqlite3")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Banco de dados removido")
    
    # Remove arquivos de migração antigos
    migrations_dir = os.path.join(settings.BASE_DIR, "core", "migrations")
    if os.path.exists(migrations_dir):
        for file in os.listdir(migrations_dir):
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(migrations_dir, file)
                os.remove(file_path)
                print(f"✅ Migração removida: {file}")
    
    # 3. Aplicar migrações
    print("\n3️⃣ Aplicando migrações...")
    
    from django.core.management import execute_from_command_line
    
    execute_from_command_line(['manage.py', 'makemigrations'])
    execute_from_command_line(['manage.py', 'migrate'])
    
    # 4. Criar usuários
    print("\n4️⃣ Criando usuários...")
    
    from django.contrib.auth.models import User
    from core.models import ConfiguracaoUsuario
    
    # Superusuário
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema'
        )
        print("✅ Superusuário criado: admin / admin123")
    
    # Usuário de teste
    usuario_teste, created = User.objects.get_or_create(
        username='cliente1',
        defaults={
            'email': 'cliente1@example.com',
            'first_name': 'João',
            'last_name': 'Silva',
            'is_active': True
        }
    )
    
    if created:
        usuario_teste.set_password('cliente123')
        usuario_teste.save()
        print("✅ Cliente de teste criado: cliente1 / cliente123")
        
        # Cria configuração e planilha
        print("📊 Criando planilha para cliente de teste...")
        config = ConfiguracaoUsuario.objects.create(
            usuario=usuario_teste,
            nome_pagina_contatos="contatos",
            nome_pagina_mensagens="mensagem",
            coluna_nome="nome",
            coluna_numero="numero",
            coluna_enviado="enviado",
            coluna_mensagem="mensagem",
            coluna_quantidade="quantidade"
        )
        
        # Tenta criar planilha
        sucesso, mensagem = config.criar_planilha_automatica()
        if sucesso:
            print(f"✅ {mensagem}")
        else:
            print(f"⚠️ Erro ao criar planilha: {mensagem}")
    
    print("\n🎉 Sistema configurado com sucesso!")
    print("\n📋 Informações de acesso:")
    print("🌐 URL: http://localhost:8000")
    print("👤 Admin: admin / admin123")
    print("👤 Cliente: cliente1 / cliente123")
    print("\n🚀 Execute: python manage.py runserver")

if __name__ == '__main__':
    configurar_sistema()
