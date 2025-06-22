# apps/academic_setup/serializers.py
from rest_framework import serializers
from .models import (
    UnidadAcademica, Carrera, PeriodoAcademico, TiposEspacio, EspaciosFisicos,
    Especialidades, Materias, CarreraMaterias, MateriaEspecialidadesRequeridas,
    TipoUnidadAcademica, Ciclo, Seccion # Importar los nuevos modelos
)

# Nuevo Serializer: TipoUnidadAcademica
class TipoUnidadAcademicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoUnidadAcademica
        fields = '__all__'

# Modificado: UnidadAcademicaSerializer
class UnidadAcademicaSerializer(serializers.ModelSerializer):
    # Campo para mostrar el nombre del tipo de unidad académica
    tipo_unidad_nombre = serializers.CharField(source='tipo_unidad.nombre_tipo', read_only=True, allow_null=True)

    class Meta:
        model = UnidadAcademica
        # Incluir nuevo campo 'tipo_unidad' y 'tipo_unidad_nombre'
        fields = ['unidad_id', 'nombre_unidad', 'descripcion', 'tipo_unidad', 'tipo_unidad_nombre']

class CarreraSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(source='unidad.nombre_unidad', read_only=True)
    class Meta:
        model = Carrera
        fields = ['carrera_id', 'nombre_carrera', 'codigo_carrera', 'horas_totales_curricula', 'unidad', 'unidad_nombre']

class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoAcademico
        fields = '__all__'

class TiposEspacioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TiposEspacio
        fields = '__all__'

class EspaciosFisicosSerializer(serializers.ModelSerializer):
    tipo_espacio_nombre = serializers.CharField(source='tipo_espacio.nombre_tipo_espacio', read_only=True)
    unidad_nombre = serializers.CharField(source='unidad.nombre_unidad', read_only=True, allow_null=True)
    class Meta:
        model = EspaciosFisicos
        fields = ['espacio_id', 'nombre_espacio', 'tipo_espacio', 'tipo_espacio_nombre', 'capacidad', 'ubicacion', 'recursos_adicionales', 'unidad', 'unidad_nombre']

class EspecialidadesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidades
        fields = '__all__'

class MateriasSerializer(serializers.ModelSerializer):
    requiere_tipo_espacio_nombre = serializers.CharField(source='requiere_tipo_espacio_especifico.nombre_tipo_espacio', read_only=True, allow_null=True)
    horas_totales = serializers.ReadOnlyField()
    # Ahora 'carreras' es una lista de IDs y ya no es write_only para poder mostrarlo si es necesario
    carreras = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    ciclo_id = serializers.IntegerField(write_only=True, required=False, help_text="ID del ciclo al que pertenece la materia en esta carrera.")

    
    class Meta:
        model = Materias
        fields = ['materia_id', 'codigo_materia', 'nombre_materia', 'descripcion',
                  'horas_academicas_teoricas', 'horas_academicas_practicas', 'horas_academicas_laboratorio', 'horas_totales',
                  'requiere_tipo_espacio_especifico', 'requiere_tipo_espacio_nombre', 'estado',
                  'carreras', 'ciclo_id'] # Cambiado a 'carreras'

    def create(self, validated_data):
        carreras_ids = validated_data.pop('carreras', [])
        ciclo_id = validated_data.pop('ciclo_id', None)
        
        # Crear la materia
        materia = Materias.objects.create(**validated_data)
        
        # Si se proveyó una lista de carreras, crear las asociaciones
        if carreras_ids:
            ciclo = None
            # La lógica del ciclo solo aplica si se eligió UNA SOLA carrera
            if len(carreras_ids) == 1 and ciclo_id:
                try:
                    ciclo = Ciclo.objects.get(pk=ciclo_id, carrera_id=carreras_ids[0])
                except Ciclo.DoesNotExist:
                    pass # El ciclo no existe o no pertenece a esa carrera, se ignora

            for carrera_id in carreras_ids:
                try:
                    carrera = Carrera.objects.get(pk=carrera_id)
                    # El ciclo solo se asigna si es aplicable (caso de una sola carrera)
                    ciclo_para_asignar = ciclo if len(carreras_ids) == 1 else None
                    CarreraMaterias.objects.create(
                        carrera=carrera, 
                        materia=materia,
                        ciclo=ciclo_para_asignar
                    )
                except Carrera.DoesNotExist:
                    # Ignorar si una de las carreras de la lista no existe
                    continue

        return materia

# Nuevo Serializer: Ciclo
class CicloSerializer(serializers.ModelSerializer):
    carrera_nombre = serializers.CharField(source='carrera.nombre_carrera', read_only=True)
    # Si quieres ver las secciones anidadas al obtener un ciclo, descomenta la siguiente línea
    # secciones = SeccionSerializer(many=True, read_only=True) # Ojo: SeccionSerializer debe estar definido antes

    class Meta:
        model = Ciclo
        fields = ['ciclo_id', 'nombre_ciclo', 'orden', 'carrera', 'carrera_nombre']

# Nuevo Serializer: Seccion
class SeccionSerializer(serializers.ModelSerializer):
    ciclo_nombre = serializers.CharField(source='ciclo.nombre_ciclo', read_only=True)
    carrera_nombre = serializers.CharField(source='ciclo.carrera.nombre_carrera', read_only=True) # Acceso a través del ciclo

    class Meta:
        model = Seccion
        fields = ['seccion_id', 'nombre_seccion', 'capacidad', 'ciclo', 'ciclo_nombre', 'carrera_nombre']

# Modificado: CarreraMateriasSerializer (si ajustaste el modelo CarreraMaterias)
class CarreraMateriasSerializer(serializers.ModelSerializer):
    carrera_nombre = serializers.CharField(source='carrera.nombre_carrera', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre_materia', read_only=True)
    materia_codigo = serializers.CharField(source='materia.codigo_materia', read_only=True)
    # Nuevo campo si CarreraMaterias ahora tiene un FK a Ciclo
    ciclo_nombre = serializers.CharField(source='ciclo.nombre_ciclo', read_only=True, allow_null=True)

    class Meta:
        model = CarreraMaterias
        # Añadir 'ciclo' y 'ciclo_nombre' a los fields
        fields = ['id', 'carrera', 'carrera_nombre', 'materia', 'materia_nombre', 'materia_codigo', 'ciclo_sugerido', 'ciclo', 'ciclo_nombre']


class MateriaEspecialidadesRequeridasSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre_materia', read_only=True)
    especialidad_nombre = serializers.CharField(source='especialidad.nombre_especialidad', read_only=True)
    class Meta:
        model = MateriaEspecialidadesRequeridas
        fields = ['id', 'materia', 'materia_nombre', 'especialidad', 'especialidad_nombre']