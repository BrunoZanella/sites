#!/usr/bin/env python
"""
Script para testar a criação de planilhas automaticamente
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_automation.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import ConfiguracaoUsuario

def testar_criacao_planilha():
    print("🧪 Testando criação automática de planilha...")
    
    # Busca um usuário de teste
    try:
        usuario = User.objects.get(username='usuario_teste')
        print(f"✅ Usuário encontrado: {usuario.username}")
    except User.DoesNotExist:
        print("❌ Usuário de teste não encontrado. Execute primeiro o script criar_dados_exemplo.py")
        return
    
    # Busca a configuração
    try:
        config = ConfiguracaoUsuario.objects.get(usuario=usuario)
        print(f"✅ Configuração encontrada para: {config.usuario.username}")
        
        # Verifica se tem credenciais
        if not config.arquivo_credenciais:
            print("⚠️ Arquivo de credenciais não configurado.")
            print("📋 Para testar a criação automática:")
            print("1. Faça login no sistema")
            print("2. Vá em Configurações")
            print("3. Faça upload do arquivo JSON de credenciais do Google")
            print("4. A planilha será criada automaticamente!")
            return
        
        # Tenta criar a planilha
        print("🚀 Tentando criar planilha...")
        sucesso, mensagem = config.criar_planilha_automatica()
        
        if sucesso:
            print(f"✅ {mensagem}")
            print(f"📊 Nome da planilha: {config.nome_tabela_sheets}")
            print("📋 Estrutura criada:")
            print(f"   - Aba '{config.nome_pagina_contatos}' com colunas: {config.coluna_nome}, {config.coluna_numero}, {config.coluna_enviado}")
            print(f"   - Aba '{config.nome_pagina_mensagens}' com colunas: {config.coluna_mensagem}, {config.coluna_quantidade}")
        else:
            print(f"❌ Erro: {mensagem}")
            
    except ConfiguracaoUsuario.DoesNotExist:
        print("❌ Configuração não encontrada para o usuário")

if __name__ == '__main__':
    testar_criacao_planilha()
