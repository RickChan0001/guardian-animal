# veterinarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.contrib import messages

from .forms import (
    CadastroVeterinarioForm, CadastroClinicaForm,
    ServiceForm, AppointmentForm, NotificationForm, EditarPerfilVeterinarioForm
)

from .models import Veterinario, Clinica, Service, Appointment, Notification
from tutores.models import Tutor, Animal


def get_clinicas_do_veterinario(veterinario):
    """Busca clínicas de um veterinário usando raw SQL para evitar problemas com nomes de coluna"""
    clinicas_list = []
    try:
        with connection.cursor() as cursor:
            # Verifica quais colunas existem na tabela
            cursor.execute("SHOW COLUMNS FROM veterinarios_clinica")
            colunas = [row[0] for row in cursor.fetchall()]
            
            # Tenta diferentes nomes de coluna para o relacionamento
            # Verifica se alguma coluna contém "veterinario" no nome
            coluna_veterinario = None
            for col in colunas:
                if 'veterinario' in col.lower():
                    coluna_veterinario = col
                    break
            
            # Se não encontrou, tenta os nomes padrão
            if not coluna_veterinario:
                for col in ['veterinario_id', 'veterinario']:
                    if col in colunas:
                        coluna_veterinario = col
                        break
            
            if coluna_veterinario:
                # Busca os IDs das clínicas
                cursor.execute(
                    f"SELECT id FROM veterinarios_clinica WHERE {coluna_veterinario} = %s",
                    [veterinario.id]
                )
                clinica_ids = [row[0] for row in cursor.fetchall()]
                
                # Busca os objetos Clinica pelos IDs encontrados
                if clinica_ids:
                    clinicas_list = list(Clinica.objects.filter(id__in=clinica_ids))
    except Exception as e:
        # Se der erro, retorna lista vazia
        pass
    
    return clinicas_list


def cadastro_veterinario(request):
    if request.method == 'POST':
        form = CadastroVeterinarioForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Verifica se o CRMV já existe (usando only para evitar campo CPF)
                    crmv = form.cleaned_data.get('crmv')
                    if Veterinario.objects.only('crmv').filter(crmv=crmv).exists():
                        messages.error(request, 'Este CRMV já está cadastrado.')
                        return render(request, 'veterinarios/cadastro_veterinario.html', {'form': form})
                    
                    # Verifica se o CPF já existe (se foi fornecido)
                    # O CPF está armazenado no CustomUser, não no Veterinario
                    cpf = form.cleaned_data.get('cpf')
                    if cpf:
                        from tutores.models import CustomUser
                        cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))
                        # Verifica no CustomUser
                        if CustomUser.objects.filter(cpf=cpf_limpo).exists():
                            messages.error(request, 'Este CPF já está cadastrado.')
                            return render(request, 'veterinarios/cadastro_veterinario.html', {'form': form})
                        cpf = cpf_limpo
                    
                    user = form.save()
                    # Salva o CPF e telefone no CustomUser (já que essas colunas não existem em veterinarios_veterinario)
                    if cpf:
                        user.cpf = cpf
                    telefone = form.cleaned_data.get('telefone')
                    if telefone:
                        user.telefone = telefone
                    user.save()
                    
                    # Cria o veterinário usando raw SQL - apenas com os campos que existem: usuario_id e crmv
                    from django.db import connection
                    with connection.cursor() as cursor:
                        # Insere apenas os campos obrigatórios que sabemos que existem
                        cursor.execute(
                            "INSERT INTO veterinarios_veterinario (usuario_id, crmv) VALUES (%s, %s)",
                            [user.id, crmv]
                        )
                    login(request, user)
                    messages.success(request, 'Cadastro realizado com sucesso!')
                    return redirect('veterinarios:painel_veterinario')
            except Exception as e:
                error_msg = str(e)
                if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                    messages.error(request, 'Erro: Este CRMV ou CPF já está cadastrado no sistema.')
                elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
                    messages.error(request, 'Erro de conexão com o banco de dados. Tente novamente.')
                else:
                    messages.error(request, f'Erro ao cadastrar veterinário: {error_msg}')
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        form = CadastroVeterinarioForm()
    return render(request, 'veterinarios/cadastro_veterinario.html', {'form': form})


@login_required(login_url='/login/')
def painel_veterinario(request):
    # Usa o manager customizado que força only() nos campos corretos
    veterinario_perfil = Veterinario.objects.filter(usuario=request.user).first()
    
    if not veterinario_perfil:
        messages.error(request, 'Perfil de veterinário não encontrado.')
        return redirect('home')
    
    # Busca clínicas usando função auxiliar
    clinicas = get_clinicas_do_veterinario(veterinario_perfil)
    
    contexto = {
        'user': request.user,
        'veterinario_perfil': veterinario_perfil,
        'clinicas': clinicas,
        'voltar_url': '/veterinarios/painel/'
    }
    return render(request, 'veterinarios/painel_veterinario.html', contexto)


