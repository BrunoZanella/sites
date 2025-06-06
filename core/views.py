from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg, F, Case, When, Value, DecimalField
from django.utils import timezone
from django.urls import reverse
from .models import ConfiguracaoUsuario, Contato, Mensagem, LogEnvio
from .forms import RegistroUsuarioForm, ConfiguracaoUsuarioForm, UploadContatosForm, ContatoForm, MensagemForm
import pandas as pd
import json
import tempfile
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

def is_superuser(user):
    return user.is_superuser

def registro_view(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Define como cliente por padrão (não staff, não superuser)
            user.is_staff = False
            user.is_superuser = False
            user.save()
            
            username = form.cleaned_data.get('username')
            
            # Cria configuração padrão para o usuário
            configuracao = ConfiguracaoUsuario.objects.create(
                usuario=user,
                nome_tabela_sheets="",
                nome_pagina_contatos="contatos",
                nome_pagina_mensagens="mensagem",
                coluna_nome="nome",
                coluna_numero="numero",
                coluna_enviado="enviado",
                coluna_mensagem="mensagem",
                coluna_quantidade="quantidade"
            )
            
            # Tenta criar a planilha automaticamente
            sucesso, mensagem = configuracao.criar_planilha_automatica()
            
            if sucesso:
                messages.success(request, f'Conta criada para {username}! Sua planilha foi criada automaticamente.')
                messages.info(request, f'Planilha: {mensagem}')
            else:
                messages.success(request, f'Conta criada para {username}!')
                messages.warning(request, f'Não foi possível criar a planilha automaticamente: {mensagem}')
            
            return redirect('login')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'registration/registro.html', {'form': form})

@login_required
def dashboard_view(request):
    # Estatísticas do usuário
    total_contatos = Contato.objects.filter(usuario=request.user).count()
    contatos_enviados = Contato.objects.filter(usuario=request.user, enviado=True).count()
    contatos_pendentes = total_contatos - contatos_enviados
    total_mensagens = Mensagem.objects.filter(usuario=request.user).count()
    
    # Mensagens recentes
    mensagens_recentes = Mensagem.objects.filter(usuario=request.user).order_by('-data_criacao')[:5]
    
    # Contatos recentes
    contatos_recentes = Contato.objects.filter(usuario=request.user).order_by('-data_criacao')[:10]
    
    # Logs recentes
    logs_recentes = LogEnvio.objects.filter(usuario=request.user).order_by('-data_tentativa')[:10]
    
    context = {
        'total_contatos': total_contatos,
        'contatos_enviados': contatos_enviados,
        'contatos_pendentes': contatos_pendentes,
        'total_mensagens': total_mensagens,
        'mensagens_recentes': mensagens_recentes,
        'contatos_recentes': contatos_recentes,
        'logs_recentes': logs_recentes,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def configuracao_view(request):
    configuracao, created = ConfiguracaoUsuario.objects.get_or_create(usuario=request.user)
    
    if request.method == 'POST':
        # Verifica se é para criar planilha
        if 'criar_planilha' in request.POST:
            sucesso, mensagem = configuracao.criar_planilha_automatica()
            if sucesso:
                messages.success(request, f'Planilha criada com sucesso! {mensagem}')
            else:
                messages.error(request, f'Erro ao criar planilha: {mensagem}')
            return redirect('configuracao')
        
        # Verifica se é para sincronizar contatos
        if 'sincronizar_contatos' in request.POST:
            sucesso, mensagem = configuracao.sincronizar_contatos()
            if sucesso:
                messages.success(request, f'Contatos sincronizados! {mensagem}')
            else:
                messages.error(request, f'Erro ao sincronizar: {mensagem}')
            return redirect('configuracao')
        
        # Verifica se é para alterar automação
        if 'automacao_ativa' in request.POST:
            configuracao.automacao_ativa = True
        else:
            configuracao.automacao_ativa = False
        
        configuracao.save()
        
        # Se for requisição AJAX, retorna JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'automacao_ativa': configuracao.automacao_ativa
            })
        
        messages.success(request, 'Configurações salvas com sucesso!')
        return redirect('configuracao')
    
    # Estatísticas para os cards
    total_contatos = Contato.objects.filter(usuario=request.user).count()
    total_mensagens = Mensagem.objects.filter(usuario=request.user).count()
    
    context = {
        'configuracao': configuracao,
        'total_contatos': total_contatos,
        'total_mensagens': total_mensagens,
    }
    return render(request, 'core/configuracao.html', context)

@login_required
def contatos_view(request):
    contatos_list = Contato.objects.filter(usuario=request.user).order_by('-data_criacao')
    
    # Filtros
    busca = request.GET.get('busca')
    status = request.GET.get('status')
    
    if busca:
        contatos_list = contatos_list.filter(
            Q(nome__icontains=busca) | Q(numero__icontains=busca)
        )
    
    if status == 'enviado':
        contatos_list = contatos_list.filter(enviado=True)
    elif status == 'pendente':
        contatos_list = contatos_list.filter(enviado=False)
    
    # Paginação
    paginator = Paginator(contatos_list, 20)
    page_number = request.GET.get('page')
    contatos = paginator.get_page(page_number)
    
    return render(request, 'core/contatos.html', {
        'contatos': contatos,
        'busca': busca,
        'status': status,
    })

@login_required
def adicionar_contato_view(request):
    if request.method == 'POST':
        form = ContatoForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.usuario = request.user
            
            # Normaliza o número
            numero_limpo = ''.join(filter(str.isdigit, contato.numero))
            
            # Verifica se já existe (busca mais flexível)
            if Contato.objects.filter(
                usuario=request.user
            ).filter(
                Q(numero=contato.numero) | Q(numero=numero_limpo) | Q(numero__contains=numero_limpo[-8:])
            ).exists():
                messages.error(request, 'Já existe um contato com este número!')
                return render(request, 'core/adicionar_contato.html', {'form': form})
            
            # Define o número limpo
            contato.numero = numero_limpo
            contato.save()
            messages.success(request, 'Contato adicionado com sucesso!')
            
            # Sincroniza automaticamente com a planilha
            try:
                configuracao = ConfiguracaoUsuario.objects.get(usuario=request.user)
                if configuracao.planilha_criada:
                    configuracao.sincronizar_contatos()
            except:
                pass
            
            return redirect('contatos')
    else:
        form = ContatoForm()
    
    return render(request, 'core/adicionar_contato.html', {'form': form})

