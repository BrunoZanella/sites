from django.db import models
from django.contrib.auth.models import User
import json
import os
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class ConfiguracaoUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Usuário")
    nome_tabela_sheets = models.CharField(max_length=200, verbose_name="Nome da Tabela Google Sheets", blank=True)
    url_planilha = models.URLField(max_length=500, verbose_name="URL da Planilha", blank=True)
    nome_pagina_contatos = models.CharField(max_length=100, default="contatos", verbose_name="Nome da Página de Contatos")
    nome_pagina_mensagens = models.CharField(max_length=100, default="mensagem", verbose_name="Nome da Página de Mensagens")

    url_evolution = models.URLField(max_length=500, default="https://evolution.apex.dev.br", verbose_name="URL da API Evolution")
    instancia_evolution = models.CharField(max_length=500, default="", verbose_name="Instância de Evolution")
    api_evolution = models.CharField(max_length=500, default="", verbose_name="API da Evolution")
    
    # Nomes das colunas
    coluna_nome = models.CharField(max_length=50, default="nome", verbose_name="Nome da Coluna Nome")
    coluna_numero = models.CharField(max_length=50, default="numero", verbose_name="Nome da Coluna Número")
    coluna_enviado = models.CharField(max_length=50, default="enviado", verbose_name="Nome da Coluna Enviado")
    coluna_mensagem = models.CharField(max_length=50, default="mensagem", verbose_name="Nome da Coluna Mensagem")
    coluna_quantidade = models.CharField(max_length=50, default="quantidade", verbose_name="Nome da Coluna Quantidade")
    
    # Status da planilha
    planilha_criada = models.BooleanField(default=False, verbose_name="Planilha Criada")
    automacao_ativa = models.BooleanField(default=True, verbose_name="Automação Ativa")
    
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Configuração do Usuário"
        verbose_name_plural = "Configurações dos Usuários"
    
    def __str__(self):
        return f"Configuração de {self.usuario.username}"
    
    def criar_planilha_automatica(self):
        """Cria automaticamente uma planilha no Google Sheets para o usuário"""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            # Caminho das credenciais (você pode colocar no settings.py)
            credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")
            
            if not os.path.exists(credentials_path):
                return False, "Arquivo de credenciais não encontrado no servidor"
            
            # Escopos necessários
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Autenticação
            credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
            gc = gspread.authorize(credentials)
            
            # Nome da planilha baseado no usuário
            nome_planilha = f"WhatsApp - {self.usuario.first_name} {self.usuario.last_name} ({self.usuario.username})"
            
            # Cria a planilha
            spreadsheet = gc.create(nome_planilha)
            
            # Compartilha com o e-mail do usuário (se existir)
            if self.usuario.email:
                try:
                    spreadsheet.share(self.usuario.email, perm_type="user", role="writer")
                except Exception as e:
                    # Log ou ignorar erro silenciosamente
                    pass

            # Compartilha com o e-mail institucional (obrigatório)
            spreadsheet.share("automacoes.apex@gmail.com", perm_type="user", role="writer")
            
            # Configura a primeira aba (contatos)
            sheet1 = spreadsheet.sheet1
            sheet1.update_title(self.nome_pagina_contatos)
            sheet1.update("A1", [[self.coluna_nome, self.coluna_numero, self.coluna_enviado]])
            
            # Cria a segunda aba (mensagens)
            sheet2 = spreadsheet.add_worksheet(title=self.nome_pagina_mensagens, rows="100", cols="5")
            sheet2.update("A1", [[self.coluna_mensagem, self.coluna_quantidade]])
            
            # Formata os cabeçalhos
            # Primeira aba
            sheet1.format("A1:C1", {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                "textFormat": {"bold": True}
            })
            
            # Segunda aba
            sheet2.format("A1:B1", {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                "textFormat": {"bold": True}
            })
            
            # Salva as informações no modelo
            self.nome_tabela_sheets = nome_planilha
            self.url_planilha = spreadsheet.url
            self.planilha_criada = True
            self.save()
            
            return True, f"Planilha criada com sucesso: {nome_planilha}"
            
        except Exception as e:
            return False, f"Erro ao criar planilha: {str(e)}"
    
    def sincronizar_contatos(self):
        """Sincroniza contatos bidirecionalmente entre o sistema e a planilha"""
        if not self.planilha_criada or not self.url_planilha:
            return False, "Planilha não foi criada ainda"
        
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            # Caminho das credenciais
            credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")
            
            if not os.path.exists(credentials_path):
                return False, "Arquivo de credenciais não encontrado no servidor"
            
            # Escopos necessários
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Autenticação
            credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
            gc = gspread.authorize(credentials)
            
            # Abre a planilha
            spreadsheet = gc.open(self.nome_tabela_sheets)
            sheet_contatos = spreadsheet.worksheet(self.nome_pagina_contatos)
            
            # Lê todos os dados da planilha (incluindo cabeçalhos)
            dados_planilha = sheet_contatos.get_all_values()
            
            if len(dados_planilha) < 2:  # Só tem cabeçalho ou está vazia
                # Se a planilha está vazia, popula com dados do banco
                return self._popular_planilha_vazia(sheet_contatos)
            
            # Identifica as colunas
            cabecalhos = dados_planilha[0]
            try:
                idx_nome = cabecalhos.index(self.coluna_nome)
                idx_numero = cabecalhos.index(self.coluna_numero)
                idx_enviado = cabecalhos.index(self.coluna_enviado)
            except ValueError as e:
                return False, f"Coluna não encontrada na planilha: {str(e)}"
            
            # Busca todos os contatos do usuário
            from .models import Contato, LogEnvio, Mensagem
            contatos_banco = {c.numero: c for c in Contato.objects.filter(usuario=self.usuario)}
            
            contatos_atualizados = 0
            logs_criados = 0
            contatos_adicionados_planilha = 0
            
            # Processa cada linha da planilha (pula o cabeçalho)
            for i, linha in enumerate(dados_planilha[1:], start=2):
                if len(linha) <= max(idx_nome, idx_numero, idx_enviado):
                    continue  # Linha incompleta
                
                nome_planilha = linha[idx_nome].strip()
                numero_planilha = linha[idx_numero].strip()
                enviado_planilha = linha[idx_enviado].strip()
                
                if not nome_planilha or not numero_planilha:
                    continue  # Linha vazia
                
                # Normaliza o número
                numero_limpo = ''.join(filter(str.isdigit, numero_planilha))
                
                # Verifica se o contato existe no banco
                contato_banco = contatos_banco.get(numero_limpo)
                
                if contato_banco:
                    # Contato existe no banco, verifica se precisa atualizar
                    enviado_planilha_bool = enviado_planilha.lower() in ['1', 'true', 'sim', 'yes', 'y', 's', 't']
                    
                    if enviado_planilha_bool and not contato_banco.enviado:
                        # Planilha diz que foi enviado, mas banco diz que não
                        # Atualiza o banco e cria log
                        contato_banco.enviado = True
                        contato_banco.data_envio = timezone.now()
                        contato_banco.save()
                        
                        # Cria log de envio
                        # Busca uma mensagem ativa do usuário para o log
                        mensagem_ativa = Mensagem.objects.filter(
                            usuario=self.usuario, 
                            ativa=True
                        ).first()
                        
                        if mensagem_ativa:
                            LogEnvio.objects.create(
                                usuario=self.usuario,
                                contato=contato_banco,
                                mensagem=mensagem_ativa,
                                status='sucesso',
                                data_tentativa=timezone.now()
                            )
                            logs_criados += 1
                        
                        contatos_atualizados += 1
                        print(f"Contato atualizado do Sheets: {nome_planilha} - {numero_limpo} - Enviado: True")
                    
                    elif not enviado_planilha_bool and contato_banco.enviado:
                        # Banco diz que foi enviado, mas planilha diz que não
                        # Atualiza a planilha com o valor do banco
                        sheet_contatos.update_cell(i, idx_enviado + 1, "1")
                        print(f"Planilha atualizada do banco: {nome_planilha} - {numero_limpo} - Enviado: 1")
                
                else:
                    # Contato não existe no banco, mas está na planilha
                    # Cria o contato no banco
                    enviado_planilha_bool = enviado_planilha.lower() in ['1', 'true', 'sim', 'yes', 'y', 's', 't']
                    
                    novo_contato = Contato.objects.create(
                        usuario=self.usuario,
                        nome=nome_planilha,
                        numero=numero_limpo,
                        enviado=enviado_planilha_bool,
                        data_envio=timezone.now() if enviado_planilha_bool else None
                    )
                    
                    # Se foi marcado como enviado, cria o log
                    if enviado_planilha_bool:
                        mensagem_ativa = Mensagem.objects.filter(
                            usuario=self.usuario, 
                            ativa=True
                        ).first()
                        
                        if mensagem_ativa:
                            LogEnvio.objects.create(
                                usuario=self.usuario,
                                contato=novo_contato,
                                mensagem=mensagem_ativa,
                                status='sucesso',
                                data_tentativa=timezone.now()
                            )
                            logs_criados += 1
                    
                    contatos_atualizados += 1
                    print(f"Contato criado da planilha: {nome_planilha} - {numero_limpo} - Enviado: {enviado_planilha_bool}")
            
            # Adiciona contatos do banco que não estão na planilha
            numeros_planilha = set()
            for linha in dados_planilha[1:]:
                if len(linha) > idx_numero:
                    numero = ''.join(filter(str.isdigit, linha[idx_numero]))
                    if numero:
                        numeros_planilha.add(numero)
            
            # Contatos que estão no banco mas não na planilha
            contatos_para_adicionar = []
            for numero, contato in contatos_banco.items():
                if numero not in numeros_planilha:
                    contatos_para_adicionar.append([
                        contato.nome,
                        contato.numero,
                        1 if contato.enviado else 0
                    ])
                    contatos_adicionados_planilha += 1
            
            # Adiciona os novos contatos à planilha
            if contatos_para_adicionar:
                proxima_linha = len(dados_planilha) + 1
                range_update = f"A{proxima_linha}:C{proxima_linha + len(contatos_para_adicionar) - 1}"
                sheet_contatos.update(range_update, contatos_para_adicionar)
            
            mensagem_resultado = f"Sincronização concluída! "
            mensagem_resultado += f"{contatos_atualizados} contatos atualizados no banco, "
            mensagem_resultado += f"{logs_criados} logs criados, "
            mensagem_resultado += f"{contatos_adicionados_planilha} contatos adicionados à planilha"
            
            return True, mensagem_resultado
            
        except Exception as e:
            return False, f"Erro ao sincronizar: {str(e)}"
    
    def _popular_planilha_vazia(self, sheet_contatos):
        """Popula uma planilha vazia com dados do banco"""
        from .models import Contato
        
        contatos = Contato.objects.filter(usuario=self.usuario).order_by('nome')
        
        # Prepara os dados
        dados = []
        for contato in contatos:
            dados.append([
                contato.nome,
                contato.numero,
                1 if contato.enviado else 0
            ])
        
        # Adiciona os dados
        if dados:
            sheet_contatos.update(f"A2:C{len(dados)+1}", dados)
        
        return True, f"Planilha populada com {len(dados)} contatos do banco"

