"""
Script para testar a criação de codigo de dispato automaticamente
"""

import os
import sys
import django

from django.contrib.auth.models import User
from core.models import ConfiguracaoUsuario

def criar_disparo():

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
            return
        

        print(config)
        # criar pasta de usuario em /home/servidor/Documentos/apex_acesso_clientes/usuarios/{usuario.username}
        

    except Exception as e:
        print(f"❌ Erro ao buscar configuração: {e}")
        return  




if __name__ == '__main__':
    criar_disparo()
    print("🧪 Testando criação automática de disparo...")