@login_required
def upload_contatos_view(request):
    if request.method == 'POST':
        # Verifica se é o primeiro POST (upload do arquivo)
        if 'arquivo' in request.FILES:
            form = UploadContatosForm(request.POST, request.FILES)
            if form.is_valid():
                arquivo = request.FILES['arquivo']
                
                try:
                    # Lê o arquivo
                    if arquivo.name.endswith('.csv'):
                        df = pd.read_csv(arquivo)
                    else:
                        df = pd.read_excel(arquivo)
                    
                    # Limita a 5 linhas para preview
                    df_preview = df.head(5)
                    
                    # Converte para formato que pode ser serializado
                    colunas = df.columns.tolist()
                    linhas = []
                    
                    for index, row in df_preview.iterrows():
                        linha = []
                        for col in colunas:
                            valor = row[col]
                            if pd.isna(valor):
                                linha.append('')
                            else:
                                linha.append(str(valor))
                        linhas.append(linha)
                    
                    # Salva o arquivo temporariamente
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo.name)[1]) as tmp:
                        for chunk in arquivo.chunks():
                            tmp.write(chunk)
                        temp_path = tmp.name
                    
                    # Salva o caminho na sessão
                    request.session['upload_temp_file'] = temp_path
                    
                    # Obtém configuração do usuário para sugestões
                    try:
                        config = ConfiguracaoUsuario.objects.get(usuario=request.user)
                        sugestoes = {
                            'nome': config.coluna_nome,
                            'numero': config.coluna_numero,
                            'enviado': config.coluna_enviado
                        }
                    except ConfiguracaoUsuario.DoesNotExist:
                        sugestoes = {
                            'nome': 'nome',
                            'numero': 'numero',
                            'enviado': 'enviado'
                        }
                    
                    # Se for uma requisição AJAX, retorna JSON
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in request.META:
                        return JsonResponse({
                            'success': True,
                            'colunas': colunas,
                            'linhas': linhas,
                            'arquivo_nome': arquivo.name,
                            'total_linhas': len(df),
                            'sugestoes': sugestoes
                        })
                    
                    # Caso contrário, renderiza a página de preview
                    return render(request, 'core/upload_contatos_preview.html', {
                        'colunas': colunas,
                        'linhas': linhas,
                        'arquivo_nome': arquivo.name,
                        'total_linhas': len(df),
                        'sugestoes': sugestoes
                    })
                    
                except Exception as e:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in request.META:
                        return JsonResponse({
                            'success': False,
                            'error': str(e)
                        })
                    messages.error(request, f'Erro ao processar arquivo: {str(e)}')
        
        # Segundo POST (processamento com colunas selecionadas)
        elif 'processar_dados' in request.POST:
            # Obtém as colunas selecionadas
            coluna_nome = request.POST.get('coluna_nome')
            coluna_numero = request.POST.get('coluna_numero')
            coluna_enviado = request.POST.get('coluna_enviado')
            
            # Obtém o mapeamento de colunas (se disponível)
            mapeamento_colunas = {}
            try:
                mapeamento_json = request.POST.get('mapeamento_colunas')
                if mapeamento_json:
                    mapeamento_colunas = json.loads(mapeamento_json)
            except:
                pass
            
            if not coluna_nome or not coluna_numero:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in request.META:
                    return JsonResponse({
                        'success': False,
                        'error': 'Selecione pelo menos as colunas de Nome e Número.'
                    })
                messages.error(request, 'Selecione pelo menos as colunas de Nome e Número.')
                return redirect('upload_contatos')
            
            try:
                # Recupera o arquivo temporário
                temp_path = request.session.get('upload_temp_file')
                if not temp_path or not os.path.exists(temp_path):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in request.META:
                        return JsonResponse({
                            'success': False,
                            'error': 'Arquivo temporário não encontrado. Faça o upload novamente.'
                        })
                    messages.error(request, 'Arquivo temporário não encontrado. Faça o upload novamente.')
                    return redirect('upload_contatos')
                
                # Lê o arquivo
                if temp_path.endswith('.csv'):
                    df = pd.read_csv(temp_path)
                else:
                    df = pd.read_excel(temp_path)
                
                # Processa os dados
                contatos_criados = 0
                contatos_ignorados = 0
                
                # Função para normalizar números
                def normalizar_numero(numero):
                    return ''.join(filter(str.isdigit, str(numero)))
                
                # Obtém todos os números existentes para verificação rápida
                numeros_existentes = set(
                    Contato.objects.filter(usuario=request.user).values_list('numero', flat=True)
                )
                
                for index, row in df.iterrows():
                    try:
                        # Obtém os valores das colunas selecionadas
                        nome = str(row[coluna_nome]).strip()
                        numero = str(row[coluna_numero]).strip()
                        
                        if pd.isna(nome) or pd.isna(numero) or not nome or not numero or nome == 'nan' or numero == 'nan':
                            continue
                        
                        # Normaliza o número
                        numero_limpo = normalizar_numero(numero)
                        if not numero_limpo:
                            continue
                        
                        # Verifica se foi enviado
                        ja_enviado = False
                        if coluna_enviado and coluna_enviado in df.columns:
                            enviado_valor = row[coluna_enviado]
                            if not pd.isna(enviado_valor):
                                enviado_str = str(enviado_valor).lower()
                                ja_enviado = enviado_str in ['1', 'true', 'sim', 'yes', 'y', 's', 't']
                        
                        # Verifica se o contato já existe
                        if numero_limpo in numeros_existentes:
                            # Pula contatos existentes sem atualizar
                            contatos_ignorados += 1
                            print(f"Ignorando contato existente: {nome} - {numero_limpo}")
                            continue
                        
                        # Cria novo contato
                        Contato.objects.create(
                            usuario=request.user,
                            numero=numero_limpo,
                            nome=nome,
                            enviado=ja_enviado,
                            data_envio=timezone.now() if ja_enviado else None
                        )
                        contatos_criados += 1
                        print(f"Contato criado: {nome} - {numero_limpo} - Enviado: {ja_enviado}")
                            
                    except Exception as e:
                        print(f"Erro ao processar linha {index}: {str(e)}")
                        continue
                
                # Sincroniza com a planilha
                try:
                    config = ConfiguracaoUsuario.objects.get(usuario=request.user)
                    if config.planilha_criada:
                        config.sincronizar_contatos()
                except Exception as e:
                    print(f"Erro ao sincronizar contatos: {str(e)}")
                
                # Remove o arquivo temporário
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
                # Limpa a sessão
                if 'upload_temp_file' in request.session:
                    del request.session['upload_temp_file']
                
                # Responde de acordo com o tipo de requisição
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in request.META:
                    return JsonResponse({
                        'success': True,
                        'message': f'Upload concluído! {contatos_criados} contatos criados, {contatos_ignorados} ignorados (já existentes).',
                        'redirect_url': reverse('contatos')
                    })
                
                messages.success(request, f'Upload concluído! {contatos_criados} contatos criados, {contatos_ignorados} ignorados (já existentes).')
                return redirect('contatos')
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'HTTP_X_REQUESTED_WITH' in request.META:
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    })
                messages.error(request, f'Erro ao processar dados: {str(e)}')
                return redirect('upload_contatos')
    
    form = UploadContatosForm()
    return render(request, 'core/upload_contatos.html', {'form': form})

@login_required
def mensagens_view(request):
    mensagens_list = Mensagem.objects.filter(usuario=request.user).order_by('-data_criacao')
    
    # Paginação
    paginator = Paginator(mensagens_list, 10)
    page_number = request.GET.get('page')
    mensagens = paginator.get_page(page_number)
    
    return render(request, 'core/mensagens.html', {'mensagens': mensagens})

@login_required
def adicionar_mensagem_view(request):
    if request.method == 'POST':
        form = MensagemForm(request.POST)
        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.usuario = request.user
            mensagem.save()
            messages.success(request, 'Mensagem criada com sucesso!')
            return redirect('mensagens')
    else:
        form = MensagemForm()
    
    return render(request, 'core/adicionar_mensagem.html', {'form': form})

