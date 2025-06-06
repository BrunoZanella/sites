from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro/', views.registro_view, name='registro'),
    
    # Dashboard principal
    path('', views.dashboard_view, name='dashboard'),
    
    # Configurações
    path('configuracao/', views.configuracao_view, name='configuracao'),
    
    # Contatos
    path('contatos/', views.contatos_view, name='contatos'),
    path('contatos/adicionar/', views.adicionar_contato_view, name='adicionar_contato'),
    path('contatos/upload/', views.upload_contatos_view, name='upload_contatos'),
    path('contatos/deletar/<int:pk>/', views.deletar_contato_view, name='deletar_contato'),
    
    # Mensagens
    path('mensagens/', views.mensagens_view, name='mensagens'),
    path('mensagens/adicionar/', views.adicionar_mensagem_view, name='adicionar_mensagem'),
    path('mensagens/editar/<int:pk>/', views.editar_mensagem_view, name='editar_mensagem'),
    path('mensagens/deletar/<int:pk>/', views.deletar_mensagem_view, name='deletar_mensagem'),
    
    # Superadmin - Dashboard
    path('superadmin/', views.superadmin_dashboard_view, name='superadmin_dashboard'),
    
    # Superadmin - Usuários
    path('superadmin/usuarios/', views.superadmin_usuarios_view, name='superadmin_usuarios'),
    path('superadmin/usuarios/criar/', views.criar_usuario_view, name='criar_usuario'),
    path('superadmin/usuarios/editar/<int:user_id>/', views.editar_usuario_view, name='editar_usuario'),
    path('superadmin/usuarios/<int:user_id>/', views.superadmin_usuario_detalhes_view, name='superadmin_usuario_detalhes'),
    path('superadmin/usuarios/<int:user_id>/deletar/', views.superadmin_deletar_usuario_view, name='superadmin_deletar_usuario'),
    
    # Minha Empresa
    path('superadmin/minha-empresa/', views.minha_empresa_view, name='minha_empresa'),
    
    # Gastos Fixos
    path('superadmin/gastos-fixos/', views.gastos_fixos_view, name='gastos_fixos'),
    path('superadmin/gastos-fixos/criar/', views.criar_gasto_fixo_view, name='criar_gasto_fixo'),
    path('superadmin/gastos-fixos/editar/<int:pk>/', views.editar_gasto_fixo_view, name='editar_gasto_fixo'),
    path('superadmin/gastos-fixos/deletar/<int:pk>/', views.deletar_gasto_fixo_view, name='deletar_gasto_fixo'),
    
    # Compras da Empresa
    path('superadmin/compras/', views.compras_empresa_view, name='compras_empresa'),
    path('superadmin/compras/criar/', views.criar_compra_empresa_view, name='criar_compra_empresa'),
    path('superadmin/compras/editar/<int:pk>/', views.editar_compra_empresa_view, name='editar_compra_empresa'),
    path('superadmin/compras/deletar/<int:pk>/', views.deletar_compra_empresa_view, name='deletar_compra_empresa'),
    
    # Clientes
    path('superadmin/clientes/', views.clientes_view, name='clientes'),
    path('superadmin/clientes/criar/', views.criar_cliente_view, name='criar_cliente'),
    path('superadmin/clientes/editar/<int:pk>/', views.editar_cliente_view, name='editar_cliente'),
    path('superadmin/clientes/deletar/<int:pk>/', views.deletar_cliente_view, name='deletar_cliente'),
    
    # Projetos
    path('superadmin/projetos/', views.projetos_view, name='projetos'),
    path('superadmin/projetos/criar/', views.criar_projeto_view, name='criar_projeto'),
    path('superadmin/projetos/editar/<int:pk>/', views.editar_projeto_view, name='editar_projeto'),
    path('superadmin/projetos/deletar/<int:pk>/', views.deletar_projeto_view, name='deletar_projeto'),
    
    # Serviços de Hospedagem
    path('superadmin/hospedagem/', views.servicos_hospedagem_view, name='servicos_hospedagem'),
    path('superadmin/hospedagem/criar/', views.criar_servico_hospedagem_view, name='criar_servico_hospedagem'),
    path('superadmin/hospedagem/editar/<int:pk>/', views.editar_servico_hospedagem_view, name='editar_servico_hospedagem'),
    path('superadmin/hospedagem/deletar/<int:pk>/', views.deletar_servico_hospedagem_view, name='deletar_servico_hospedagem'),
    
    # Dashboard Financeiro
    path('superadmin/dashboard-financeiro/', views.dashboard_financeiro_view, name='dashboard_financeiro'),
    
    # Notificações
    path('superadmin/notificacoes/', views.notificacoes_view, name='notificacoes'),
    path('superadmin/notificacoes/marcar-lida/<int:pk>/', views.marcar_notificacao_lida_view, name='marcar_notificacao_lida'),
]
