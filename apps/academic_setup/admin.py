# apps/academic_setup/admin.py
from django.contrib import admin
from .models import (
    TipoUnidadAcademica, UnidadAcademica, Carrera, Ciclo, Seccion,
    PeriodoAcademico, TiposEspacio, EspaciosFisicos, Especialidades,
    Materias, CarreraMaterias,  MateriaEspecialidadesRequeridas
)

# Registra tus modelos aquí
admin.site.register(TipoUnidadAcademica)
admin.site.register(UnidadAcademica)
admin.site.register(Carrera)
admin.site.register(Ciclo)
admin.site.register(Seccion)
admin.site.register(PeriodoAcademico)
admin.site.register(TiposEspacio)
admin.site.register(EspaciosFisicos)
admin.site.register(Especialidades)
admin.site.register(Materias)
admin.site.register(CarreraMaterias)
admin.site.register(MateriaEspecialidadesRequeridas)

# Opcional: Para una mejor visualización en el admin (ejemplo para UnidadAcademica)
# class UnidadAcademicaAdmin(admin.ModelAdmin):
#     list_display = ('nombre_unidad', 'tipo_unidad', 'descripcion')
#     search_fields = ('nombre_unidad',)
# admin.site.register(UnidadAcademica, UnidadAcademicaAdmin)