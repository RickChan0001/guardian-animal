# veterinarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from .forms import (
    CadastroVeterinarioForm, CadastroClinicaForm,
    ServiceForm, AppointmentForm, NotificationForm, EditarPerfilVeterinarioForm
)

from .models import Veterinario, Clinica, Service, Appointment, Notification
from tutores.models import Tutor, Animal


def cadastro_veterinario(request):
    if request.method == 'POST':
        form = CadastroVeterinarioForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    Veterinario.objects.create(
                        usuario=user,
                        cpf=form.cleaned_data.get('cpf'),
                        crmv=form.cleaned_data.get('crmv'),
                        telefone=form.cleaned_data.get('telefone'),
                        especialidade=form.cleaned_data.get('especialidade')
                    )
                    login(request, user)
                    messages.success(request, 'Cadastro realizado com sucesso!')
                    return redirect('veterinarios:painel_veterinario')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar veterinário: {e}')
    else:
        form = CadastroVeterinarioForm()
    return render(request, 'veterinarios/cadastro_veterinario.html', {'form': form})


@login_required(login_url='/login/')
def painel_veterinario(request):
    veterinario_perfil = Veterinario.objects.filter(usuario=request.user).first()
    clinicas = Clinica.objects.filter(veterinario=veterinario_perfil)
    contexto = {
        'user': request.user,
        'veterinario_perfil': veterinario_perfil,
        'clinicas': clinicas,
        'voltar_url': '/veterinarios/painel/'
    }
    return render(request, 'veterinarios/painel_veterinario.html', contexto)


@login_required(login_url='/login/')
def cadastro_clinica(request):
    veterinario_perfil = get_object_or_404(Veterinario, usuario=request.user)
    if request.method == 'POST':
        form = CadastroClinicaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    clinica = form.save(commit=False)
                    clinica.veterinario = veterinario_perfil
                    clinica.save()
                    messages.success(request, 'Clínica cadastrada com sucesso!')
                    return redirect('veterinarios:painel_veterinario')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar clínica: {e}')
    else:
        form = CadastroClinicaForm()
    return render(request, 'veterinarios/cadastro_clinica.html', {'form': form, 'titulo_pagina': 'Cadastro de Clínica'})


@login_required(login_url='/login/')
def editar_clinica(request, clinica_id):
    veterinario_perfil = get_object_or_404(Veterinario, usuario=request.user)
    clinica = get_object_or_404(Clinica, id=clinica_id, veterinario=veterinario_perfil)
    if request.method == 'POST':
        form = CadastroClinicaForm(request.POST, request.FILES, instance=clinica)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clínica editada com sucesso!')
            return redirect('veterinarios:painel_veterinario')
    else:
        form = CadastroClinicaForm(instance=clinica)
    return render(request, 'veterinarios/editar_clinica.html', {'form': form, 'clinica': clinica, 'titulo_pagina': 'Editar Clínica'})


@login_required(login_url='/login/')
def delete_clinica(request, clinica_id):
    veterinario_perfil = get_object_or_404(Veterinario, usuario=request.user)
    clinica = get_object_or_404(Clinica, id=clinica_id, veterinario=veterinario_perfil)
    if request.method == 'POST':
        clinica.delete()
        messages.success(request, 'Clínica excluída com sucesso!')
        return redirect('veterinarios:painel_veterinario')
    return render(request, 'veterinarios/delete_clinica.html', {'clinica': clinica, 'voltar_url': '/veterinarios/painel/'})


@login_required(login_url='/login/')
def perfil_veterinario(request):
    veterinario_perfil = get_object_or_404(Veterinario, usuario=request.user)
    return render(request, 'veterinarios/perfil_veterinario.html', {'veterinario_perfil': veterinario_perfil})


@login_required(login_url='/login/')
def editar_perfil_veterinario(request):
    veterinario = get_object_or_404(Veterinario, usuario=request.user)
    user = request.user
    if request.method == 'POST':
        form = EditarPerfilVeterinarioForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            veterinario.telefone = form.cleaned_data.get('telefone')
            veterinario.especialidade = form.cleaned_data.get('especialidade')
            veterinario.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('veterinarios:perfil_veterinario')
        else:
            messages.error(request, "Corrija os erros do formulário.")
    else:
        form = EditarPerfilVeterinarioForm(instance=user)
    return render(request, 'veterinarios/editar_perfil_veterinario.html', {'form': form, 'veterinario': veterinario})
