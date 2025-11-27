from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re
from .models import Tutor, Animal, CustomUser, PetHistory
from veterinarios.models import Veterinario


class CadastroTutorForm(UserCreationForm):
    cpf = forms.CharField(required=False)
    telefone = forms.CharField(required=False)
    localizacao_placeholder = forms.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email',
                'telefone', 'cpf', 'password1', 'password2')

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            if re.search(r'[a-zA-Z]', cpf):
                raise ValidationError("CPF não pode conter letras.")
            digits = re.sub(r'\D', '', cpf)
            if len(digits) != 11 or digits == digits[0] * 11:
                raise ValidationError("CPF inválido.")
            return digits
        return cpf

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if telefone:
            digits = re.sub(r'\D', '', telefone)
            if len(digits) != 11:
                raise ValidationError("Telefone deve ter 11 dígitos.")
            return digits
        return telefone

class EditarPerfilTutorForm(forms.ModelForm):
    cpf = forms.CharField(required=False)
    telefone = forms.CharField(required=False)
    localizacao_placeholder = forms.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'cpf', 'telefone', 'localizacao_placeholder')

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            digits = re.sub(r'\D', '', cpf)
            if len(digits) != 11 or digits == digits[0] * 11:
                raise ValidationError("CPF inválido.")
            return digits
        return cpf

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if telefone:
            digits = re.sub(r'\D', '', telefone)
            if len(digits) != 11:
                raise ValidationError("Telefone deve ter 11 dígitos.")
            return digits
        return telefone

class CadastroAnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ['nome', 'especie', 'raca', 'idade', 'peso',
            'altura', 'microchip', 'observacoes', 'foto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        especie = None
        if self.instance and self.instance.pk:
            especie = self.instance.especie
        if 'data' in kwargs:
            especie = kwargs['data'].get('especie', especie)
        self.fields['raca'].widget = forms.Select()
        self.fields['raca'].choices = self.get_racas_choices(especie)

    def get_racas_choices(self, especie):
        racas = {
            'cachorro': ['labrador', 'poodle', 'bulldog', 'vira_lata', 'outro'],
            'gato': ['persa', 'siames', 'maine_coon', 'vira_lata', 'outro'],
            'passaro': ['canario', 'calopsita', 'periquito', 'outro'],
            'outro': ['outro'],
        }
        if especie not in racas:
            especie = 'outro'
        choices = [(r, r.replace('_', ' ').capitalize()) for r in racas[especie]]
        choices.insert(0, ('', 'Selecione a raça'))
        return choices

    def clean_microchip(self):
        microchip = self.cleaned_data.get('microchip')
        if microchip:
            digits = microchip.replace(' ', '').replace('-', '')
            if not digits.isdigit():
                raise ValidationError("Microchip deve conter apenas números.")
            if len(digits) != 15:
                raise ValidationError("Microchip deve ter 15 dígitos.")
            return digits
        return microchip

class PetHistoryForm(forms.ModelForm):
    class Meta:
        model = PetHistory
        fields = ['description', 'veterinarian']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['veterinarian'].queryset = Veterinario.objects.all()
