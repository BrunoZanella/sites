#!/usr/bin/env python
"""
Script para configurar o banco de dados inicial
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import execute_from_command_line

def setup_database():
    print("🚀 Configurando banco de dados...")
    
    # Fazer migrações
    print("📦 Aplicando migrações...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Criar superusuário se não existir
    if not User.objects.filter(is_superuser=True).exists():
        print("👤 Criando superusuário...")
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema'
        )
        print("✅ Superusuário criado: admin / admin123")
    else:
        print("ℹ️ Superusuário já existe")
    
    print("✅ Configuração do banco de dados concluída!")
    print("\n📋 Próximos passos:")
    print("1. Execute: python manage.py runserver")
    print("2. Acesse: http://localhost:8000")
    print("3. Faça login com: admin / admin123")

if __name__ == '__main__':
    setup_database()
