#apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Roles, Docentes, DocenteEspecialidades, SesionesUsuario

# Inline para mostrar el perfil de Docente dentro del formulario de Usuario
class DocenteInline(admin.StackedInline):
    model = Docentes
    can_delete = False
    verbose_name_plural = 'Perfil de Docente'
    fk_name = 'usuario'
    # Campos a mostrar en el inline
    fields = ('codigo_docente', 'dni', 'telefono', 'tipo_contrato', 'max_horas_semanales', 'unidad_principal')

# Definir un nuevo UserAdmin
class UserAdmin(BaseUserAdmin):
    inlines = (DocenteInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_docente_codigo')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    @admin.display(description='Código Docente')
    def get_docente_codigo(self, obj):
        if hasattr(obj, 'perfil_docente'):
            return obj.perfil_docente.codigo_docente
        return "N/A"

# Re-registrar UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Admin para el modelo Roles
@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ('rol_id', 'nombre_rol')
    search_fields = ('nombre_rol',)

# Inline para las especialidades del docente
class DocenteEspecialidadesInline(admin.TabularInline):
    model = DocenteEspecialidades
    extra = 1 # Cuántos campos de especialidad mostrar por defecto

# Admin para el modelo Docentes
@admin.register(Docentes)
class DocentesAdmin(admin.ModelAdmin):
    list_display = ('docente_id', 'nombres', 'apellidos', 'codigo_docente', 'email', 'tipo_contrato', 'unidad_principal')
    search_fields = ('nombres', 'apellidos', 'codigo_docente', 'dni', 'email')
    list_filter = ('tipo_contrato', 'unidad_principal')
    inlines = [DocenteEspecialidadesInline]
    # Si un docente no está enlazado a un usuario, no se mostrará en el admin de User
    # Este admin es útil para gestionar docentes que no son usuarios del sistema.
    raw_id_fields = ('usuario',) # Mejora la interfaz para seleccionar usuarios

# Admin para el modelo SesionesUsuario
@admin.register(SesionesUsuario)
class SesionesUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_creacion', 'fecha_expiracion', 'ip_address')
    search_fields = ('usuario__username', 'ip_address')
    list_filter = ('fecha_creacion', 'fecha_expiracion')
    readonly_fields = ('usuario', 'token', 'fecha_creacion', 'fecha_expiracion', 'ip_address', 'user_agent')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