@login_required
def editar_mensagem_view(request, pk):
    mensagem = get_object_or_404(Mensagem, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        form = MensagemForm(request.POST, instance=mensagem)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mensagem atualizada com sucesso!')
            return redirect('mensagens')
    else:
        form = MensagemForm(instance=mensagem)
    
    return render(request, 'core/editar_mensagem.html', {'form': form, 'mensagem': mensagem})

@login_required
def deletar_contato_view(request, pk):
    contato = get_object_or_404(Contato, pk=pk, usuario=request.user)
    if request.method == 'POST':
        contato.delete()
        
        # Sincroniza automaticamente com a planilha
        try:
            configuracao = ConfiguracaoUsuario.objects.get(usuario=request.user)
            if configuracao.planilha_criada:
                configuracao.sincronizar_contatos()
        except:
            pass
        
        messages.success(request, 'Contato deletado com sucesso!')
    return redirect('contatos')

@login_required
def deletar_mensagem_view(request, pk):
    mensagem = get_object_or_404(Mensagem, pk=pk, usuario=request.user)
    if request.method == 'POST':
        mensagem.delete()
        messages.success(request, 'Mensagem deletada com sucesso!')
    return redirect('mensagens')

# Views de Superadmin
@user_passes_test(is_superuser)
def superadmin_dashboard_view(request):
    total_usuarios = User.objects.count()
    total_contatos = Contato.objects.count()
    total_mensagens = Mensagem.objects.count()
    total_logs = LogEnvio.objects.count()
    
    # Usuários recentes
    usuarios_recentes = User.objects.order_by('-date_joined')[:10]
    
    context = {
        'total_usuarios': total_usuarios,
        'total_contatos': total_contatos,
        'total_mensagens': total_mensagens,
        'total_logs': total_logs,
        'usuarios_recentes': usuarios_recentes,
    }
    return render(request, 'core/superadmin/dashboard.html', context)

@user_passes_test(is_superuser)
def superadmin_usuarios_view(request):
    usuarios_list = User.objects.all().order_by('-date_joined')
    
    # Busca
    busca = request.GET.get('busca')
    if busca:
        usuarios_list = usuarios_list.filter(
            Q(username__icontains=busca) | 
            Q(email__icontains=busca) | 
            Q(first_name__icontains=busca) | 
            Q(last_name__icontains=busca)
        )
    
    # Paginação
    paginator = Paginator(usuarios_list, 20)
    page_number = request.GET.get('page')
    usuarios = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/usuarios.html', {
        'usuarios': usuarios,
        'busca': busca,
    })

