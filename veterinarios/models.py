from django.db import models
from django.conf import settings

class Veterinario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='veterinario'
    )
    crmv = models.CharField(max_length=20, unique=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    especialidade = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username}"


class Clinica(models.Model):
    veterinario = models.ForeignKey(
        Veterinario,
        on_delete=models.CASCADE,
        related_name='clinicas',
        null=True,
        blank=True
    )
    nome = models.CharField(max_length=100, unique=True, default='Clínica Padrão')
    cnpj = models.CharField(max_length=18, unique=True, blank=True, null=True)
    rua = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    foto = models.ImageField(upload_to='clinicas/', blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    def __str__(self):
        return self.nome


class Service(models.Model):
    clinic = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.clinic.nome}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('confirmed', 'Confirmado'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado'),
    ]

    tutor = models.ForeignKey('tutores.Tutor', on_delete=models.CASCADE)
    veterinarian = models.ForeignKey(Veterinario, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinica, on_delete=models.CASCADE)
    animal = models.ForeignKey('tutores.Animal', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Consulta de {self.animal.nome} - {self.date}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificação para {self.user.username}"


class Rating(models.Model):
    clinic = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='ratings')
    tutor = models.ForeignKey('tutores.Tutor', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Avaliação {self.rating}⭐ - {self.clinic.nome}"


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"De {self.sender.username} para {self.receiver.username}"
