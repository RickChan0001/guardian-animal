from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from PIL import Image
import os

# Usuário personalizado
class CustomUser(AbstractUser):
    telefone = models.CharField(max_length=15, blank=True, null=True)
    cpf = models.CharField(max_length=14, blank=True, null=True)

    def __str__(self):
        return self.username


# Tutor
class Tutor(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tutor'
    )
    telefone = models.CharField(max_length=15, blank=True, null=True)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    localizacao_placeholder = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Tutor: {self.usuario.get_full_name() or self.usuario.username}"


# Animal
class Animal(models.Model):

    # Espécies fixas
    ESPECIE_CHOICES = [
        ("cachorro", "Cachorro"),
        ("gato", "Gato"),
        ("passaro", "Pássaro"),
        ("outro", "Outro"),
    ]

    # Dicionário de raças
    RACAS = {
        "cachorro": [
            ("labrador", "Labrador"),
            ("poodle", "Poodle"),
            ("bulldog", "Bulldog"),
            ("vira_lata", "Vira-lata"),
        ],
        "gato": [
            ("persa", "Persa"),
            ("siames", "Siamês"),
            ("maine_coon", "Maine Coon"),
            ("vira_lata", "Vira-lata"),
        ],
        "passaro": [
            ("canario", "Canário"),
            ("calopsita", "Calopsita"),
            ("periquito", "Periquito"),
        ],
        "outro": [
            ("outro", "Outro"),
        ]
    }

    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='animais')

    nome = models.CharField(max_length=100)
    especie = models.CharField(max_length=50, choices=ESPECIE_CHOICES)
    raca = models.CharField(max_length=50, blank=True)  # Não colocamos choices aqui

    idade = models.IntegerField(blank=True, null=True)
    altura = models.CharField(max_length=50, blank=True, null=True)
    peso = models.CharField(max_length=50, blank=True, null=True)
    microchip = models.CharField(max_length=50, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)

    foto = models.ImageField(
        upload_to='animais/',
        blank=True,
        null=True,
        default='animais/default_animal.jpg'
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.foto:
            try:
                # Verifica se o arquivo existe antes de processar
                if hasattr(self.foto, 'path') and os.path.exists(self.foto.path):
                    img = Image.open(self.foto.path)
                    img.thumbnail((300, 300))
                    img.save(self.foto.path, quality=85)
            except Exception as e:
                # Se houver erro no processamento, apenas ignora mas não impede o salvamento
                pass

    def __str__(self):
        return f"{self.nome} ({self.especie})"


# Histórico do animal
class PetHistory(models.Model):
    animal = models.ForeignKey(
        Animal,
        on_delete=models.CASCADE,
        related_name='history'
    )
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    veterinarian = models.ForeignKey(
        'veterinarios.Veterinario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Histórico: {self.animal.nome} - {self.date}"
