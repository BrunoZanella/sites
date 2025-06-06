# core/signals.py
import subprocess
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
import os

@receiver(post_save, sender=User)
def criar_codigo_disparo_ao_criar_usuario(sender, instance, created, **kwargs):
    if created:
        print(f"✅ Novo usuário criado: {instance.username}")

        # Caminho do script externo
        python_path = '/home/servidor/Documentos/apex_acesso_clientes/venv/bin/python'
        script_path = '/home/servidor/Documentos/apex_acesso_clientes/scripts/criar_disparo.py'

        try:
            # Executa o script
            result = subprocess.run(
                [python_path, script_path],
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "DJANGO_SETTINGS_MODULE": "whatsapp_automation.settings",
                    "PYTHONPATH": "/home/servidor/Documentos/apex_acesso_clientes"
                }
            )

            print("📤 Saída do script:")
            print(result.stdout)

            if result.stderr:
                print("⚠️ Erros do script:")
                print(result.stderr)

        except Exception as e:
            print(f"❌ Erro ao executar o script externo: {e}")
