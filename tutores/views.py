from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from .forms import CadastroTutorForm, CadastroAnimalForm, EditarPerfilTutorForm
from .models import Tutor, Animal

def home(request):
    # Logout any existing user when accessing home page
    if request.user.is_authenticated:
        logout(request)
    return render(request, 'home.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not username or not password:
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'login.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.first_name or user.username}!')
            # redireciona conforme tipo de conta
            if hasattr(user, 'tutor'):
                return redirect('tutores:painel_tutor')
            elif hasattr(user, 'veterinario'):
                return redirect('veterinarios:painel_veterinario')
            else:
                return redirect('home')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Você saiu com sucesso.')
    return redirect('home')

def cadastro_tutor(request):
    if request.method == 'POST':
        form = CadastroTutorForm(request.POST)
        if form.is_valid():
            try:
                # Usa transação atômica para garantir consistência no banco online
                with transaction.atomic():
                    # Cria o usuário primeiro
                    user = form.save()
                    
                    # Verifica se já existe um tutor para este usuário (proteção contra duplicatas)
                    if Tutor.objects.filter(usuario=user).exists():
                        messages.error(request, 'Este usuário já possui um perfil de tutor.')
                        user.delete()  # Remove o usuário criado se já existe tutor
                        return render(request, 'tutores/cadastro_tutor.html', {'form': form})
                    
                    # Verifica se o CPF já existe (se foi fornecido)
                    cpf = form.cleaned_data.get('cpf', '').strip()
                    if cpf:
                        # Remove caracteres não numéricos do CPF para comparação
                        cpf_limpo = ''.join(filter(str.isdigit, cpf))
                        if Tutor.objects.filter(cpf=cpf_limpo).exists():
                            messages.error(request, 'Este CPF já está cadastrado.')
                            user.delete()  # Remove o usuário criado se CPF duplicado
                            return render(request, 'tutores/cadastro_tutor.html', {'form': form})
                        cpf = cpf_limpo
                    
                    # Cria o perfil de tutor vinculado ao usuário
                    Tutor.objects.create(
                        usuario=user,
                        cpf=cpf if cpf else None,
                        telefone=form.cleaned_data.get('telefone', '').strip() or None
                    )
                    
                    # Faz login do usuário
                    login(request, user)
                    messages.success(request, 'Cadastro realizado com sucesso!')
                    return redirect('tutores:painel_tutor')
                    
            except Exception as e:
                # Tratamento de erros específicos para banco online
                error_msg = str(e)
                if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                    messages.error(request, 'Erro: Este CPF ou usuário já está cadastrado no sistema.')
                elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
                    messages.error(request, 'Erro de conexão com o banco de dados. Tente novamente.')
                else:
                    messages.error(request, f'Erro ao cadastrar tutor: {error_msg}')
                return render(request, 'tutores/cadastro_tutor.html', {'form': form})
        # Se o formulário for inválido, os erros serão exibidos automaticamente no template
    else:
        form = CadastroTutorForm()
    return render(request, 'tutores/cadastro_tutor.html', {'form': form})

@login_required(login_url='/login/')
def painel_tutor(request):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    animais = tutor_perfil.animais.all().order_by('nome')
    return render(request, 'tutores/painel_tutor.html', {
        'tutor_perfil': tutor_perfil,
        'animais': animais
    })

@login_required(login_url='/login/')
def cadastro_animal(request):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    if request.method == 'POST':
        form = CadastroAnimalForm(request.POST, request.FILES)
        if form.is_valid():
            animal = form.save(commit=False)
            animal.tutor = tutor_perfil
            animal.save()
            messages.success(request, 'Animal cadastrado com sucesso!')
            # Após cadastro, redirecionar para painel onde as informações aparecem
            return redirect('tutores:painel_tutor')
    else:
        form = CadastroAnimalForm()
    return render(request, 'tutores/cadastro_animal.html', {'form': form})

