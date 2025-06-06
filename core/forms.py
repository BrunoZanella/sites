from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    ConfiguracaoUsuario, Contato, Mensagem, GastoFixo, CompraEmpresa,
    Cliente, Projeto, ServicoHospedagem
)
import pandas as pd

class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class ConfiguracaoUsuarioForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoUsuario
        fields = [
            'nome_pagina_contatos', 'nome_pagina_mensagens',
            'coluna_nome', 'coluna_numero', 'coluna_enviado', 'coluna_mensagem',
            'coluna_quantidade'
        ]
        widgets = {
            'nome_pagina_contatos': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_pagina_mensagens': forms.TextInput(attrs={'class': 'form-control'}),
            'coluna_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'coluna_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'coluna_enviado': forms.TextInput(attrs={'class': 'form-control'}),
            'coluna_mensagem': forms.TextInput(attrs={'class': 'form-control'}),
            'coluna_quantidade': forms.TextInput(attrs={'class': 'form-control'}),
        }

class EvolutionConfigForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoUsuario
        fields = ['url_evolution', 'instancia_evolution', 'api_evolution']
        widgets = {
            'url_evolution': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://evolution.apex.dev.br'
            }),
            'instancia_evolution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sua Instância Evolution'
            }),
            'api_evolution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sua API Evolution'
            }),
        }

class UploadContatosForm(forms.Form):
    arquivo = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls,.csv'}),
        help_text="Formatos aceitos: Excel (.xlsx, .xls) ou CSV"
    )
    
    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo:
            extensoes_validas = ['.xlsx', '.xls', '.csv']
            if not any(arquivo.name.lower().endswith(ext) for ext in extensoes_validas):
                raise forms.ValidationError("Formato de arquivo não suportado. Use Excel ou CSV.")
        return arquivo

class ContatoForm(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ['nome', 'numero']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5511999999999'}),
        }

class MensagemForm(forms.ModelForm):
    class Meta:
        model = Mensagem
        fields = ['texto_mensagem', 'quantidade_maxima', 'ativa']
        widgets = {
            'texto_mensagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'quantidade_maxima': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Formulários para gestão de usuários
class EditarUsuarioForm(forms.ModelForm):
    is_superuser = forms.BooleanField(required=False, label="Superusuário")
    is_staff = forms.BooleanField(required=False, label="Staff")
    is_active = forms.BooleanField(required=False, label="Ativo")
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CriarUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    is_superuser = forms.BooleanField(required=False, label="Superusuário")
    is_staff = forms.BooleanField(required=False, label="Staff")
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'is_staff', 'is_superuser')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs.update({'class': 'form-control'})

# Formulários para gestão empresarial
class GastoFixoForm(forms.ModelForm):
    class Meta:
        model = GastoFixo
        fields = ['nome', 'categoria', 'valor', 'descricao', 'dia_vencimento', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CompraEmpresaForm(forms.ModelForm):
    class Meta:
        model = CompraEmpresa
        fields = ['nome', 'categoria', 'valor', 'descricao', 'status', 'data_compra', 'fornecedor', 'observacoes']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_compra': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fornecedor': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['usuario', 'nome_empresa', 'contato_principal', 'telefone', 'email_contato', 'endereco', 'observacoes']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'nome_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_principal': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email_contato': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = [
            'cliente', 'nome', 'descricao', 'valor_total', 'tipo_pagamento',
            'valor_entrada', 'numero_parcelas', 'dia_vencimento_parcelas',
            'status', 'data_inicio', 'data_conclusao', 'observacoes'
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valor_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'valor_entrada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'dia_vencimento_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_conclusao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ServicoHospedagemForm(forms.ModelForm):
    class Meta:
        model = ServicoHospedagem
        fields = [
            'cliente', 'nome', 'tipo', 'valor_mensal', 'dia_vencimento',
            'status', 'data_inicio', 'data_fim', 'provedor', 'observacoes'
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor_mensal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'provedor': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