@user_passes_test(is_superuser)
def superadmin_usuario_detalhes_view(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    
    try:
        configuracao = ConfiguracaoUsuario.objects.get(usuario=usuario)
    except ConfiguracaoUsuario.DoesNotExist:
        configuracao = None
    
    contatos = Contato.objects.filter(usuario=usuario).order_by('-data_criacao')[:10]
    mensagens = Mensagem.objects.filter(usuario=usuario).order_by('-data_criacao')[:10]
    logs = LogEnvio.objects.filter(usuario=usuario).order_by('-data_tentativa')[:10]
    
    # Estatísticas
    stats = {
        'total_contatos': Contato.objects.filter(usuario=usuario).count(),
        'contatos_enviados': Contato.objects.filter(usuario=usuario, enviado=True).count(),
        'total_mensagens': Mensagem.objects.filter(usuario=usuario).count(),
        'total_logs': LogEnvio.objects.filter(usuario=usuario).count(),
    }
    
    context = {
        'usuario': usuario,
        'configuracao': configuracao,
        'contatos': contatos,
        'mensagens': mensagens,
        'logs': logs,
        'stats': stats,
    }
    return render(request, 'core/superadmin/usuario_detalhes.html', context)

@user_passes_test(is_superuser)
def superadmin_deletar_usuario_view(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        if usuario.is_superuser:
            messages.error(request, 'Não é possível deletar um superusuário!')
        else:
            username = usuario.username
            usuario.delete()
            messages.success(request, f'Usuário {username} deletado com sucesso!')
        return redirect('superadmin_usuarios')
    
    return render(request, 'core/superadmin/confirmar_deletar_usuario.html', {'usuario': usuario})

# Views de Gestão Empresarial
@user_passes_test(is_superuser)
def minha_empresa_view(request):
    from django.db.models import Sum
    from .models import GastoFixo, CompraEmpresa, Projeto, ServicoHospedagem, Notificacao
    from datetime import datetime, timedelta, date
    
    # Estatísticas
    total_gastos_fixos = GastoFixo.objects.filter(ativo=True).aggregate(Sum('valor'))['valor__sum'] or 0
    total_gastos_fixos_count = GastoFixo.objects.filter(ativo=True).count()
    
    total_compras = CompraEmpresa.objects.aggregate(Sum('valor'))['valor__sum'] or 0
    total_compras_count = CompraEmpresa.objects.count()
    
    total_receita_projetos = Projeto.objects.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_projetos_count = Projeto.objects.count()
    
    total_hospedagem_mensal = ServicoHospedagem.objects.filter(status='ativo').aggregate(Sum('valor_mensal'))['valor_mensal__sum'] or 0
    total_hospedagem_count = ServicoHospedagem.objects.filter(status='ativo').count()
    
    # Alertas
    hoje = timezone.now().date()
    proximos_7_dias = hoje + timedelta(days=7)
    
    # Parcelas vencendo (simulação - você pode implementar um modelo de Parcela depois)
    parcelas_vencendo = 0
    parcelas_vencidas = 0
    
    # Hospedagem vencendo
    hospedagem_vencendo = ServicoHospedagem.objects.filter(
        status='ativo',
        data_fim__lte=proximos_7_dias,
        data_fim__gte=hoje
    ).count()
    
    # Notificações não lidas
    notificacoes_nao_lidas = Notificacao.objects.filter(lida=False).count()
    
    context = {
        'total_gastos_fixos': total_gastos_fixos,
        'total_gastos_fixos_count': total_gastos_fixos_count,
        'total_compras': total_compras,
        'total_compras_count': total_compras_count,
        'total_receita_projetos': total_receita_projetos,
        'total_projetos_count': total_projetos_count,
        'total_hospedagem_mensal': total_hospedagem_mensal,
        'total_hospedagem_count': total_hospedagem_count,
        'parcelas_vencendo': parcelas_vencendo,
        'parcelas_vencidas': parcelas_vencidas,
        'hospedagem_vencendo': hospedagem_vencendo,
        'notificacoes_nao_lidas': notificacoes_nao_lidas,
    }
    return render(request, 'core/superadmin/minha_empresa.html', context)

@user_passes_test(is_superuser)
def dashboard_financeiro_view(request):
    from django.db.models import Sum, Avg, Count, F, Q, Case, When, Value, DecimalField
    from .models import GastoFixo, CompraEmpresa, Projeto, ServicoHospedagem, Cliente, ParcelaProjeto
    import json
    from datetime import datetime, timedelta, date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal
    
    # Datas de referência
    hoje = timezone.now().date()
    
    # Parâmetros de filtro
    periodo = request.GET.get('periodo', 'mes_atual')
    comparacao = request.GET.get('comparacao', 'anterior')
    data_inicio_param = request.GET.get('data_inicio')
    data_fim_param = request.GET.get('data_fim')
    
    # Definir período baseado no filtro
    if periodo == 'mes_atual':
        inicio_periodo = hoje.replace(day=1)
        fim_periodo = (inicio_periodo + relativedelta(months=1)) - timedelta(days=1)
        periodo_label = "Este Mês"
    elif periodo == 'mes_anterior':
        inicio_periodo = (hoje.replace(day=1) - relativedelta(months=1))
        fim_periodo = hoje.replace(day=1) - timedelta(days=1)
        periodo_label = "Mês Anterior"
    elif periodo == 'trimestre_atual':
        mes_atual = hoje.month
        inicio_trimestre = ((mes_atual - 1) // 3) * 3 + 1
        inicio_periodo = hoje.replace(month=inicio_trimestre, day=1)
        fim_periodo = (inicio_periodo + relativedelta(months=3)) - timedelta(days=1)
        periodo_label = "Este Trimestre"
    elif periodo == 'trimestre_anterior':
        mes_atual = hoje.month
        inicio_trimestre_atual = ((mes_atual - 1) // 3) * 3 + 1
        inicio_periodo = hoje.replace(month=inicio_trimestre_atual, day=1) - relativedelta(months=3)
        fim_periodo = hoje.replace(month=inicio_trimestre_atual, day=1) - timedelta(days=1)
        periodo_label = "Trimestre Anterior"
    elif periodo == 'semestre_atual':
        if hoje.month <= 6:
            inicio_periodo = hoje.replace(month=1, day=1)
            fim_periodo = hoje.replace(month=6, day=30)
        else:
            inicio_periodo = hoje.replace(month=7, day=1)
            fim_periodo = hoje.replace(month=12, day=31)
        periodo_label = "Este Semestre"
    elif periodo == 'ano_atual':
        inicio_periodo = hoje.replace(month=1, day=1)
        fim_periodo = hoje.replace(month=12, day=31)
        periodo_label = "Este Ano"
    elif periodo == 'ano_anterior':
        inicio_periodo = hoje.replace(year=hoje.year-1, month=1, day=1)
        fim_periodo = hoje.replace(year=hoje.year-1, month=12, day=31)
        periodo_label = "Ano Anterior"
    elif periodo == 'personalizado' and data_inicio_param and data_fim_param:
        inicio_periodo = datetime.strptime(data_inicio_param, '%Y-%m-%d').date()
        fim_periodo = datetime.strptime(data_fim_param, '%Y-%m-%d').date()
        periodo_label = f"{inicio_periodo.strftime('%d/%m/%Y')} - {fim_periodo.strftime('%d/%m/%Y')}"
    else:
        # Padrão: mês atual
        inicio_periodo = hoje.replace(day=1)
        fim_periodo = (inicio_periodo + relativedelta(months=1)) - timedelta(days=1)
        periodo_label = "Este Mês"
    
    # Definir período de comparação
    if comparacao == 'anterior':
        if periodo in ['mes_atual', 'mes_anterior']:
            inicio_comparacao = inicio_periodo - relativedelta(months=1)
            fim_comparacao = fim_periodo - relativedelta(months=1)
            comparacao_label = "mês anterior"
        elif periodo in ['trimestre_atual', 'trimestre_anterior']:
            inicio_comparacao = inicio_periodo - relativedelta(months=3)
            fim_comparacao = fim_periodo - relativedelta(months=3)
            comparacao_label = "trimestre anterior"
        elif periodo == 'semestre_atual':
            inicio_comparacao = inicio_periodo - relativedelta(months=6)
            fim_comparacao = fim_periodo - relativedelta(months=6)
            comparacao_label = "semestre anterior"
        else:
            inicio_comparacao = inicio_periodo - relativedelta(years=1)
            fim_comparacao = fim_periodo - relativedelta(years=1)
            comparacao_label = "ano anterior"
    elif comparacao == 'ano_anterior':
        inicio_comparacao = inicio_periodo.replace(year=inicio_periodo.year-1)
        fim_comparacao = fim_periodo.replace(year=fim_periodo.year-1)
        comparacao_label = "mesmo período ano anterior"
    else:
        inicio_comparacao = None
        fim_comparacao = None
        comparacao_label = None
    
    # Cálculos financeiros do período atual
    receitas_periodo = Projeto.objects.filter(
        data_inicio__gte=inicio_periodo,
        data_inicio__lte=fim_periodo
    )
    receita_total = receitas_periodo.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    # Gastos fixos (sempre mensais, calcular proporcionalmente)
    gastos_fixos = GastoFixo.objects.filter(ativo=True)
    gastos_fixos_total = gastos_fixos.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Calcular proporção de gastos fixos baseado no período
    dias_periodo = (fim_periodo - inicio_periodo).days + 1
    dias_mes = 30  # Média
    proporcao_gastos_fixos = min(dias_periodo / dias_mes, 1.0)
    gastos_fixos_periodo = gastos_fixos_total * Decimal(str(proporcao_gastos_fixos))
    
    # Compras do período
    compras_periodo = CompraEmpresa.objects.filter(
        data_compra__gte=inicio_periodo,
        data_compra__lte=fim_periodo
    )
    compras_total = compras_periodo.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Serviços de hospedagem (proporcionalmente)
    servicos = ServicoHospedagem.objects.filter(status='ativo')
    servicos_total = servicos.aggregate(total=Sum('valor_mensal'))['total'] or Decimal('0.00')
    servicos_periodo = servicos_total * Decimal(str(proporcao_gastos_fixos))
    
    # Total de despesas
    despesas_total = gastos_fixos_periodo + compras_total + servicos_periodo
    
    # Cálculos do período de comparação (se houver)
    receita_comparacao = Decimal('0.00')
    despesas_comparacao = Decimal('0.00')
    lucro_comparacao = Decimal('0.00')
    
    if inicio_comparacao and fim_comparacao:
        receitas_comparacao = Projeto.objects.filter(
            data_inicio__gte=inicio_comparacao,
            data_inicio__lte=fim_comparacao
        )
        receita_comparacao = receitas_comparacao.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        
        compras_comparacao = CompraEmpresa.objects.filter(
            data_compra__gte=inicio_comparacao,
            data_compra__lte=fim_comparacao
        )
        compras_comparacao_total = compras_comparacao.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        # Gastos fixos e serviços proporcionais para o período de comparação
        dias_comparacao = (fim_comparacao - inicio_comparacao).days + 1
        proporcao_comparacao = min(dias_comparacao / dias_mes, 1.0)
        gastos_fixos_comparacao = gastos_fixos_total * Decimal(str(proporcao_comparacao))
        servicos_comparacao = servicos_total * Decimal(str(proporcao_comparacao))
        
        despesas_comparacao = gastos_fixos_comparacao + compras_comparacao_total + servicos_comparacao
        lucro_comparacao = receita_comparacao - despesas_comparacao
    
    # Cálculos de percentuais
    receita_percentual = 0
    despesas_percentual = 0
    
    if receita_comparacao > 0:
        receita_percentual = float(((receita_total - receita_comparacao) / receita_comparacao) * 100)
    
    if despesas_comparacao > 0:
        despesas_percentual = float(((despesas_total - despesas_comparacao) / despesas_comparacao) * 100)
    
    # Lucro líquido e margem
    lucro_liquido = receita_total - despesas_total
    margem_lucro = float((lucro_liquido / receita_total * 100)) if receita_total > 0 else 0
    
    # Fluxo de caixa (próximos 30 dias)
    data_limite = hoje + timedelta(days=30)
    
    # Entradas previstas (parcelas a receber)
    try:
        entradas_previstas = ParcelaProjeto.objects.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=data_limite,
            status='pendente'
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    except:
        entradas_previstas = Decimal('0.00')
    
    # Saídas previstas (gastos fixos mensais)
    saidas_previstas = gastos_fixos_total
    
    # Fluxo de caixa projetado
    fluxo_caixa = entradas_previstas - saidas_previstas
    
    # KPIs
    projetos_ativos = Projeto.objects.filter(status__in=['desenvolvimento', 'aprovado']).count()
    
    try:
        clientes_ativos = Cliente.objects.count()
    except:
        clientes_ativos = User.objects.filter(is_staff=False, is_superuser=False).count()
    
    ticket_medio = receita_total / projetos_ativos if projetos_ativos > 0 else Decimal('0.00')
    
    # Taxa de inadimplência
    try:
        parcelas_vencidas = ParcelaProjeto.objects.filter(
            data_vencimento__lt=hoje,
            status='pendente'
        ).count()
        total_parcelas = ParcelaProjeto.objects.count()
        taxa_inadimplencia = (parcelas_vencidas / total_parcelas * 100) if total_parcelas > 0 else 0
    except:
        taxa_inadimplencia = 0
    
    servicos_ativos = ServicoHospedagem.objects.filter(status='ativo').count()
    
    # ROI médio
    roi_medio = float((lucro_liquido / despesas_total * 100)) if despesas_total > 0 else 0
    
    # Dados para gráficos - Evolução financeira (últimos 6 meses)
    meses_labels = []
    receitas_mensais = []
    despesas_mensais = []
    lucros_mensais = []
    
    for i in range(5, -1, -1):
        mes = hoje - relativedelta(months=i)
        primeiro_dia = mes.replace(day=1)
        ultimo_dia = (primeiro_dia + relativedelta(months=1) - timedelta(days=1))
        
        meses_labels.append(mes.strftime('%b/%Y'))
        
        # Receitas do mês
        receita_mes = Projeto.objects.filter(
            data_inicio__gte=primeiro_dia,
            data_inicio__lte=ultimo_dia
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
        
        # Despesas do mês
        compras_mes = CompraEmpresa.objects.filter(
            data_compra__gte=primeiro_dia,
            data_compra__lte=ultimo_dia
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        despesa_mes = compras_mes + gastos_fixos_total + servicos_total
        lucro_mes = receita_mes - despesa_mes
        
        receitas_mensais.append(float(receita_mes))
        despesas_mensais.append(float(despesa_mes))
        lucros_mensais.append(float(lucro_mes))

    # Dados trimestrais e anuais para comparativos mais amplos
    trimestres_labels = []
    receitas_trimestrais = []
    despesas_trimestrais = []
    lucros_trimestrais = []

    for i in range(3, -1, -1):
        tri_inicio = hoje - relativedelta(months=i*3)
        tri_inicio = tri_inicio.replace(month=((tri_inicio.month - 1)//3)*3 + 1, day=1)
        tri_fim = (tri_inicio + relativedelta(months=3)) - timedelta(days=1)
        trimestres_labels.append(f"T{((tri_inicio.month-1)//3)+1}/{tri_inicio.year}")

        receita_tri = Projeto.objects.filter(
            data_inicio__gte=tri_inicio,
            data_inicio__lte=tri_fim
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')

        compras_tri = CompraEmpresa.objects.filter(
            data_compra__gte=tri_inicio,
            data_compra__lte=tri_fim
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        despesa_tri = compras_tri + (gastos_fixos_total + servicos_total) * Decimal('3')
        lucro_tri = receita_tri - despesa_tri

        receitas_trimestrais.append(float(receita_tri))
        despesas_trimestrais.append(float(despesa_tri))
        lucros_trimestrais.append(float(lucro_tri))

    anos_labels = []
    receitas_anuais = []
    despesas_anuais = []
    lucros_anuais = []

    for i in range(3, -1, -1):
        ano = hoje.year - i
        ano_inicio = date(ano, 1, 1)
        ano_fim = date(ano, 12, 31)
        anos_labels.append(str(ano))

        receita_ano = Projeto.objects.filter(
            data_inicio__gte=ano_inicio,
            data_inicio__lte=ano_fim
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')

        compras_ano = CompraEmpresa.objects.filter(
            data_compra__gte=ano_inicio,
            data_compra__lte=ano_fim
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        despesa_ano = compras_ano + (gastos_fixos_total + servicos_total) * Decimal('12')
        lucro_ano = receita_ano - despesa_ano

        receitas_anuais.append(float(receita_ano))
        despesas_anuais.append(float(despesa_ano))
        lucros_anuais.append(float(lucro_ano))
    
    # Categorias de receita (baseado nos tipos de projeto)
    categorias_receita = []
    categorias_receita_labels = []
    categorias_receita_valores = []
    categorias_receita_cores = []
    
    # Obter categorias reais dos projetos
    tipos_projeto = receitas_periodo.values('tipo').annotate(
        total=Sum('valor_total')
    ).order_by('-total')
    
    # Se não há dados, criar categoria padrão
    if not tipos_projeto:
        tipos_projeto = [{'tipo': 'Sem dados', 'total': Decimal('0.00')}]
    
    # Cores para as categorias
    cores = ['#007bff', '#28a745', '#17a2b8', '#ffc107', '#dc3545', '#6c757d']
    
    # Total para cálculo de percentual
    total_receitas = sum([tp['total'] for tp in tipos_projeto]) or Decimal('1.00')
    
    for i, tipo in enumerate(tipos_projeto):
        cor = cores[i % len(cores)]
        percentual = float((tipo['total'] / total_receitas) * 100) if total_receitas > 0 else 0
        
        categorias_receita.append({
            'nome': tipo['tipo'] or 'Sem categoria',
            'valor': float(tipo['total']),
            'percentual': percentual,
            'cor': cor
        })

        categorias_receita_labels.append(tipo['tipo'] or 'Sem categoria')
        categorias_receita_valores.append(float(tipo['total']))
        categorias_receita_cores.append(cor)
    
    # Categorias de despesa
    categorias_despesa = []
    categorias_despesa_labels = []
    categorias_despesa_valores = []
    categorias_despesa_cores = []
    
    # Gastos fixos por categoria
    gastos_por_categoria = gastos_fixos.values('categoria').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    # Compras por categoria
    compras_por_categoria = compras_periodo.values('categoria').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    # Combinar categorias de gastos fixos e compras
    todas_categorias = {}
    
    for gasto in gastos_por_categoria:
        categoria = gasto['categoria'] or 'Outros'
        if categoria not in todas_categorias:
            todas_categorias[categoria] = Decimal('0.00')
        todas_categorias[categoria] += gasto['total'] * Decimal(str(proporcao_gastos_fixos))
    
    for compra in compras_por_categoria:
        categoria = compra['categoria'] or 'Outros'
        if categoria not in todas_categorias:
            todas_categorias[categoria] = Decimal('0.00')
        todas_categorias[categoria] += compra['total']
    
    # Se não há dados, criar categoria padrão
    if not todas_categorias:
        todas_categorias = {'Sem dados': Decimal('0.00')}
    
    # Converter para lista ordenada
    categorias_ordenadas = sorted(todas_categorias.items(), key=lambda x: x[1], reverse=True)
    
    # Total para cálculo de percentual
    total_despesas = sum([valor for _, valor in categorias_ordenadas]) or Decimal('1.00')
    
    for i, (categoria, valor) in enumerate(categorias_ordenadas):
        cor = cores[i % len(cores)]
        percentual = float((valor / total_despesas) * 100) if total_despesas > 0 else 0
        
        categorias_despesa.append({
            'nome': categoria,
            'valor': float(valor),
            'percentual': percentual,
            'cor': cor
        })

        categorias_despesa_labels.append(categoria)
        categorias_despesa_valores.append(float(valor))
        categorias_despesa_cores.append(cor)
    
    # Top clientes
    top_clientes = []
    try:
        clientes = Cliente.objects.all()[:10]
        for cliente in clientes:
            projetos_cliente = Projeto.objects.filter(cliente=cliente)
            receita_cliente = projetos_cliente.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            total_projetos = projetos_cliente.count()
            ultima_atividade = projetos_cliente.order_by('-data_criacao').first()
            
            top_clientes.append({
                'nome': f"{cliente.usuario.first_name} {cliente.usuario.last_name}".strip() or cliente.usuario.username,
                'empresa': cliente.nome_empresa,
                'receita_total': receita_cliente,
                'total_projetos': total_projetos,
                'ultima_atividade': ultima_atividade.data_criacao.date() if ultima_atividade else None,
                'status': 'ativo',
                'get_status_display': 'Ativo'
            })
    except:
        # Se não há modelo Cliente, usar dados dos usuários
        usuarios = User.objects.filter(is_staff=False, is_superuser=False)[:10]
        for usuario in usuarios:
            projetos_usuario = Projeto.objects.filter(cliente__usuario=usuario) if hasattr(Projeto, 'cliente') else []
            receita_usuario = sum([p.valor_total for p in projetos_usuario]) if projetos_usuario else 0
            
            top_clientes.append({
                'nome': f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username,
                'empresa': '',
                'receita_total': receita_usuario,
                'total_projetos': len(projetos_usuario),
                'ultima_atividade': usuario.date_joined.date(),
                'status': 'ativo',
                'get_status_display': 'Ativo'
            })

    top_clientes_labels = [c['nome'] for c in top_clientes[:5]]
    top_clientes_valores = [float(c['receita_total']) for c in top_clientes[:5]]
    
    # Alertas financeiros
    alertas = []
    
    if taxa_inadimplencia > 10:
        alertas.append({
            'tipo': 'warning',
            'icone': 'exclamation-triangle',
            'titulo': 'Alta Inadimplência',
            'mensagem': f'Taxa de inadimplência em {taxa_inadimplencia:.1f}%'
        })
    
    if margem_lucro < 10:
        alertas.append({
            'tipo': 'danger',
            'icone': 'chart-line-down',
            'titulo': 'Margem Baixa',
            'mensagem': f'Margem de lucro em {margem_lucro:.1f}%'
        })
    
    if fluxo_caixa < 0:
        alertas.append({
            'tipo': 'danger',
            'icone': 'money-bill-wave',
            'titulo': 'Fluxo Negativo',
            'mensagem': 'Fluxo de caixa projetado negativo'
        })
    
    # Dados para fluxo de caixa (próximos 3 meses)
    fluxo_caixa_labels = []
    fluxo_caixa_entradas = []
    fluxo_caixa_saidas = []
    
    for i in range(3):
        mes_futuro = hoje + relativedelta(months=i)
        fluxo_caixa_labels.append(mes_futuro.strftime('%b/%Y'))
        
        # Entradas projetadas (baseado na média mensal)
        entrada_projetada = float(receita_total) if receita_total > 0 else 0
        fluxo_caixa_entradas.append(entrada_projetada)
        
        # Saídas projetadas
        saida_projetada = float(gastos_fixos_total + servicos_total)
        fluxo_caixa_saidas.append(saida_projetada)

    # Distribuição de status para relatórios detalhados
    status_colors = {
        'pendente': '#FBBF24',
        'paga': '#10B981',
        'vencida': '#EF4444',
        'cancelada': '#6B7280',
        'planejada': '#3B82F6',
        'aprovada': '#10B981',
        'comprada': '#F59E0B',
        'entregue': '#8B5CF6',
        'orcamento': '#6B7280',
        'desenvolvimento': '#3B82F6',
        'concluido': '#10B981',
        'ativo': '#10B981',
        'suspenso': '#FBBF24',
        'expirado': '#EF4444'
    }

    def get_status_data(queryset, status_choices):
        result = queryset.values('status').annotate(total=Count('id'))
        labels = []
        valores = []
        cores = []
        for item in result:
            key = item['status']
            labels.append(dict(status_choices).get(key, key))
            valores.append(item['total'])
            cores.append(status_colors.get(key, '#3B82F6'))
        return labels, valores, cores

    parcelas_status_labels, parcelas_status_valores, parcelas_status_cores = get_status_data(ParcelaProjeto.objects.all(), ParcelaProjeto.STATUS_CHOICES)
    compras_status_labels, compras_status_valores, compras_status_cores = get_status_data(CompraEmpresa.objects.all(), CompraEmpresa.STATUS_CHOICES)
    projetos_status_labels, projetos_status_valores, projetos_status_cores = get_status_data(Projeto.objects.all(), Projeto.STATUS_CHOICES)
    servicos_status_labels, servicos_status_valores, servicos_status_cores = get_status_data(ServicoHospedagem.objects.all(), ServicoHospedagem.STATUS_CHOICES)
    
    # Dados padrão para datas
    data_inicio_default = inicio_periodo.strftime('%Y-%m-%d')
    data_fim_default = fim_periodo.strftime('%Y-%m-%d')
    
    context = {
        # Período e comparação
        'periodo_atual_label': periodo_label,
        'periodo_comparacao_label': comparacao_label,
        'comparacao_label': comparacao_label,
        'data_inicio_default': data_inicio_default,
        'data_fim_default': data_fim_default,
        
        # Resumo financeiro
        'receita_total': receita_total,
        'despesas_total': despesas_total,
        'lucro_liquido': lucro_liquido,
        'margem_lucro': margem_lucro,
        'fluxo_caixa': fluxo_caixa,
        'gastos_fixos_total': gastos_fixos_total,
        'compras_total': compras_total,
        'servicos_total': servicos_total,
        
        # Comparações
        'receita_comparacao': receita_comparacao,
        'despesas_comparacao': despesas_comparacao,
        'lucro_comparacao': lucro_comparacao,
        'receita_percentual': receita_percentual,
        'despesas_percentual': despesas_percentual,
        
        # KPIs
        'projetos_ativos': projetos_ativos,
        'clientes_ativos': clientes_ativos,
        'ticket_medio': ticket_medio,
        'taxa_inadimplencia': taxa_inadimplencia,
        'servicos_ativos': servicos_ativos,
        'roi_medio': roi_medio,
        
        # Dados para gráficos
        'meses_labels': json.dumps(meses_labels),
        'receitas_mensais': json.dumps(receitas_mensais),
        'despesas_mensais': json.dumps(despesas_mensais),
        'lucros_mensais': json.dumps(lucros_mensais),
        'trimestres_labels': json.dumps(trimestres_labels),
        'receitas_trimestrais': json.dumps(receitas_trimestrais),
        'despesas_trimestrais': json.dumps(despesas_trimestrais),
        'lucros_trimestrais': json.dumps(lucros_trimestrais),
        'anos_labels': json.dumps(anos_labels),
        'receitas_anuais': json.dumps(receitas_anuais),
        'despesas_anuais': json.dumps(despesas_anuais),
        'lucros_anuais': json.dumps(lucros_anuais),
        
        # Categorias
        'categorias_receita': categorias_receita,
        'categorias_receita_labels': json.dumps(categorias_receita_labels),
        'categorias_receita_valores': json.dumps(categorias_receita_valores),
        'categorias_receita_cores': json.dumps(categorias_receita_cores),
        'categorias_despesa': categorias_despesa,
        'categorias_despesa_labels': json.dumps(categorias_despesa_labels),
        'categorias_despesa_valores': json.dumps(categorias_despesa_valores),
        'categorias_despesa_cores': json.dumps(categorias_despesa_cores),
        
        # Clientes e alertas
        'top_clientes': top_clientes,
        'top_clientes_labels': json.dumps(top_clientes_labels),
        'top_clientes_valores': json.dumps(top_clientes_valores),
        'alertas': alertas,
        
        # Fluxo de caixa
        'fluxo_caixa_labels': json.dumps(fluxo_caixa_labels),
        'fluxo_caixa_entradas': json.dumps(fluxo_caixa_entradas),
        'fluxo_caixa_saidas': json.dumps(fluxo_caixa_saidas),

        # Status charts
        'parcelas_status_labels': json.dumps(parcelas_status_labels),
        'parcelas_status_valores': json.dumps(parcelas_status_valores),
        'parcelas_status_cores': json.dumps(parcelas_status_cores),
        'compras_status_labels': json.dumps(compras_status_labels),
        'compras_status_valores': json.dumps(compras_status_valores),
        'compras_status_cores': json.dumps(compras_status_cores),
        'projetos_status_labels': json.dumps(projetos_status_labels),
        'projetos_status_valores': json.dumps(projetos_status_valores),
        'projetos_status_cores': json.dumps(projetos_status_cores),
        'servicos_status_labels': json.dumps(servicos_status_labels),
        'servicos_status_valores': json.dumps(servicos_status_valores),
        'servicos_status_cores': json.dumps(servicos_status_cores),
    }
    
    return render(request, 'core/superadmin/dashboard_financeiro.html', context)

# Views de Gastos Fixos
@user_passes_test(is_superuser)
def gastos_fixos_view(request):
    from .models import GastoFixo
    
    gastos_list = GastoFixo.objects.all().order_by('-data_criacao')
    
    # Filtros
    categoria = request.GET.get('categoria')
    status = request.GET.get('status')
    
    if categoria:
        gastos_list = gastos_list.filter(categoria=categoria)
    
    if status == 'ativo':
        gastos_list = gastos_list.filter(ativo=True)
    elif status == 'inativo':
        gastos_list = gastos_list.filter(ativo=False)
    
    # Paginação
    paginator = Paginator(gastos_list, 20)
    page_number = request.GET.get('page')
    gastos = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/gastos_fixos.html', {
        'gastos': gastos,
        'categoria': categoria,
        'status': status,
    })

@user_passes_test(is_superuser)
def criar_gasto_fixo_view(request):
    from .forms import GastoFixoForm
    
    if request.method == 'POST':
        form = GastoFixoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto fixo criado com sucesso!')
            return redirect('gastos_fixos')
    else:
        form = GastoFixoForm()
    
    return render(request, 'core/superadmin/criar_gasto_fixo.html', {'form': form})

@user_passes_test(is_superuser)
def editar_gasto_fixo_view(request, pk):
    from .models import GastoFixo
    from .forms import GastoFixoForm
    
    gasto = get_object_or_404(GastoFixo, pk=pk)
    
    if request.method == 'POST':
        form = GastoFixoForm(request.POST, instance=gasto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto fixo atualizado com sucesso!')
            return redirect('gastos_fixos')
    else:
        form = GastoFixoForm(instance=gasto)
    
    return render(request, 'core/superadmin/editar_gasto_fixo.html', {'form': form, 'gasto': gasto})

@user_passes_test(is_superuser)
def deletar_gasto_fixo_view(request, pk):
    from .models import GastoFixo
    
    gasto = get_object_or_404(GastoFixo, pk=pk)
    
    if request.method == 'POST':
        gasto.delete()
        messages.success(request, 'Gasto fixo deletado com sucesso!')
        return redirect('gastos_fixos')
    
    return render(request, 'core/superadmin/confirmar_deletar_gasto.html', {'gasto': gasto})

# Views de Compras da Empresa
@user_passes_test(is_superuser)
def compras_empresa_view(request):
    from .models import CompraEmpresa
    
    compras_list = CompraEmpresa.objects.all().order_by('-data_compra')
    
    # Filtros
    categoria = request.GET.get('categoria')
    status = request.GET.get('status')
    
    if categoria:
        compras_list = compras_list.filter(categoria=categoria)
    
    if status:
        compras_list = compras_list.filter(status=status)
    
    # Paginação
    paginator = Paginator(compras_list, 20)
    page_number = request.GET.get('page')
    compras = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/compras_empresa.html', {
        'compras': compras,
        'categoria': categoria,
        'status': status,
    })

@user_passes_test(is_superuser)
def criar_compra_empresa_view(request):
    from .forms import CompraEmpresaForm
    
    if request.method == 'POST':
        form = CompraEmpresaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compra registrada com sucesso!')
            return redirect('compras_empresa')
    else:
        form = CompraEmpresaForm()
    
    return render(request, 'core/superadmin/criar_compra_empresa.html', {'form': form})

@user_passes_test(is_superuser)
def editar_compra_empresa_view(request, pk):
    from .models import CompraEmpresa
    from .forms import CompraEmpresaForm
    
    compra = get_object_or_404(CompraEmpresa, pk=pk)
    
    if request.method == 'POST':
        form = CompraEmpresaForm(request.POST, instance=compra)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compra atualizada com sucesso!')
            return redirect('compras_empresa')
    else:
        form = CompraEmpresaForm(instance=compra)
    
    return render(request, 'core/superadmin/editar_compra_empresa.html', {'form': form, 'compra': compra})

@user_passes_test(is_superuser)
def deletar_compra_empresa_view(request, pk):
    from .models import CompraEmpresa
    
    compra = get_object_or_404(CompraEmpresa, pk=pk)
    
    if request.method == 'POST':
        compra.delete()
        messages.success(request, 'Compra deletada com sucesso!')
        return redirect('compras_empresa')
    
    return render(request, 'core/superadmin/confirmar_deletar_compra.html', {'compra': compra})

# Views de Clientes
@user_passes_test(is_superuser)
def clientes_view(request):
    from .models import Cliente
    
    clientes_list = Cliente.objects.all().order_by('-data_criacao')
    
    # Busca
    busca = request.GET.get('busca')
    if busca:
        clientes_list = clientes_list.filter(
            Q(nome_empresa__icontains=busca) | 
            Q(contato_principal__icontains=busca) |
            Q(email_contato__icontains=busca)
        )
    
    # Paginação
    paginator = Paginator(clientes_list, 20)
    page_number = request.GET.get('page')
    clientes = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/clientes.html', {
        'clientes': clientes,
        'busca': busca,
    })

@user_passes_test(is_superuser)
def criar_cliente_view(request):
    from .forms import ClienteForm
    
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente criado com sucesso!')
            return redirect('clientes')
    else:
        form = ClienteForm()
    
    return render(request, 'core/superadmin/criar_cliente.html', {'form': form})

@user_passes_test(is_superuser)
def editar_cliente_view(request, pk):
    from .models import Cliente
    from .forms import ClienteForm
    
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('clientes')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'core/superadmin/editar_cliente.html', {'form': form, 'cliente': cliente})

@user_passes_test(is_superuser)
def deletar_cliente_view(request, pk):
    from .models import Cliente
    
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente deletado com sucesso!')
        return redirect('clientes')
    
    return render(request, 'core/superadmin/confirmar_deletar_cliente.html', {'cliente': cliente})

# Views de Projetos
@user_passes_test(is_superuser)
def projetos_view(request):
    from .models import Projeto
    
    projetos_list = Projeto.objects.all().order_by('-data_criacao')
    
    # Filtros
    status = request.GET.get('status')
    cliente_id = request.GET.get('cliente')
    
    if status:
        projetos_list = projetos_list.filter(status=status)
    
    if cliente_id:
        projetos_list = projetos_list.filter(cliente_id=cliente_id)
    
    # Paginação
    paginator = Paginator(projetos_list, 20)
    page_number = request.GET.get('page')
    projetos = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/projetos.html', {
        'projetos': projetos,
        'status': status,
        'cliente_id': cliente_id,
    })

@user_passes_test(is_superuser)
def criar_projeto_view(request):
    from .forms import ProjetoForm
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Projeto criado com sucesso!')
            return redirect('projetos')
    else:
        form = ProjetoForm()
    
    return render(request, 'core/superadmin/criar_projeto.html', {'form': form})

@user_passes_test(is_superuser)
def editar_projeto_view(request, pk):
    from .models import Projeto
    from .forms import ProjetoForm
    
    projeto = get_object_or_404(Projeto, pk=pk)
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST, instance=projeto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Projeto atualizado com sucesso!')
            return redirect('projetos')
    else:
        form = ProjetoForm(instance=projeto)
    
    return render(request, 'core/superadmin/editar_projeto.html', {'form': form, 'projeto': projeto})

@user_passes_test(is_superuser)
def deletar_projeto_view(request, pk):
    from .models import Projeto
    
    projeto = get_object_or_404(Projeto, pk=pk)
    
    if request.method == 'POST':
        projeto.delete()
        messages.success(request, 'Projeto deletado com sucesso!')
        return redirect('projetos')
    
    return render(request, 'core/superadmin/confirmar_deletar_projeto.html', {'projeto': projeto})

# Views de Serviços de Hospedagem
@user_passes_test(is_superuser)
def servicos_hospedagem_view(request):
    from .models import ServicoHospedagem
    
    servicos_list = ServicoHospedagem.objects.all().order_by('-data_criacao')
    
    # Filtros
    status = request.GET.get('status')
    tipo = request.GET.get('tipo')
    
    if status:
        servicos_list = servicos_list.filter(status=status)
    
    if tipo:
        servicos_list = servicos_list.filter(tipo=tipo)
    
    # Paginação
    paginator = Paginator(servicos_list, 20)
    page_number = request.GET.get('page')
    servicos = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/servicos_hospedagem.html', {
        'servicos': servicos,
        'status': status,
        'tipo': tipo,
    })

@user_passes_test(is_superuser)
def criar_servico_hospedagem_view(request):
    from .forms import ServicoHospedagemForm
    
    if request.method == 'POST':
        form = ServicoHospedagemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Serviço de hospedagem criado com sucesso!')
            return redirect('servicos_hospedagem')
    else:
        form = ServicoHospedagemForm()
    
    return render(request, 'core/superadmin/criar_servico_hospedagem.html', {'form': form})

@user_passes_test(is_superuser)
def editar_servico_hospedagem_view(request, pk):
    from .models import ServicoHospedagem
    from .forms import ServicoHospedagemForm
    
    servico = get_object_or_404(ServicoHospedagem, pk=pk)
    
    if request.method == 'POST':
        form = ServicoHospedagemForm(request.POST, instance=servico)
        if form.is_valid():
            form.save()
            messages.success(request, 'Serviço de hospedagem atualizado com sucesso!')
            return redirect('servicos_hospedagem')
    else:
        form = ServicoHospedagemForm(instance=servico)
    
    return render(request, 'core/superadmin/editar_servico_hospedagem.html', {'form': form, 'servico': servico})

@user_passes_test(is_superuser)
def deletar_servico_hospedagem_view(request, pk):
    from .models import ServicoHospedagem
    
    servico = get_object_or_404(ServicoHospedagem, pk=pk)
    
    if request.method == 'POST':
        servico.delete()
        messages.success(request, 'Serviço de hospedagem deletado com sucesso!')
        return redirect('servicos_hospedagem')
    
    return render(request, 'core/superadmin/confirmar_deletar_servico.html', {'servico': servico})

# Views de Notificações
@user_passes_test(is_superuser)
def notificacoes_view(request):
    from .models import Notificacao
    
    notificacoes_list = Notificacao.objects.all().order_by('-data_criacao')
    
    # Filtros
    lida = request.GET.get('lida')
    tipo = request.GET.get('tipo')
    
    if lida == 'true':
        notificacoes_list = notificacoes_list.filter(lida=True)
    elif lida == 'false':
        notificacoes_list = notificacoes_list.filter(lida=False)
    
    if tipo:
        notificacoes_list = notificacoes_list.filter(tipo=tipo)
    
    # Paginação
    paginator = Paginator(notificacoes_list, 20)
    page_number = request.GET.get('page')
    notificacoes = paginator.get_page(page_number)
    
    return render(request, 'core/superadmin/notificacoes.html', {
        'notificacoes': notificacoes,
        'lida': lida,
        'tipo': tipo,
    })

@user_passes_test(is_superuser)
def marcar_notificacao_lida_view(request, pk):
    from .models import Notificacao
    
    notificacao = get_object_or_404(Notificacao, pk=pk)
    notificacao.lida = True
    notificacao.save()
    
    messages.success(request, 'Notificação marcada como lida!')
    return redirect('notificacoes')

# Views de Edição de Usuários
@user_passes_test(is_superuser)
def criar_usuario_view(request):
    from .forms import CriarUsuarioForm
    
    if request.method == 'POST':
        form = CriarUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Cria configuração padrão para o usuário
            configuracao = ConfiguracaoUsuario.objects.create(
                usuario=user,
                nome_tabela_sheets="",
                nome_pagina_contatos="contatos",
                nome_pagina_mensagens="mensagem",
                coluna_nome="nome",
                coluna_numero="numero",
                coluna_enviado="enviado",
                coluna_mensagem="mensagem",
                coluna_quantidade="quantidade"
            )
            
            messages.success(request, f'Usuário {user.username} criado com sucesso!')
            return redirect('superadmin_usuarios')
    else:
        form = CriarUsuarioForm()
    
    return render(request, 'core/superadmin/criar_usuario.html', {'form': form})

@user_passes_test(is_superuser)
def editar_usuario_view(request, user_id):
    from .forms import EditarUsuarioForm, EvolutionConfigForm
    
    usuario = get_object_or_404(User, pk=user_id)
    
    # Obtém ou cria configuração
    configuracao, created = ConfiguracaoUsuario.objects.get_or_create(usuario=usuario)
    
    if request.method == 'POST':
        # Verifica se é configuração Evolution
        if 'evolution_config' in request.POST:
            evolution_form = EvolutionConfigForm(request.POST, instance=configuracao)
            if evolution_form.is_valid():
                evolution_form.save()
                messages.success(request, 'Configurações Evolution salvas com sucesso!')
                return redirect('superadmin_usuario_detalhes', user_id=usuario.pk)
        else:
            # Formulário de edição do usuário
            form = EditarUsuarioForm(request.POST, instance=usuario)
            if form.is_valid():
                form.save()
                messages.success(request, f'Usuário {usuario.username} atualizado com sucesso!')
                return redirect('superadmin_usuario_detalhes', user_id=usuario.pk)
    else:
        form = EditarUsuarioForm(instance=usuario)
        evolution_form = EvolutionConfigForm(instance=configuracao)
    
    context = {
        'form': form,
        'evolution_form': evolution_form,
        'usuario': usuario,
        'configuracao': configuracao,
    }
    return render(request, 'core/superadmin/editar_usuario.html', context)
