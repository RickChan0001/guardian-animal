from django.contrib import admin
from .models import Veterinario, Clinica, Service, Appointment, Notification, Rating, Message

@admin.register(Veterinario)
class VeterinarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'crmv', 'telefone', 'get_cpf', 'especialidade')
    search_fields = ('usuario__username', 'usuario__first_name', 'crmv', 'usuario__cpf')
    
    def get_cpf(self, obj):
        """Retorna o CPF do usuário vinculado"""
        return obj.usuario.cpf if hasattr(obj.usuario, 'cpf') else '-'
    get_cpf.short_description = 'CPF'

@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'veterinario', 'telefone')
    search_fields = ('nome', 'cnpj', 'veterinario__usuario__username')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'clinic', 'price')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('animal', 'clinic', 'veterinarian', 'date', 'status')
    list_filter = ('status',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at', 'is_read')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    pass

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message', 'timestamp', 'is_read')
    search_fields = ('sender__username', 'receiver__username', 'message')
    list_filter = ('is_read', 'timestamp')

