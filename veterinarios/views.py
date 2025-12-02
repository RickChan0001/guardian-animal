# veterinarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.contrib import messages

from .forms import (
    CadastroVeterinarioForm, CadastroClinicaForm,
    ServiceForm, AppointmentForm, NotificationForm, EditarPerfilVeterinarioForm,
    EditarConsultaForm
)

from .models import Veterinario, Clinica, Service, Appointment, Notification
from django.db import connection
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


def criar_servicos_predefinidos(clinica):
    """Cria serviços pré-definidos para uma clínica"""
    servicos_predefinidos = [
        {
            'name': 'Consulta Geral',
            'description': 'Consulta veterinária geral para avaliação do animal',
            'price': 80.00
        },
        {
            'name': 'Vacinação',
            'description': 'Aplicação de vacinas conforme calendário vacinal',
            'price': 50.00
        },
        {
            'name': 'Castração',
            'description': 'Procedimento cirúrgico de castração',
            'price': 300.00
        },
        {
            'name': 'Exame de Sangue',
            'description': 'Exame laboratorial completo de sangue',
            'price': 120.00
        },
        {
            'name': 'Cirurgia',
            'description': 'Procedimento cirúrgico geral',
            'price': 500.00
        },
        {
            'name': 'Banho e Tosa',
            'description': 'Serviço de higiene e estética animal',
            'price': 60.00
        },
        {
            'name': 'Ultrassonografia',
            'description': 'Exame de imagem por ultrassom',
            'price': 150.00
        },
        {
            'name': 'Radiografia',
            'description': 'Exame de imagem por raio-X',
            'price': 100.00
        }
    ]
    
    try:
        # Tenta criar usando ORM
        for servico_data in servicos_predefinidos:
            Service.objects.get_or_create(
                clinic=clinica,
                name=servico_data['name'],
                defaults={
                    'description': servico_data['description'],
                    'price': servico_data['price']
                }
            )
    except Exception as e:
        # Se der erro com ORM, tenta usar raw SQL
        try:
            with connection.cursor() as cursor:
                # Verifica se a tabela existe
                cursor.execute("SHOW TABLES LIKE 'veterinarios_service'")
                if cursor.fetchone():
                    for servico_data in servicos_predefinidos:
                        # Verifica se o serviço já existe
                        cursor.execute(
                            "SELECT id FROM veterinarios_service WHERE clinic_id = %s AND name = %s",
                            [clinica.id, servico_data['name']]
                        )
                        if not cursor.fetchone():
                            # Insere o serviço
                            cursor.execute(
                                "INSERT INTO veterinarios_service (clinic_id, name, description, price) VALUES (%s, %s, %s, %s)",
                                [clinica.id, servico_data['name'], servico_data['description'], servico_data['price']]
                            )
        except Exception as e2:
            # Se der erro, apenas registra mas não impede o cadastro da clínica
            print(f"Erro ao criar serviços pré-definidos: {e2}")


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
                    # A tabela veterinarios_veterinario tem apenas: id, crmv, usuario_id
                    with connection.cursor() as cursor:
                        # Insere apenas os campos que existem na tabela
                        # Usa o CRMV normalizado (maiúsculas)
                        cursor.execute(
                            "INSERT INTO veterinarios_veterinario (usuario_id, crmv) VALUES (%s, %s)",
                            [user.id, crmv_normalizado]
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
                    # Cria serviços pré-definidos para a clínica
                    criar_servicos_predefinidos(clinica)
                    messages.success(request, 'Clínica cadastrada com sucesso! Serviços pré-definidos foram criados automaticamente.')
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
                        # Cria serviços pré-definidos para a clínica
                        criar_servicos_predefinidos(clinica)
                        messages.success(request, 'Clínica cadastrada com sucesso! Serviços pré-definidos foram criados automaticamente.')
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
        try:
            # Tenta deletar usando o ORM do Django
            clinica.delete()
            messages.success(request, 'Clínica excluída com sucesso!')
            return redirect('veterinarios:painel_veterinario')
        except Exception as e:
            # Se der erro, tenta deletar usando SQL direto
            error_msg = str(e)
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    # Deleta apenas a clínica
                    cursor.execute("DELETE FROM veterinarios_clinica WHERE id = %s", [clinica.id])
                messages.success(request, 'Clínica excluída com sucesso!')
                return redirect('veterinarios:painel_veterinario')
            except Exception as e2:
                messages.error(request, f'Erro ao deletar clínica: {str(e2)}')
    
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
            
            # Salva especialidade, formação e experiência na tabela veterinarios_veterinario usando SQL direto
            especialidade = form.cleaned_data.get('especialidade') if 'especialidade' in form.cleaned_data else request.POST.get('especialidade', '').strip()
            formacao = form.cleaned_data.get('formacao', '').strip() if 'formacao' in form.cleaned_data else ''
            experiencia = form.cleaned_data.get('experiencia', '').strip() if 'experiencia' in form.cleaned_data else ''
            
            from django.db import connection
            try:
                with connection.cursor() as cursor:
                    # Verifica quais colunas existem
                    cursor.execute("SHOW COLUMNS FROM veterinarios_veterinario")
                    colunas_existentes = [row[0] for row in cursor.fetchall()]
                    
                    # Atualiza especialidade
                    if 'especialidade' in colunas_existentes:
                        cursor.execute(
                            "UPDATE veterinarios_veterinario SET especialidade = %s WHERE id = %s",
                            [especialidade if especialidade else None, veterinario.id]
                        )
                    else:
                        try:
                            cursor.execute("ALTER TABLE veterinarios_veterinario ADD COLUMN especialidade VARCHAR(100) NULL")
                            cursor.execute(
                                "UPDATE veterinarios_veterinario SET especialidade = %s WHERE id = %s",
                                [especialidade if especialidade else None, veterinario.id]
                            )
                        except:
                            pass
                    
                    # Atualiza formacao
                    if 'formacao' in colunas_existentes:
                        cursor.execute(
                            "UPDATE veterinarios_veterinario SET formacao = %s WHERE id = %s",
                            [formacao if formacao else None, veterinario.id]
                        )
                    else:
                        try:
                            cursor.execute("ALTER TABLE veterinarios_veterinario ADD COLUMN formacao TEXT NULL")
                            cursor.execute(
                                "UPDATE veterinarios_veterinario SET formacao = %s WHERE id = %s",
                                [formacao if formacao else None, veterinario.id]
                            )
                        except:
                            pass
                    
                    # Atualiza experiencia
                    if 'experiencia' in colunas_existentes:
                        cursor.execute(
                            "UPDATE veterinarios_veterinario SET experiencia = %s WHERE id = %s",
                            [experiencia if experiencia else None, veterinario.id]
                        )
                    else:
                        try:
                            cursor.execute("ALTER TABLE veterinarios_veterinario ADD COLUMN experiencia TEXT NULL")
                            cursor.execute(
                                "UPDATE veterinarios_veterinario SET experiencia = %s WHERE id = %s",
                                [experiencia if experiencia else None, veterinario.id]
                            )
                        except:
                            pass
            except Exception as e:
                import traceback
                print(f"Erro ao salvar dados do veterinário: {e}")
                print(traceback.format_exc())
            
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('veterinarios:perfil_veterinario')
        else:
            messages.error(request, "Corrija os erros do formulário.")
    else:
        # Busca formacao e experiencia do banco
        formacao = None
        experiencia = None
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM veterinarios_veterinario")
                colunas = [row[0] for row in cursor.fetchall()]
                if 'formacao' in colunas:
                    cursor.execute("SELECT formacao FROM veterinarios_veterinario WHERE id = %s", [veterinario.id])
                    row = cursor.fetchone()
                    formacao = row[0] if row and row[0] else None
                if 'experiencia' in colunas:
                    cursor.execute("SELECT experiencia FROM veterinarios_veterinario WHERE id = %s", [veterinario.id])
                    row = cursor.fetchone()
                    experiencia = row[0] if row and row[0] else None
        except:
            pass
        
        form = EditarPerfilVeterinarioForm(instance=user, initial={
            'telefone': veterinario.telefone,
            'especialidade': veterinario.especialidade,
            'formacao': formacao,
            'experiencia': experiencia
        })
    return render(request, 'veterinarios/editar_perfil_veterinario.html', {'form': form, 'veterinario': veterinario})


@login_required(login_url='/login/')
def notificacoes_veterinario(request):
    """Exibe as notificações do veterinário"""
    notificacoes = Notification.objects.filter(user=request.user).order_by('-created_at')
    nao_lidas = notificacoes.filter(is_read=False).count()
    
    return render(request, 'veterinarios/notificacoes.html', {
        'notificacoes': notificacoes,
        'nao_lidas': nao_lidas
    })


@login_required(login_url='/login/')
def marcar_notificacao_lida_veterinario(request, notificacao_id):
    """Marca uma notificação como lida"""
    notificacao = get_object_or_404(Notification, id=notificacao_id, user=request.user)
    notificacao.is_read = True
    notificacao.save()
    return redirect('veterinarios:notificacoes_veterinario')


@login_required(login_url='/login/')
def cadastrar_consulta(request):
    """Permite ao veterinário cadastrar uma consulta"""
    veterinario = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, veterinarian=veterinario)
        if form.is_valid():
            try:
                appointment = form.save(commit=False)
                appointment.veterinarian = veterinario
                appointment.tutor = form.cleaned_data['tutor']
                appointment.save()
                
                # Envia notificação para o tutor
                from veterinarios.utils import enviar_notificacao
                tutor = appointment.tutor
                status_display = dict(Appointment.STATUS_CHOICES).get(appointment.status, appointment.status)
                mensagem = f"Nova consulta agendada para {appointment.animal.nome} em {appointment.clinic.nome} no dia {appointment.date.strftime('%d/%m/%Y às %H:%M')}. Status: {status_display}"
                enviar_notificacao(tutor.usuario, mensagem, enviar_email=True)
                
                messages.success(request, 'Consulta cadastrada com sucesso! O tutor foi notificado.')
                return redirect('veterinarios:listar_consultas')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar consulta: {str(e)}')
    else:
        form = AppointmentForm(veterinarian=veterinario)
    
    return render(request, 'veterinarios/cadastrar_consulta.html', {
        'form': form,
        'veterinario': veterinario
    })


