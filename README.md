# Guardião Animal - Sistema de Gestão para Tutores e Veterinários

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## 🚀 Como Executar o Projeto

### 1. Instalar as Dependências

Primeiro, instale todas as dependências necessárias:

```bash
pip install -r requirements.txt
```

**Nota:** É recomendado usar um ambiente virtual. Para criar e ativar:

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar no Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Ativar no Windows (CMD)
venv\Scripts\activate.bat

# Depois instalar as dependências
pip install -r requirements.txt
```

### 2. Configurar o Banco de Dados

O projeto está configurado para usar **SQLite por padrão** (não precisa de configuração adicional).

Se quiser usar PostgreSQL ou MySQL, crie um arquivo `.env` na raiz do projeto com:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=nome_do_banco
DB_USER=usuario
DB_PASSWORD=senha
DB_HOST=localhost
DB_PORT=5432
```

### 3. Executar as Migrações

Crie as tabelas no banco de dados:

```bash
python manage.py migrate
```

### 4. Criar um Superusuário (Opcional)

Para acessar o painel administrativo do Django:

```bash
python manage.py createsuperuser
```

### 5. Coletar Arquivos Estáticos

```bash
python manage.py collectstatic --noinput
```

### 6. Iniciar o Servidor

```bash
python manage.py runserver
```

O servidor estará rodando em: **http://127.0.0.1:8000/**

## 📝 Comandos Úteis

- **Criar migrações:** `python manage.py makemigrations`
- **Aplicar migrações:** `python manage.py migrate`
- **Acessar shell do Django:** `python manage.py shell`
- **Criar superusuário:** `python manage.py createsuperuser`
- **Rodar testes:** `python manage.py test`

## 🔧 Estrutura do Projeto

- `tutores/` - App para gestão de tutores e animais
- `veterinarios/` - App para gestão de veterinários e clínicas
- `guardiao_animal/` - Configurações principais do Django
- `templates/` - Templates HTML compartilhados
- `static/` - Arquivos estáticos (CSS, JS, imagens)
- `media/` - Arquivos de upload (fotos de animais, etc.)

## 🌐 URLs Principais

- `/` - Página inicial
- `/login/` - Página de login
- `/tutores/painel/` - Painel do tutor (após login)
- `/veterinarios/painel/` - Painel do veterinário (após login)
- `/admin/` - Painel administrativo do Django

