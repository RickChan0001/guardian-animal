# veterinarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
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
                    # Normaliza o CRMV para comparação (maiúsculas)
                    crmv_normalizado = crmv.upper() if crmv else ''
                    # Verifica se existe CRMV com mesmo valor (case-insensitive)
                    if Veterinario.objects.only('crmv').filter(
                        Q(crmv__iexact=crmv_normalizado) | Q(crmv=crmv_normalizado)
                    ).exists():
                        form.add_error('crmv', 'Este CRMV já está cadastrado.')
                        return render(request, 'veterinarios/cadastro_veterinario.html', {'form': form})
                    
                    # Verifica se o CPF já existe (se foi fornecido)
                    # O CPF está armazenado no CustomUser, não no Veterinario
                    # O CPF já vem limpo (apenas números) do método clean_cpf do form
                    cpf = form.cleaned_data.get('cpf')
                    if cpf:
                        from tutores.models import CustomUser
                        # Verifica no CustomUser (o CPF já está limpo do clean_cpf)
                        if CustomUser.objects.filter(cpf=cpf).exists():
                            form.add_error('cpf', 'Este CPF já está cadastrado.')
                            return render(request, 'veterinarios/cadastro_veterinario.html', {'form': form})
                    
                    # Prepara dados do usuário
                    email = form.cleaned_data['email']
                    nome_completo = form.cleaned_data['nome_completo'].strip()
                    partes = nome_completo.split(maxsplit=1)
                    first_name = partes[0]
                    last_name = partes[1] if len(partes) > 1 else ''
                    
                    # Gera username único
                    base_username = email.split('@')[0]
                    username = base_username
                    counter = 1
                    from tutores.models import CustomUser
                    while CustomUser.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Prepara telefone e CPF
                    telefone = form.cleaned_data.get('telefone')
                    cpf = form.cleaned_data.get('cpf')
                    
                    # Hash da senha
                    from django.contrib.auth.hashers import make_password
                    password = form.cleaned_data['password1']
                    password_hash = make_password(password)
                    
                    # Insere o usuário usando SQL direto para garantir que telefone e CPF sejam incluídos
                    from django.db import connection
                    from django.utils.timezone import now
                    
                    with connection.cursor() as cursor:
                        # Prepara valores - usa string vazia se não fornecido (evita erro do MySQL)
                        telefone_valor = telefone if telefone else ''
                        cpf_valor = cpf if cpf else ''
                        
                        # Insere o usuário com TODOS os campos obrigatórios
                        # Inclui telefone e CPF explicitamente (mesmo que vazio) para evitar erro
                        cursor.execute("""
                            INSERT INTO tutores_customuser 
                            (username, email, password, first_name, last_name, telefone, cpf, 
                             is_staff, is_active, is_superuser, date_joined, last_login)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            username,
                            email,
                            password_hash,
                            first_name,
                            last_name,
                            telefone_valor,  # String vazia se não fornecido
                            cpf_valor,  # String vazia se não fornecido
                            0,  # is_staff (0 = False no MySQL)
                            1,  # is_active (1 = True no MySQL)
                            0,  # is_superuser (0 = False no MySQL)
                            now(),  # date_joined
                            None  # last_login (NULL é permitido)
                        ])
                        user_id = cursor.lastrowid
                    
                    # Busca o usuário criado
                    user = CustomUser.objects.get(id=user_id)
                    
                    # Cria o veterinário usando raw SQL
                    # A tabela veterinarios_veterinario tem campo telefone que é NOT NULL
                    with connection.cursor() as cursor:
                        # Insere com todos os campos obrigatórios, incluindo telefone
                        # Usa o CRMV normalizado (maiúsculas)
                        # Telefone da tabela veterinario (não do CustomUser) - usa string vazia se não fornecido
                        telefone_vet = telefone if telefone else ''
                        cursor.execute(
                            "INSERT INTO veterinarios_veterinario (usuario_id, crmv, telefone) VALUES (%s, %s, %s)",
                            [user.id, crmv_normalizado, telefone_vet]
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
            # Os erros do formulário serão exibidos automaticamente no template
            pass
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
    return render(request, 'veterinarios/cadastro_clinica.html', {'form': form, 'titulo_pagina': 'Cadastro de Clínica'})


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
            # Salva telefone no CustomUser
            telefone = form.cleaned_data.get('telefone')
            if telefone:
                user.telefone = telefone
            else:
                user.telefone = None
            user.save()
            
            # Salva especialidade na tabela veterinarios_veterinario usando SQL direto
            # Pega do form.cleaned_data se disponível, senão do POST
            especialidade = form.cleaned_data.get('especialidade') if 'especialidade' in form.cleaned_data else request.POST.get('especialidade', '').strip()
            especialidade_valor = especialidade if especialidade else None
            
            from django.db import connection
            try:
                with connection.cursor() as cursor:
                    # Verifica se a coluna especialidade existe
                    cursor.execute("SHOW COLUMNS FROM veterinarios_veterinario LIKE 'especialidade'")
                    coluna_existe = cursor.fetchone() is not None
                    
                    if coluna_existe:
                        # Se a coluna existe, atualiza
                        cursor.execute(
                            "UPDATE veterinarios_veterinario SET especialidade = %s WHERE id = %s",
                            [especialidade_valor, veterinario.id]
                        )
                    else:
                        # Se não existe, tenta adicionar a coluna
                        try:
                            cursor.execute(
                                "ALTER TABLE veterinarios_veterinario ADD COLUMN especialidade VARCHAR(100) NULL DEFAULT NULL"
                            )
                            # Atualiza após criar a coluna
                            cursor.execute(
                                "UPDATE veterinarios_veterinario SET especialidade = %s WHERE id = %s",
                                [especialidade_valor, veterinario.id]
                            )
                        except Exception as alter_error:
                            # Se não conseguir adicionar, apenas registra o erro
                            import traceback
                            print(f"Erro ao adicionar coluna especialidade: {alter_error}")
                            print(traceback.format_exc())
            except Exception as e:
                # Se der erro, apenas registra mas não impede o salvamento
                import traceback
                print(f"Erro ao salvar especialidade: {e}")
                print(traceback.format_exc())
            
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
