# veterinarios/context_processors.py
from .models import Notification


def notificacoes_nao_lidas(request):
    """Adiciona a contagem de notificações não lidas ao contexto"""
    if request.user.is_authenticated:
        try:
            nao_lidas = Notification.objects.filter(user=request.user, is_read=False).count()
        except:
            nao_lidas = 0
    else:
        nao_lidas = 0
    
    return {'notificacoes_nao_lidas': nao_lidas}