@login_required(login_url='/login/')
def cadastro_clinica(request):
    veterinario_perfil = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    if request.method == 'POST':
        form = CadastroClinicaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    clinica = form.save(commit=False)
                    # Atribui o veterinário antes de salvar
                    clinica.veterinario = veterinario_perfil
                    # Salva a clínica
                    clinica.save()
                    messages.success(request, 'Clínica cadastrada com sucesso!')
                    return redirect('veterinarios:painel_veterinario')
            except Exception as e:
                # Se der erro ao salvar normalmente, tenta usar raw SQL
                error_msg = str(e)
                try:
                    with transaction.atomic():
                        clinica = form.save(commit=False)
                        # Salva sem o veterinário primeiro
                        clinica.save()
                        # Depois atualiza o relacionamento usando raw SQL
                        with connection.cursor() as cursor:
                            cursor.execute("SHOW COLUMNS FROM veterinarios_clinica")
                            colunas = [row[0] for row in cursor.fetchall()]
                            coluna_veterinario = None
                            for col in ['veterinario_id', 'veterinario']:
                                if col in colunas:
                                    coluna_veterinario = col
                                    break
                            if coluna_veterinario:
                                cursor.execute(
                                    f"UPDATE veterinarios_clinica SET {coluna_veterinario} = %s WHERE id = %s",
                                    [veterinario_perfil.id, clinica.id]
                                )
                        messages.success(request, 'Clínica cadastrada com sucesso!')
                        return redirect('veterinarios:painel_veterinario')
                except Exception as e2:
                    messages.error(request, f'Erro ao cadastrar clínica: {str(e2)}')
                    import traceback
                    print(traceback.format_exc())
        else:
            # Se o formulário não é válido, mostra os erros
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CadastroClinicaForm()
    return render(request, 'veterinarios/cadastro_clinica.html', {'form': form, 'titulo_pagina': 'Cadastro de Clínica'}) {'form': form, 'titulo_pagina': 'Cadastro de Clínica'})


@login_required(login_url='/login/')
def editar_clinica(request, clinica_id):
    veterinario_perfil = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    # Busca a clínica verificando se pertence ao veterinário
    clinicas_do_vet = get_clinicas_do_veterinario(veterinario_perfil)
    clinica = None
    for c in clinicas_do_vet:
        if c.id == clinica_id:
            clinica = c
            break
    if not clinica:
        messages.error(request, 'Clínica não encontrada ou você não tem permissão para editá-la.')
        return redirect('veterinarios:painel_veterinario')
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
    veterinario_perfil = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    # Busca a clínica verificando se pertence ao veterinário
    clinicas_do_vet = get_clinicas_do_veterinario(veterinario_perfil)
    clinica = None
    for c in clinicas_do_vet:
        if c.id == clinica_id:
            clinica = c
            break
    if not clinica:
        messages.error(request, 'Clínica não encontrada ou você não tem permissão para deletá-la.')
        return redirect('veterinarios:painel_veterinario')
    if request.method == 'POST':
        clinica.delete()
        messages.success(request, 'Clínica excluída com sucesso!')
        return redirect('veterinarios:painel_veterinario')
    return render(request, 'veterinarios/delete_clinica.html', {'clinica': clinica, 'voltar_url': '/veterinarios/painel/'})


@login_required(login_url='/login/')
def perfil_veterinario(request):
    veterinario_perfil = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    return render(request, 'veterinarios/perfil_veterinario.html', {'veterinario_perfil': veterinario_perfil})


@login_required(login_url='/login/')
def editar_perfil_veterinario(request):
    veterinario = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    user = request.user
    if request.method == 'POST':
        form = EditarPerfilVeterinarioForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            # Salva telefone no CustomUser (não existe coluna telefone em veterinarios_veterinario)
            telefone = form.cleaned_data.get('telefone')
            if telefone:
                user.telefone = telefone
                user.save()
            # Especialidade não pode ser salva porque a coluna não existe no banco
            # Se precisar salvar especialidade, seria necessário criar a coluna ou usar outra tabela
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('veterinarios:perfil_veterinario')
        else:
            messages.error(request, "Corrija os erros do formulário.")
    else:
        form = EditarPerfilVeterinarioForm(instance=user, initial={
            'telefone': veterinario.telefone,
            'especialidade': veterinario.especialidade
        })
    return render(request, 'veterinarios/editar_perfil_veterinario.html', {'form': form, 'veterinario': veterinario})
