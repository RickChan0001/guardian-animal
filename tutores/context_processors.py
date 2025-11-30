# tutores/context_processors.py
from .models import Tutor


def user_is_tutor(request):
    """Adiciona informação se o usuário é tutor ao contexto"""
    is_tutor = False
    if request.user.is_authenticated:
        try:
            # Usa o manager customizado que só busca campos existentes
            is_tutor = Tutor.objects.filter(usuario=request.user).exists()
        except:
            is_tutor = False
    
    return {'user_is_tutor': is_tutor}

