#!/usr/bin/env python
"""
Script para resetar o banco de dados e aplicar as migrações
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')

def resetar_banco():
    print("🔄 Resetando banco de dados...")
    
    # Remove o banco SQLite se existir
    db_path = "db.sqlite3"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Banco de dados removido")
    
    # Remove arquivos de migração antigos
    migrations_dir = "core/migrations"
    if os.path.exists(migrations_dir):
        for file in os.listdir(migrations_dir):
            if file.endswith('.py') and file != '__init__.py':
                os.remove(os.path.join(migrations_dir, file))
                print(f"✅ Migração removida: {file}")
    
    print("🚀 Configurando Django...")
    django.setup()
    
    from django.core.management import execute_from_command_line
    from django.contrib.auth.models import User
    
    # Fazer migrações
    print("📦 Criando migrações...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    
    print("📦 Aplicando migrações...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Criar superusuário
    print("👤 Criando superusuário...")
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema'
        )
        print("✅ Superusuário criado: admin / admin123")
    
    # Criar usuário de teste
    print("👤 Criando usuário de teste...")
    usuario_teste, created = User.objects.get_or_create(
        username='teste',
        defaults={
            'email': 'teste@example.com',
            'first_name': 'Usuário',
            'last_name': 'Teste',
            'is_active': True
        }
    )
    
    if created:
        usuario_teste.set_password('teste123')
        usuario_teste.save()
        print("✅ Usuário de teste criado: teste / teste123")
    
    print("✅ Banco de dados resetado com sucesso!")
    print("\n📋 Próximos passos:")
    print("1. Execute: python manage.py runserver")
    print("2. Acesse: http://localhost:8000")
    print("3. Faça login com: admin / admin123 ou teste / teste123")

if __name__ == '__main__':
    resetar_banco()