class Contato(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    nome = models.CharField(max_length=200, verbose_name="Nome")
    numero = models.CharField(max_length=20, verbose_name="Número do WhatsApp")
    enviado = models.BooleanField(default=False, verbose_name="Mensagem Enviada")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    data_envio = models.DateTimeField(null=True, blank=True, verbose_name="Data do Envio")
    
    class Meta:
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"
        unique_together = ['usuario', 'numero']
    
    def __str__(self):
        return f"{self.nome} - {self.numero}"
    
    @staticmethod
    def normalizar_numero(numero):
        """Remove formatação do número, mantendo apenas dígitos"""
        return ''.join(filter(str.isdigit, str(numero)))
    
    def save(self, *args, **kwargs):
        # Normaliza o número antes de salvar
        self.numero = self.normalizar_numero(self.numero)
        super().save(*args, **kwargs)

class Mensagem(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    texto_mensagem = models.TextField(verbose_name="Texto da Mensagem")
    quantidade_envios = models.IntegerField(default=0, verbose_name="Quantidade de Envios Realizados")
    quantidade_maxima = models.IntegerField(default=100, verbose_name="Quantidade Máxima de Envios")
    ativa = models.BooleanField(default=True, verbose_name="Mensagem Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
    
    def __str__(self):
        return f"Mensagem de {self.usuario.username} - {self.texto_mensagem[:50]}..."
    
    def pode_enviar(self):
        """Verifica se ainda pode enviar mensagens"""
        return self.ativa and self.quantidade_envios < self.quantidade_maxima

class LogEnvio(models.Model):
    STATUS_CHOICES = [
        ('sucesso', 'Sucesso'),
        ('erro', 'Erro'),
        ('pendente', 'Pendente'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    contato = models.ForeignKey(Contato, on_delete=models.CASCADE, verbose_name="Contato")
    mensagem = models.ForeignKey(Mensagem, on_delete=models.CASCADE, verbose_name="Mensagem")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    erro_detalhes = models.TextField(null=True, blank=True, verbose_name="Detalhes do Erro")
    data_tentativa = models.DateTimeField(auto_now_add=True, verbose_name="Data da Tentativa")
    
    class Meta:
        verbose_name = "Log de Envio"
        verbose_name_plural = "Logs de Envio"
    
    def __str__(self):
        return f"Envio para {self.contato.nome} - {self.status}"

# Modelos para Gestão Empresarial

class GastoFixo(models.Model):
    CATEGORIA_CHOICES = [
        ('energia', 'Energia Elétrica'),
        ('internet', 'Internet'),
        ('telefone', 'Telefone'),
        ('aluguel', 'Aluguel'),
        ('agua', 'Água'),
        ('gas', 'Gás'),
        ('salarios', 'Salários'),
        ('software', 'Software/Licenças'),
        ('servidor', 'Servidor/Hospedagem'),
        ('marketing', 'Marketing'),
        ('contabilidade', 'Contabilidade'),
        ('impostos', 'Impostos'),
        ('outros', 'Outros'),
    ]
    
    nome = models.CharField(max_length=200, verbose_name="Nome do Gasto")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, verbose_name="Categoria")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Mensal")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    dia_vencimento = models.IntegerField(default=10, verbose_name="Dia do Vencimento")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Gasto Fixo"
        verbose_name_plural = "Gastos Fixos"
        ordering = ['categoria', 'nome']
    
    def __str__(self):
        return f"{self.nome} - R$ {self.valor}"
    
    def proximo_vencimento(self):
        """Retorna a próxima data de vencimento"""
        hoje = date.today()
        if hoje.day <= self.dia_vencimento:
            return hoje.replace(day=self.dia_vencimento)
        else:
            proximo_mes = hoje + relativedelta(months=1)
            return proximo_mes.replace(day=self.dia_vencimento)

class CompraEmpresa(models.Model):
    CATEGORIA_CHOICES = [
        ('hardware', 'Hardware'),
        ('software', 'Software'),
        ('mobiliario', 'Mobiliário'),
        ('equipamento', 'Equipamento'),
        ('material', 'Material de Escritório'),
        ('marketing', 'Marketing'),
        ('servicos', 'Serviços'),
        ('outros', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('planejada', 'Planejada'),
        ('aprovada', 'Aprovada'),
        ('comprada', 'Comprada'),
        ('entregue', 'Entregue'),
        ('cancelada', 'Cancelada'),
    ]
    
    nome = models.CharField(max_length=200, verbose_name="Nome do Item")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, verbose_name="Categoria")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planejada', verbose_name="Status")
    data_compra = models.DateField(null=True, blank=True, verbose_name="Data da Compra")
    fornecedor = models.CharField(max_length=200, blank=True, verbose_name="Fornecedor")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Compra da Empresa"
        verbose_name_plural = "Compras da Empresa"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.nome} - R$ {self.valor} ({self.get_status_display()})"

class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Usuário do Sistema")
    nome_empresa = models.CharField(max_length=200, blank=True, verbose_name="Nome da Empresa")
    contato_principal = models.CharField(max_length=200, blank=True, verbose_name="Contato Principal")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    email_contato = models.EmailField(blank=True, verbose_name="Email de Contato")
    endereco = models.TextField(blank=True, verbose_name="Endereço")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['usuario__first_name', 'usuario__last_name']
    
    def __str__(self):
        nome = f"{self.usuario.first_name} {self.usuario.last_name}".strip()
        if self.nome_empresa:
            return f"{nome} ({self.nome_empresa})"
        return nome or self.usuario.username

class Projeto(models.Model):
    TIPO_PAGAMENTO_CHOICES = [
        ('avista', 'À Vista'),
        ('parcelado', 'Parcelado'),
        ('entrada_parcelas', 'Entrada + Parcelas'),
    ]
    
    STATUS_CHOICES = [
        ('orcamento', 'Orçamento'),
        ('aprovado', 'Aprovado'),
        ('desenvolvimento', 'Em Desenvolvimento'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    TIPO_PROJETO_CHOICES = [
        ('site', 'Site'),
        ('bot_ia', 'Bot com IA'),
        ('bot_padrao', 'Bot sem IA'),
        ('sheets', 'Envio via Google Sheets'),
    ]

    tipo = models.CharField(max_length=20,choices=TIPO_PROJETO_CHOICES,default='site',verbose_name="Tipo de Projeto")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    nome = models.CharField(max_length=200, verbose_name="Nome do Projeto")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total")
    tipo_pagamento = models.CharField(max_length=20, choices=TIPO_PAGAMENTO_CHOICES, verbose_name="Tipo de Pagamento")
    valor_entrada = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Valor da Entrada")
    numero_parcelas = models.IntegerField(default=1, verbose_name="Número de Parcelas")
    dia_vencimento_parcelas = models.IntegerField(default=10, verbose_name="Dia de Vencimento das Parcelas")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='orcamento', verbose_name="Status")
    data_inicio = models.DateField(null=True, blank=True, verbose_name="Data de Início")
    data_conclusao = models.DateField(null=True, blank=True, verbose_name="Data de Conclusão")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.nome} - {self.cliente}"
    
    @property
    def valor_parcela(self):
        if self.numero_parcelas > 0:
            valor_a_parcelar = self.valor_total - self.valor_entrada
            return valor_a_parcelar / self.numero_parcelas
        return Decimal('0.00')
    
    def criar_parcelas(self):
        """Cria as parcelas do projeto"""
        # Remove parcelas existentes
        self.parcelas.all().delete()
        
        if self.numero_parcelas > 0 and self.data_inicio:
            valor_parcela = self.valor_parcela
            
            for i in range(1, self.numero_parcelas + 1):
                # Calcula a data de vencimento
                data_vencimento = self.data_inicio + relativedelta(months=i-1)
                data_vencimento = data_vencimento.replace(day=self.dia_vencimento_parcelas)
                
                ParcelaProjeto.objects.create(
                    projeto=self,
                    numero_parcela=i,
                    valor=valor_parcela,
                    data_vencimento=data_vencimento
                )

class ParcelaProjeto(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Paga'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]
    
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='parcelas', verbose_name="Projeto")
    numero_parcela = models.IntegerField(verbose_name="Número da Parcela")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    data_pagamento = models.DateField(null=True, blank=True, verbose_name="Data de Pagamento")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Parcela do Projeto"
        verbose_name_plural = "Parcelas dos Projetos"
        ordering = ['projeto', 'numero_parcela']
        unique_together = ['projeto', 'numero_parcela']
    
    def __str__(self):
        return f"{self.projeto.nome} - Parcela {self.numero_parcela}/{self.projeto.numero_parcelas}"
    
    @property
    def dias_vencimento(self):
        if self.status == 'paga':
            return 0
        return (self.data_vencimento - date.today()).days
    
    def save(self, *args, **kwargs):
        # Atualiza status automaticamente
        if self.status == 'pendente' and self.data_vencimento < date.today():
            self.status = 'vencida'
        elif self.data_pagamento and self.status in ['pendente', 'vencida']:
            self.status = 'paga'
        super().save(*args, **kwargs)

class ServicoHospedagem(models.Model):
    TIPO_CHOICES = [
        ('dominio', 'Domínio'),
        ('hospedagem', 'Hospedagem'),
        ('email', 'Email'),
        ('ssl', 'Certificado SSL'),
        ('backup', 'Backup'),
        ('cdn', 'CDN'),
        ('outros', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('suspenso', 'Suspenso'),
        ('cancelado', 'Cancelado'),
        ('expirado', 'Expirado'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    nome = models.CharField(max_length=200, verbose_name="Nome do Serviço")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Serviço")
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Mensal")
    dia_vencimento = models.IntegerField(default=10, verbose_name="Dia de Vencimento")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo', verbose_name="Status")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim = models.DateField(null=True, blank=True, verbose_name="Data de Fim")
    provedor = models.CharField(max_length=200, blank=True, verbose_name="Provedor")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Serviço de Hospedagem"
        verbose_name_plural = "Serviços de Hospedagem"
        ordering = ['cliente', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {self.cliente} (R$ {self.valor_mensal}/mês)"
    
    def proximo_vencimento(self):
        """Retorna a próxima data de vencimento"""
        hoje = date.today()
        if hoje.day <= self.dia_vencimento:
            return hoje.replace(day=self.dia_vencimento)
        else:
            proximo_mes = hoje + relativedelta(months=1)
            return proximo_mes.replace(day=self.dia_vencimento)

class PagamentoHospedagem(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('vencido', 'Vencido'),
        ('cancelado', 'Cancelado'),
    ]
    
    servico = models.ForeignKey(ServicoHospedagem, on_delete=models.CASCADE, related_name='pagamentos', verbose_name="Serviço")
    mes_referencia = models.DateField(verbose_name="Mês de Referência")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    data_pagamento = models.DateField(null=True, blank=True, verbose_name="Data de Pagamento")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Pagamento de Hospedagem"
        verbose_name_plural = "Pagamentos de Hospedagem"
        ordering = ['-data_vencimento']
        unique_together = ['servico', 'mes_referencia']
    
    def __str__(self):
        return f"{self.servico.nome} - {self.mes_referencia.strftime('%m/%Y')}"
    
    @property
    def dias_vencimento(self):
        if self.status == 'pago':
            return 0
        return (self.data_vencimento - date.today()).days
    
    def save(self, *args, **kwargs):
        # Atualiza status automaticamente
        if self.status == 'pendente' and self.data_vencimento < date.today():
            self.status = 'vencido'
        elif self.data_pagamento and self.status in ['pendente', 'vencido']:
            self.status = 'pago'
        super().save(*args, **kwargs)

class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('parcela_vencendo', 'Parcela Vencendo'),
        ('parcela_vencida', 'Parcela Vencida'),
        ('hospedagem_vencendo', 'Hospedagem Vencendo'),
        ('hospedagem_vencida', 'Hospedagem Vencida'),
        ('gasto_fixo_vencendo', 'Gasto Fixo Vencendo'),
        ('projeto_atrasado', 'Projeto Atrasado'),
        ('cliente_inadimplente', 'Cliente Inadimplente'),
    ]
    
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    mensagem = models.TextField(verbose_name="Mensagem")
    lida = models.BooleanField(default=False, verbose_name="Lida")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    # Campos opcionais para referência
    parcela_projeto = models.ForeignKey(ParcelaProjeto, on_delete=models.CASCADE, null=True, blank=True)
    pagamento_hospedagem = models.ForeignKey(PagamentoHospedagem, on_delete=models.CASCADE, null=True, blank=True)
    gasto_fixo = models.ForeignKey(GastoFixo, on_delete=models.CASCADE, null=True, blank=True)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"
