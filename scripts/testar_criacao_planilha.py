#!/usr/bin/env python
"""
Script para testar a criação automática de planilhas
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import ConfiguracaoUsuario

def testar_criacao():
    print("🧪 Testando criação automática de planilhas...")
    
    # Verifica se existe o arquivo de credenciais
    from django.conf import settings
    credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")
    
    if not os.path.exists(credentials_path):
        print("❌ Arquivo credentials.json não encontrado!")
        print("Execute primeiro: python scripts/configurar_credenciais.py")
        return
    
    print("✅ Arquivo de credenciais encontrado")
    
    # Busca usuários para testar
    usuarios = User.objects.filter(is_superuser=False)[:3]
    
    if not usuarios:
        print("❌ Nenhum usuário encontrado para teste")
        print("Crie alguns usuários primeiro")
        return
    
    print(f"👥 Encontrados {len(usuarios)} usuários para teste")
    
    for usuario in usuarios:
        print(f"\n🔄 Testando usuário: {usuario.username}")
        
        # Busca ou cria configuração
        config, created = ConfiguracaoUsuario.objects.get_or_create(
            usuario=usuario,
            defaults={
                'nome_pagina_contatos': 'contatos',
                'nome_pagina_mensagens': 'mensagem',
                'coluna_nome': 'nome',
                'coluna_numero': 'numero',
                'coluna_enviado': 'enviado',
                'coluna_mensagem': 'mensagem',
                'coluna_quantidade': 'quantidade'
            }
        )
        
        if config.planilha_criada:
            print(f"ℹ️ Usuário já tem planilha: {config.nome_tabela_sheets}")
            print(f"🔗 URL: {config.url_planilha}")
        else:
            print("🚀 Criando planilha...")
            sucesso, mensagem = config.criar_planilha_automatica()
            
            if sucesso:
                print(f"✅ {mensagem}")
                print(f"🔗 URL: {config.url_planilha}")
            else:
                print(f"❌ Erro: {mensagem}")

if __name__ == '__main__':
    testar_criacao()
