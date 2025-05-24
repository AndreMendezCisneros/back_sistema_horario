from rest_framework import serializers
from .models import Grupos, BloquesHorariosDefinicion, DisponibilidadDocentes, HorariosAsignados, ConfiguracionRestricciones
from apps.academic_setup.serializers import MateriasSerializer, CarreraSerializer, EspaciosFisicosSerializer
from apps.users.serializers import DocentesSerializer
from apps.academic_setup.models import PeriodoAcademico

class GruposSerializer(serializers.ModelSerializer):
    materia_detalle = MateriasSerializer(source='materia', read_only=True)
    carrera_detalle = CarreraSerializer(source='carrera', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo.nombre_periodo', read_only=True)
    docente_asignado_directamente_nombre = serializers.CharField(source='docente_asignado_directamente.__str__', read_only=True, allow_null=True)


    class Meta:
        model = Grupos
        fields = ['grupo_id', 'codigo_grupo', 'materia', 'materia_detalle', 'carrera', 'carrera_detalle',
                  'periodo', 'periodo_nombre', 'numero_estudiantes_estimado', 'turno_preferente',
                  'docente_asignado_directamente', 'docente_asignado_directamente_nombre']

class BloquesHorariosDefinicionSerializer(serializers.ModelSerializer):
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True, allow_null=True)
    turno_display = serializers.CharField(source='get_turno_display', read_only=True)

    class Meta:
        model = BloquesHorariosDefinicion
        fields = ['bloque_def_id', 'nombre_bloque', 'hora_inicio', 'hora_fin',
                  'turno', 'turno_display', 'dia_semana', 'dia_semana_display']

class DisponibilidadDocentesSerializer(serializers.ModelSerializer):
    docente_nombre = serializers.CharField(source='docente.__str__', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo.nombre_periodo', read_only=True)
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True)
    bloque_horario_detalle = BloquesHorariosDefinicionSerializer(source='bloque_horario', read_only=True)
    origen_carga_display = serializers.CharField(source='get_origen_carga_display', read_only=True)


    class Meta:
        model = DisponibilidadDocentes
        fields = ['disponibilidad_id', 'docente', 'docente_nombre', 'periodo', 'periodo_nombre',
                  'dia_semana', 'dia_semana_display', 'bloque_horario', 'bloque_horario_detalle',
                  'esta_disponible', 'preferencia', 'origen_carga', 'origen_carga_display']

class HorariosAsignadosSerializer(serializers.ModelSerializer):
    grupo_detalle = GruposSerializer(source='grupo', read_only=True)
    docente_detalle = DocentesSerializer(source='docente', read_only=True)
    espacio_detalle = EspaciosFisicosSerializer(source='espacio', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo.nombre_periodo', read_only=True)
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True)
    bloque_horario_detalle = BloquesHorariosDefinicionSerializer(source='bloque_horario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)


    class Meta:
        model = HorariosAsignados
        fields = ['horario_id', 'grupo', 'grupo_detalle', 'docente', 'docente_detalle',
                  'espacio', 'espacio_detalle', 'periodo', 'periodo_nombre',
                  'dia_semana', 'dia_semana_display', 'bloque_horario', 'bloque_horario_detalle',
                  'estado', 'estado_display', 'observaciones']
        # Validar unique_together en el serializador si es necesario, aunque el modelo ya lo hace.

class ConfiguracionRestriccionesSerializer(serializers.ModelSerializer):
    periodo_aplicable_nombre = serializers.CharField(source='periodo_aplicable.nombre_periodo', read_only=True, allow_null=True)
    tipo_aplicacion_display = serializers.CharField(source='get_tipo_aplicacion_display', read_only=True)

    class Meta:
        model = ConfiguracionRestricciones
        fields = ['restriccion_id', 'codigo_restriccion', 'descripcion', 'tipo_aplicacion', 'tipo_aplicacion_display',
                  'entidad_id_1', 'entidad_id_2', 'valor_parametro',
                  'periodo_aplicable', 'periodo_aplicable_nombre', 'esta_activa']
