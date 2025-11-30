from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro_tutor, name='cadastro_tutor'),
    path('painel/', views.painel_tutor, name='painel_tutor'),
    path('cadastro_animal/', views.cadastro_animal, name='cadastro_animal'),
    path('editar_animal/<int:animal_id>/', views.editar_animal, name='editar_animal'),
    path('deletar_animal/<int:animal_id>/', views.deletar_animal, name='deletar_animal'),
    path('editar_perfil/', views.editar_perfil, name='editar_perfil'),
    path('perfil/', views.perfil_tutor, name='perfil_tutor'),
    path('animal/<int:animal_id>/', views.animal_profile, name='animal_profile'),
    path('animal/<int:animal_id>/add_history/', views.add_pet_history, name='add_pet_history'),
    path('buscar_veterinario/', views.buscar_veterinario, name='buscar_veterinario'),
    path('veterinario/<int:veterinario_id>/', views.perfil_publico_veterinario, name='perfil_publico_veterinario'),
    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path('notificacao/<int:notificacao_id>/marcar_lida/', views.marcar_notificacao_lida, name='marcar_notificacao_lida'),
    path('api/animais/', views.api_animais_por_tutor, name='api_animais_por_tutor'),
]
