#!/usr/bin/env python
"""
Script para verificar datos en la base de datos
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'la_pontificia_horarios.settings')
django.setup()

from apps.academic_setup.models import UnidadAcademica, Carrera, PeriodoAcademico, Materias
from apps.scheduling.models import Grupos, BloquesHorariosDefinicion
from apps.users.models import Docentes

def check_data():
    print("=== VERIFICACIÓN DE DATOS EN LA BASE DE DATOS ===")
    
    # Verificar Unidades Académicas
    unidades = UnidadAcademica.objects.all()
    print(f"Unidades Académicas: {unidades.count()}")
    for unidad in unidades[:5]:  # Mostrar solo las primeras 5
        print(f"  - {unidad.unidad_id}: {unidad.nombre_unidad}")
    
    # Verificar Carreras
    carreras = Carrera.objects.all()
    print(f"\nCarreras: {carreras.count()}")
    for carrera in carreras[:5]:
        print(f"  - {carrera.carrera_id}: {carrera.nombre_carrera} (Unidad: {carrera.unidad.nombre_unidad})")
    
    # Verificar Períodos Académicos
    periodos = PeriodoAcademico.objects.all()
    print(f"\nPeríodos Académicos: {periodos.count()}")
    for periodo in periodos:
        print(f"  - {periodo.periodo_id}: {periodo.nombre_periodo} (Activo: {periodo.activo})")
    
    # Verificar Materias
    materias = Materias.objects.all()
    print(f"\nMaterias: {materias.count()}")
    for materia in materias[:5]:
        print(f"  - {materia.materia_id}: {materia.nombre_materia}")
    
    # Verificar Grupos
    grupos = Grupos.objects.all()
    print(f"\nGrupos: {grupos.count()}")
    for grupo in grupos[:5]:
        print(f"  - {grupo.grupo_id}: {grupo.codigo_grupo} (Carrera: {grupo.carrera.nombre_carrera}, Período: {grupo.periodo.nombre_periodo})")
    
    # Verificar Bloques Horarios
    bloques = BloquesHorariosDefinicion.objects.all()
    print(f"\nBloques Horarios: {bloques.count()}")
    for bloque in bloques[:5]:
        print(f"  - {bloque.bloque_def_id}: {bloque.hora_inicio} - {bloque.hora_fin}")
    
    # Verificar Docentes
    docentes = Docentes.objects.all()
    print(f"\nDocentes: {docentes.count()}")
    for docente in docentes[:5]:
        print(f"  - {docente.docente_id}: {docente.nombres} {docente.apellidos}")

if __name__ == "__main__":
    check_data() 