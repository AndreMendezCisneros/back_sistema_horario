
from rest_framework import serializers
from .models import UnidadAcademica, Carrera, PeriodoAcademico, TiposEspacio, EspaciosFisicos, Especialidades, Materias, CarreraMaterias, MateriaEspecialidadesRequeridas

class UnidadAcademicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadAcademica
        fields = '__all__'

class CarreraSerializer(serializers.ModelSerializer):
    #Creamos un campo para mostrar el nombre de la unidad academica esto se cre en el JSON
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
    class Meta:
        model = Materias
        fields = ['materia_id', 'codigo_materia', 'nombre_materia', 'descripcion',
                  'horas_academicas_teoricas', 'horas_academicas_practicas', 'horas_academicas_laboratorio', 'horas_totales',
                  'requiere_tipo_espacio_especifico', 'requiere_tipo_espacio_nombre', 'estado']

class CarreraMateriasSerializer(serializers.ModelSerializer):
    carrera_nombre = serializers.CharField(source='carrera.nombre_carrera', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre_materia', read_only=True)
    materia_codigo = serializers.CharField(source='materia.codigo_materia', read_only=True)

    class Meta:
        model = CarreraMaterias
        fields = ['id', 'carrera', 'carrera_nombre', 'materia', 'materia_nombre', 'materia_codigo', 'ciclo_sugerido']


class MateriaEspecialidadesRequeridasSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre_materia', read_only=True)
    especialidad_nombre = serializers.CharField(source='especialidad.nombre_especialidad', read_only=True)
    class Meta:
        model = MateriaEspecialidadesRequeridas
        fields = ['id', 'materia', 'materia_nombre', 'especialidad', 'especialidad_nombre']

# ... (Crea serializers similares para las otras apps y modelos)
