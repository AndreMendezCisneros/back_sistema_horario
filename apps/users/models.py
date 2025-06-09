#apps/users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser # Para un modelo de Usuario personalizado si es necesario
from apps.academic_setup.models import UnidadAcademica, Especialidades

# Si quieres un modelo de Usuario personalizado:
# class Usuario(AbstractUser):
#     # Añade campos adicionales aquí si es necesario
#     # email = models.EmailField(unique=True) # Ya está en AbstractUser pero podrías querer forzarlo
#     # rol = models.ForeignKey('Roles', ...) # Si no usas los grupos de Django
#     pass

class Roles(models.Model): # Puedes usar los Grupos de Django o un modelo simple de Roles
    rol_id = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=50, unique=True) # Administrador, Coordinador Académico, Docente

    def __str__(self):
        return self.nombre_rol

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"


# Docentes
class Docentes(models.Model):
    docente_id = models.AutoField(primary_key=True)
    # Relación uno a uno con el sistema de usuarios de Django (o tu modelo Usuario personalizado)
    usuario = models.OneToOneField(
        'auth.User', # O 'users.Usuario' si usas modelo personalizado
        on_delete=models.SET_NULL, # O CASCADE si al borrar el usuario se borra el docente
        null=True, blank=True, # Permite crear docentes sin usuario asociado inicialmente
        related_name='perfil_docente'
    )
    codigo_docente = models.CharField(max_length=50, unique=True, blank=True, null=True)
    nombres = models.CharField(max_length=100) # Puede tomarse del modelo User si hay enlace
    apellidos = models.CharField(max_length=100) # Puede tomarse del modelo User si hay enlace
    dni = models.CharField(max_length=15, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True) # Puede tomarse del modelo User
    telefono = models.CharField(max_length=30, blank=True, null=True)
    tipo_contrato = models.CharField(max_length=50, blank=True, null=True)
    max_horas_semanales = models.IntegerField(blank=True, null=True)
    unidad_principal = models.ForeignKey(UnidadAcademica, on_delete=models.SET_NULL, null=True, blank=True, related_name='docentes')
    especialidades = models.ManyToManyField(Especialidades, through='DocenteEspecialidades', blank=True)


    def __str__(self):
        if self.usuario:
            return f"{self.usuario.get_full_name()} ({self.codigo_docente or 'Sin código'})"
        return f"{self.nombres} {self.apellidos} ({self.codigo_docente or 'Sin código'})"

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"


class DocenteEspecialidades(models.Model):
    docente = models.ForeignKey(Docentes, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidades, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('docente', 'especialidad')
        verbose_name = "Especialidad de Docente"
        verbose_name_plural = "Especialidades de Docentes"

# SesionesUsuario - Opcional si usas SimpleJWT y su blacklist, pero útil para auditoría o control más fino
class SesionesUsuario(models.Model):
    sesion_id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='sesiones_activas')
    token = models.CharField(max_length=500, unique=True) # Podría ser el JTI de un JWT
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Sesión de {self.usuario.username} - Expira: {self.fecha_expiracion}"

    class Meta:
        verbose_name = "Sesión de Usuario"
        verbose_name_plural = "Sesiones de Usuarios"