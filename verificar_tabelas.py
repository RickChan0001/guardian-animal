"""
Script para verificar se as tabelas principais existem e têm dados
Execute: python verificar_tabelas.py
"""
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guardiao_animal.settings')

django.setup()

from django.db import connection

def verificar_tabela(tabela):
    """Verifica se uma tabela existe e quantos registros tem"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            count = cursor.fetchone()[0]
            return count
    except Exception as e:
        return f"ERRO: {e}"

def main():
    print("=" * 60)
    print("  VERIFICACAO DE TABELAS NO BANCO ONLINE")
    print("=" * 60)
    
    tabelas_principais = [
        'tutores_customuser',
        'tutores_tutor',
        'tutores_animal',
        'veterinarios_veterinario',
        'veterinarios_clinica',
    ]
    
    print("\n[INFO] Verificando tabelas principais:\n")
    
    for tabela in tabelas_principais:
        resultado = verificar_tabela(tabela)
        if isinstance(resultado, int):
            print(f"[OK] {tabela}: {resultado} registro(s)")
        else:
            print(f"[ERRO] {tabela}: {resultado}")
    
    print("\n" + "=" * 60)
    print("Verificacao concluida!")
    print("=" * 60)
    
    print("\n[INFO] Para ver os dados das tabelas, execute:")
    print("   python manage.py dbshell")
    print("\nE depois:")
    print("   SELECT * FROM tutores_customuser;")
    print("   SELECT * FROM tutores_tutor;")

if __name__ == '__main__':
    main()