@login_required(login_url='/login/')
def editar_animal(request, animal_id):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    animal = get_object_or_404(Animal, id=animal_id, tutor=tutor_perfil)
    if request.method == 'POST':
        form = CadastroAnimalForm(request.POST, request.FILES, instance=animal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Animal atualizado com sucesso!')
            return redirect('tutores:painel_tutor')
    else:
        form = CadastroAnimalForm(instance=animal)
    return render(request, 'tutores/editar_animal.html', {'form': form, 'animal': animal})

@login_required(login_url='/login/')
def editar_perfil(request):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    if request.method == 'POST':
        form = EditarPerfilTutorForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                # Usa transação atômica para garantir consistência no banco online
                with transaction.atomic():
                    # Atualiza os dados do usuário
                    form.save()

                    # Atualiza os dados do perfil de tutor usando os dados limpos do formulário
                    cpf = form.cleaned_data.get('cpf')
                    telefone = form.cleaned_data.get('telefone')
                    localizacao_placeholder = form.cleaned_data.get('localizacao_placeholder', '').strip() or None

                    # Verifica se o CPF já existe em outro tutor
                    if cpf and Tutor.objects.filter(cpf=cpf).exclude(usuario=request.user).exists():
                        messages.error(request, 'Este CPF já está cadastrado para outro tutor.')
                        return render(request, 'tutores/editar_perfil.html', {
                            'form': form,
                            'tutor_perfil': tutor_perfil
                        })

                    tutor_perfil.telefone = telefone
                    tutor_perfil.cpf = cpf
                    tutor_perfil.localizacao_placeholder = localizacao_placeholder
                    tutor_perfil.save()

                    messages.success(request, 'Perfil atualizado com sucesso!')
                    return redirect('tutores:perfil_tutor')
            except Exception as e:
                error_msg = str(e)
                if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                    messages.error(request, 'Erro: Este CPF já está cadastrado no sistema.')
                elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
                    messages.error(request, 'Erro de conexão com o banco de dados. Tente novamente.')
                else:
                    messages.error(request, f'Erro ao atualizar perfil: {error_msg}')
    else:
        # Preenche o formulário com os dados atuais do tutor
        initial_data = {
            'telefone': tutor_perfil.telefone,
            'cpf': tutor_perfil.cpf,
            'localizacao_placeholder': tutor_perfil.localizacao_placeholder,
        }
        form = EditarPerfilTutorForm(instance=request.user, initial=initial_data)
    return render(request, 'tutores/editar_perfil.html', {
        'form': form,
        'tutor_perfil': tutor_perfil
    })

@login_required(login_url='/login/')
def perfil_tutor(request):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    return render(request, 'tutores/perfil_tutor.html', {
        'tutor_perfil': tutor_perfil
    })

@login_required(login_url='/login/')
def animal_profile(request, animal_id):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    animal = get_object_or_404(Animal, id=animal_id, tutor=tutor_perfil)
    history = animal.history.all().order_by('-date')
    return render(request, 'tutores/animal_profile.html', {
        'animal': animal,
        'history': history
    })

@login_required(login_url='/login/')
def deletar_animal(request, animal_id):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    animal = get_object_or_404(Animal, id=animal_id, tutor=tutor_perfil)
    if request.method == 'POST':
        animal.delete()
        messages.success(request, 'Animal deletado com sucesso!')
        return redirect('tutores:painel_tutor')
    return render(request, 'tutores/deletar_animal.html', {'animal': animal})

@login_required(login_url='/login/')
def add_pet_history(request, animal_id):
    tutor_perfil = get_object_or_404(Tutor, usuario=request.user)
    animal = get_object_or_404(Animal, id=animal_id, tutor=tutor_perfil)
    if request.method == 'POST':
        form = PetHistoryForm(request.POST)
        if form.is_valid():
            history = form.save(commit=False)
            history.animal = animal
            history.save()
            messages.success(request, 'Histórico adicionado com sucesso!')
            return redirect('tutores:animal_profile', animal_id=animal.id)
    else:
        form = PetHistoryForm()
    return render(request, 'tutores/add_pet_history.html', {'form': form, 'animal': animal})
