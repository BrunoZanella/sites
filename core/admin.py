from django.contrib import admin
from .models import (
    ConfiguracaoUsuario, Contato, Mensagem, LogEnvio,
    GastoFixo, CompraEmpresa, Cliente, Projeto, 
    ServicoHospedagem, Notificacao
)

@admin.register(ConfiguracaoUsuario)
class ConfiguracaoUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'nome_tabela_sheets', 'automacao_ativa', 'data_criacao']
    list_filter = ['automacao_ativa', 'data_criacao']
    search_fields = ['usuario__username', 'nome_tabela_sheets']
    readonly_fields = ['data_criacao']

@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'numero', 'usuario', 'enviado', 'data_criacao']
    list_filter = ['enviado', 'data_criacao', 'usuario']
    search_fields = ['nome', 'numero']
    readonly_fields = ['data_criacao']

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'texto_mensagem_preview', 'quantidade_envios', 'quantidade_maxima', 'ativa']
    list_filter = ['ativa', 'data_criacao', 'usuario']
    search_fields = ['texto_mensagem']
    readonly_fields = ['data_criacao']
    
    def texto_mensagem_preview(self, obj):
        return obj.texto_mensagem[:50] + "..." if len(obj.texto_mensagem) > 50 else obj.texto_mensagem
    texto_mensagem_preview.short_description = "Mensagem"

@admin.register(LogEnvio)
class LogEnvioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'contato', 'status', 'data_tentativa']
    list_filter = ['status', 'data_tentativa', 'usuario']
    search_fields = ['contato__nome', 'contato__numero']
    readonly_fields = ['data_tentativa']
    date_hierarchy = 'data_tentativa'

# Administração da Empresa
@admin.register(GastoFixo)
class GastoFixoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'valor', 'dia_vencimento', 'ativo']
    list_filter = ['categoria', 'ativo', 'data_criacao']
    search_fields = ['nome', 'descricao']
    readonly_fields = ['data_criacao']

@admin.register(CompraEmpresa)
class CompraEmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'valor', 'status', 'data_compra']
    list_filter = ['categoria', 'status', 'data_compra']
    search_fields = ['nome', 'fornecedor']
    readonly_fields = ['data_criacao']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'nome_empresa', 'contato_principal', 'telefone', 'data_criacao']
    list_filter = ['data_criacao']
    search_fields = ['usuario__username', 'nome_empresa', 'contato_principal']
    readonly_fields = ['data_criacao']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('usuario',)
        }),
        ('Informações da Empresa', {
            'fields': ('nome_empresa', 'contato_principal', 'telefone', 'email_contato')
        }),
        ('Endereço', {
            'fields': ('endereco',),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('data_criacao',),
            'classes': ('collapse',)
        })
    )

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cliente', 'valor_total', 'status', 'data_inicio', 'data_conclusao']
    list_filter = ['status', 'tipo_pagamento', 'data_inicio']
    search_fields = ['nome', 'cliente__usuario__username']
    readonly_fields = ['data_criacao']
    date_hierarchy = 'data_inicio'

@admin.register(ServicoHospedagem)
class ServicoHospedagemAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cliente', 'tipo', 'valor_mensal', 'status', 'data_inicio']
    list_filter = ['tipo', 'status', 'data_inicio']
    search_fields = ['nome', 'cliente__usuario__username', 'provedor']
    readonly_fields = ['data_criacao']

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'lida', 'data_criacao']
    list_filter = ['tipo', 'lida', 'data_criacao']
    search_fields = ['titulo', 'mensagem']
    readonly_fields = ['data_criacao']
    date_hierarchy = 'data_criacao'
    
    actions = ['marcar_como_lida', 'marcar_como_nao_lida']
    
    def marcar_como_lida(self, request, queryset):
        queryset.update(lida=True)
        self.message_user(request, f"{queryset.count()} notificações marcadas como lidas.")
    marcar_como_lida.short_description = "Marcar como lida"
    
    def marcar_como_nao_lida(self, request, queryset):
        queryset.update(lida=False)
        self.message_user(request, f"{queryset.count()} notificações marcadas como não lidas.")
    marcar_como_nao_lida.short_description = "Marcar como não lida"

# Configurações do Admin
admin.site.site_header = "WhatsApp Automation - Administração"
admin.site.site_title = "WA Admin"
admin.site.index_title = "Painel de Administração"
