# veterinarios/utils.py
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification


def enviar_notificacao(user, mensagem, enviar_email=True):
    """
    Cria uma notificação para o usuário e opcionalmente envia por email
    
    Args:
        user: Usuário que receberá a notificação
        mensagem: Mensagem da notificação
        enviar_email: Se True, envia email também
    """
    # Cria a notificação no banco
    notificacao = Notification.objects.create(
        user=user,
        message=mensagem,
        is_read=False
    )
    
    # Envia email se solicitado e se o usuário tem email
    if enviar_email and user.email:
        try:
            send_mail(
                subject='Notificação - Guardião Animal',
                message=mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@guardiaoanimal.com',
                recipient_list=[user.email],
                fail_silently=True,  # Não levanta exceção se falhar
            )
        except Exception as e:
            # Se falhar ao enviar email, apenas registra mas não impede a criação da notificação
            print(f"Erro ao enviar email: {e}")
    
    return notificacao

