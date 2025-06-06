#!/usr/bin/env python
"""
Script para criar dados de exemplo no sistema
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import ConfiguracaoUsuario, Contato, Mensagem

def criar_dados_exemplo():
    print("📊 Criando dados de exemplo...")
    
    # Criar usuário de teste
    usuario_teste, created = User.objects.get_or_create(
        username='usuario_teste',
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
        print("✅ Usuário de teste criado: usuario_teste / teste123")
    
    # Criar configuração
    config, created = ConfiguracaoUsuario.objects.get_or_create(
        usuario=usuario_teste,
        defaults={
            'nome_tabela_sheets': 'Planilha WhatsApp Teste',
            'nome_pagina_contatos': 'contatos',
            'nome_pagina_mensagens': 'mensagens',
            'coluna_nome': 'nome',
            'coluna_numero': 'numero',
            'coluna_enviado': 'enviado',
            'coluna_mensagem': 'mensagem',
            'coluna_quantidade': 'quantidade'
        }
    )
    
    if created:
        print("✅ Configuração criada para usuário de teste")
    
    # Criar contatos de exemplo
    contatos_exemplo = [
        {'nome': 'João Silva', 'numero': '5511999999999', 'enviado': False},
        {'nome': 'Maria Santos', 'numero': '5511888888888', 'enviado': True},
        {'nome': 'Pedro Oliveira', 'numero': '5511777777777', 'enviado': False},
        {'nome': 'Ana Costa', 'numero': '5511666666666', 'enviado': True},
        {'nome': 'Carlos Ferreira', 'numero': '5511555555555', 'enviado': False},
    ]
    
    for contato_data in contatos_exemplo:
        contato, created = Contato.objects.get_or_create(
            usuario=usuario_teste,
            numero=contato_data['numero'],
            defaults={
                'nome': contato_data['nome'],
                'enviado': contato_data['enviado'],
                'data_envio': datetime.now() - timedelta(days=1) if contato_data['enviado'] else None
            }
        )
        if created:
            print(f"✅ Contato criado: {contato_data['nome']}")
    
    # Criar mensagens de exemplo
    mensagens_exemplo = [
        {
            'texto_mensagem': 'Olá! Esta é
