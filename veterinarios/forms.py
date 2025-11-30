# veterinarios/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Clinica, Service, Appointment, Notification
import re

User = get_user_model()


class CadastroVeterinarioForm(UserCreationForm):
    nome_completo = forms.CharField(max_length=300, required=True, label='Nome Completo')
    email = forms.EmailField(required=True, label='E-mail')
    cpf = forms.CharField(max_length=14, required=False, label='CPF')
    crmv = forms.CharField(max_length=20, required=True, label='CRMV')
    telefone = forms.CharField(max_length=15, required=False, label='Telefone')
    especialidade = forms.CharField(max_length=100, required=False, label='Especialidade')

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove o campo username do formulário
        if 'username' in self.fields:
            del self.fields['username']

    def clean_crmv(self):
        crmv = self.cleaned_data.get('crmv')
        if not crmv:
            raise forms.ValidationError("CRMV é obrigatório.")
        # Remove espaços e converte para maiúsculas
        crmv = crmv.strip().upper()
        # CRMV pode ter formato: números, letras, hífen (ex: 12345-SP, ABC1234-RJ)
        # Remove hífen para validação
        crmv_sem_hifen = crmv.replace('-', '')
        # Verifica se contém apenas letras e números
        if not crmv_sem_hifen.isalnum():
            raise forms.ValidationError("CRMV deve conter apenas letras, números e hífen (ex: 12345-SP).")
        if len(crmv_sem_hifen) < 3:
            raise forms.ValidationError("CRMV deve ter pelo menos 3 caracteres.")
        return crmv

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not cpf:
            return None
        cpf_numeros = re.sub(r'\D', '', cpf)
        if not cpf_numeros.isdigit():
            raise forms.ValidationError("CPF/CNPJ deve conter apenas números.")
        if len(cpf_numeros) == 11:
            if not self.validar_cpf(cpf_numeros):
                raise forms.ValidationError("CPF inválido.")
            return cpf_numeros
        if len(cpf_numeros) == 14:
            if not self.validar_cnpj(cpf_numeros):
                raise forms.ValidationError("CNPJ inválido.")
            return cpf_numeros
        raise forms.ValidationError("CPF deve ter 11 dígitos ou CNPJ 14 dígitos.")

    def validar_cpf(self, cpf):
        if cpf == cpf[0] * len(cpf):
            return False
        for i in [9, 10]:
            soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
            dv = ((soma * 10) % 11) % 10
            if dv != int(cpf[i]):
                return False
        return True

    def validar_cnpj(self, cnpj):
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
        dv1 = 11 - soma % 11
        dv1 = 0 if dv1 >= 10 else dv1
        if dv1 != int(cnpj[12]):
            return False
        pesos2 = [6] + pesos1
        soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
        dv2 = 11 - soma % 11
        dv2 = 0 if dv2 >= 10 else dv2
        return dv2 == int(cnpj[13])

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if not telefone:
            return None
        telefone_numeros = re.sub(r'\D', '', telefone)
        if not telefone_numeros.isdigit():
            raise forms.ValidationError("Telefone deve conter apenas números.")
        if len(telefone_numeros) != 11:
            raise forms.ValidationError("Telefone deve ter 11 dígitos.")
        return telefone_numeros

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está em uso.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        # Gera username automaticamente a partir do email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        nome_completo = self.cleaned_data['nome_completo'].strip()
        partes = nome_completo.split(maxsplit=1)
        user.username = username
        user.email = email
        user.first_name = partes[0]
        user.last_name = partes[1] if len(partes) > 1 else ''
        # Define telefone e CPF ANTES do save para garantir que sejam incluídos no INSERT
        telefone = self.cleaned_data.get('telefone')
        user.telefone = telefone if telefone else ''
        cpf = self.cleaned_data.get('cpf')
        user.cpf = cpf if cpf else ''
        if commit:
            user.save()
        return user


class EditarPerfilVeterinarioForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='E-mail')
    telefone = forms.CharField(max_length=15, required=False, label='Telefone')
    especialidade = forms.CharField(max_length=100, required=False, label='Especialidade')

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class CadastroClinicaForm(forms.ModelForm):
    foto = forms.ImageField(required=False)

    class Meta:
        model = Clinica
        fields = [
            'nome', 'cnpj', 'rua', 'numero', 'bairro',
            'observacoes', 'telefone', 'foto'
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price']


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['veterinarian', 'clinic', 'animal', 'service', 'date', 'notes']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['message']
