from django.db import models
from django.conf import settings

class VeterinarioQuerySet(models.QuerySet):
    """QuerySet customizado que exclui o campo CPF das queries"""
    def _clone(self):
        clone = super()._clone()
        return clone

class VeterinarioManager(models.Manager):
    """Manager customizado para Veterinario que sempre usa only() com campos que existem"""
    def get_queryset(self):
        # Usa apenas os campos que sabemos que existem: id, usuario_id, crmv
        return VeterinarioQuerySet(self.model, using=self._db).only('id', 'usuario', 'crmv')
    
    def get(self, *args, **kwargs):
        # Sempre usa only() para evitar buscar campos que não existem
        return self.get_queryset().only('id', 'usuario', 'crmv').get(*args, **kwargs)
    
    def filter(self, *args, **kwargs):
        return self.get_queryset().only('id', 'usuario', 'crmv').filter(*args, **kwargs)
    
    def first(self):
        return self.get_queryset().only('id', 'usuario', 'crmv').first()

class Veterinario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='veterinario'
    )
    crmv = models.CharField(max_length=20, unique=True)
    # Campos removidos do modelo porque não existem no banco MySQL:
    # - telefone (pode não existir)
    # - especialidade (pode não existir)
    # - cpf (está no CustomUser)
    
    objects = VeterinarioManager()
    
    @property
    def cpf(self):
        """Retorna o CPF do usuário vinculado"""
        return self.usuario.cpf if hasattr(self.usuario, 'cpf') else None
    
    @property
    def telefone(self):
        """Retorna o telefone do usuário vinculado (armazenado no CustomUser)"""
        return self.usuario.telefone if hasattr(self.usuario, 'telefone') else None
    
    @property
    def especialidade(self):
        """Retorna especialidade se existir no banco, senão None"""
        # Tenta buscar do banco se a coluna existir
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT especialidade FROM veterinarios_veterinario WHERE id = %s",
                    [self.id]
                )
                row = cursor.fetchone()
                return row[0] if row and row[0] else None
        except:
            return None

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username}"
    
    class Meta:
        # Força o Django a não buscar o campo CPF
        managed = True


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
