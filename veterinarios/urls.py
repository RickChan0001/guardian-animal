# veterinarios/urls.py
from django.urls import path
from . import views

app_name = 'veterinarios'

urlpatterns = [
    path('cadastro/', views.cadastro_veterinario, name='cadastro_veterinario'),
    path('painel/', views.painel_veterinario, name='painel_veterinario'),
    path('cadastro_clinica/', views.cadastro_clinica, name='cadastro_clinica'),
    path('editar_clinica/<int:clinica_id>/', views.editar_clinica, name='editar_clinica'),
    path('delete_clinica/<int:clinica_id>/', views.delete_clinica, name='delete_clinica'),
    path('perfil/', views.perfil_veterinario, name='perfil_veterinario'),
    path('editar_perfil/', views.editar_perfil_veterinario, name='editar_perfil_veterinario'),
    path('notificacoes/', views.notificacoes_veterinario, name='notificacoes_veterinario'),
    path('notificacao/<int:notificacao_id>/marcar_lida/', views.marcar_notificacao_lida_veterinario, name='marcar_notificacao_lida_veterinario'),
    path('cadastrar_consulta/', views.cadastrar_consulta, name='cadastrar_consulta'),
    path('consultas/', views.listar_consultas, name='listar_consultas'),
    path('editar_consulta/<int:consulta_id>/', views.editar_consulta, name='editar_consulta'),
]