@login_required(login_url='/login/')
def listar_consultas(request):
    """Lista todas as consultas do veterinário"""
    veterinario = get_object_or_404(Veterinario.objects.select_related('usuario'), usuario=request.user)
    consultas = Appointment.objects.filter(
        veterinarian=veterinario
    ).select_related(
        'tutor',
        'tutor__usuario',
        'animal',
        'clinic',
        'service'
    ).order_by('-date')
    
    return render(request, 'veterinarios/listar_consultas.html', {
        'consultas': consultas,
        'veterinario': veterinario
    })


@login_required(login_url='/login/')
def editar_consulta(request, consulta_id):
    """Permite editar uma consulta (principalmente status)"""
    # Busca o veterinário - o manager customizado já limita os campos
    veterinario = get_object_or_404(Veterinario.objects, usuario=request.user)
    
    consulta = get_object_or_404(
        Appointment.objects.select_related('tutor', 'tutor__usuario', 'animal', 'clinic', 'service'),
        id=consulta_id,
        veterinarian=veterinario
    )
    
    status_anterior = consulta.status
    
    if request.method == 'POST':
        form = EditarConsultaForm(request.POST, instance=consulta)
        if form.is_valid():
            try:
                consulta = form.save()
                
                # SEMPRE envia notificação para o tutor quando o status for alterado
                if consulta.status != status_anterior:
                    from veterinarios.utils import enviar_notificacao
                    status_display = dict(Appointment.STATUS_CHOICES).get(consulta.status, consulta.status)
                    status_anterior_display = dict(Appointment.STATUS_CHOICES).get(status_anterior, status_anterior)
                    mensagem = f"Status da consulta de {consulta.animal.nome} em {consulta.clinic.nome} foi alterado de '{status_anterior_display}' para '{status_display}'. Data: {consulta.date.strftime('%d/%m/%Y às %H:%M')}"
                    enviar_notificacao(consulta.tutor.usuario, mensagem, enviar_email=True)
                    messages.success(request, f'Consulta atualizada com sucesso! O tutor foi notificado sobre a mudança de status.')
                else:
                    messages.success(request, 'Consulta atualizada com sucesso!')
                
                return redirect('veterinarios:listar_consultas')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar consulta: {str(e)}')
    else:
        form = EditarConsultaForm(instance=consulta)
    
    return render(request, 'veterinarios/editar_consulta.html', {
        'form': form,
        'consulta': consulta,
        'veterinario': veterinario
    })
