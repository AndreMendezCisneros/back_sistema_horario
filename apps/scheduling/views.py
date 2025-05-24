from django.db import models # <--- AÑADE O ASEGÚRATE QUE ESTA LÍNEA EXISTA

from rest_framework import viewsets, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend # Para filtrado avanzado
from .models import Grupos, BloquesHorariosDefinicion, DisponibilidadDocentes, HorariosAsignados, ConfiguracionRestricciones
from .tasks import generar_horarios_task # Importar la tarea Celery

# Importar el servicio
from .service.schedule_generator import ScheduleGeneratorService # Asegúrate que la ruta sea correcta (service o services)
import logging
logger = logging.getLogger(__name__)

from .serializers import (
    GruposSerializer, BloquesHorariosDefinicionSerializer, DisponibilidadDocentesSerializer,
    HorariosAsignadosSerializer, ConfiguracionRestriccionesSerializer
)
# Importar servicios
from .service.schedule_generator import ScheduleGeneratorService
from .service.conflict_validator import ConflictValidatorService
from apps.academic_setup.models import PeriodoAcademico # Para la acción de generar

class GruposViewSet(viewsets.ModelViewSet):
    queryset = Grupos.objects.select_related('materia', 'carrera', 'periodo', 'docente_asignado_directamente').all()
    serializer_class = GruposSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['periodo', 'carrera', 'materia', 'turno_preferente'] # Campos para filtrar por query params


class BloquesHorariosDefinicionViewSet(viewsets.ModelViewSet):
    queryset = BloquesHorariosDefinicion.objects.all()
    serializer_class = BloquesHorariosDefinicionSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['turno', 'dia_semana']

class DisponibilidadDocentesViewSet(viewsets.ModelViewSet):
    queryset = DisponibilidadDocentes.objects.select_related('docente', 'periodo', 'bloque_horario').all()
    serializer_class = DisponibilidadDocentesSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['docente', 'periodo', 'dia_semana', 'esta_disponible']

    # RU15: Permitir subir horarios disponibles de docentes en formato Excel
    @action(detail=False, methods=['post'], url_path='cargar-disponibilidad-excel')
    def cargar_disponibilidad_excel(self, request):
        # Aquí iría la lógica para procesar el archivo Excel
        # Validar archivo, leer datos, crear o actualizar registros de DisponibilidadDocentes
        # Ejemplo:
        # file_obj = request.FILES.get('file')
        # if not file_obj:
        #     return Response({"error": "No se proporcionó ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)
        # try:
        #     # Lógica de procesamiento de Excel (usando pandas, openpyxl, etc.)
        #     # ...
        #     # Detección y reporte de errores de validación (RD25)
        #     return Response({"message": "Disponibilidad cargada y validada exitosamente."}, status=status.HTTP_201_CREATED)
        # except Exception as e:
        #     return Response({"error": f"Error procesando el archivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"message": "Funcionalidad de carga Excel pendiente de implementación detallada."}, status=status.HTTP_501_NOT_IMPLEMENTED)


class HorariosAsignadosViewSet(viewsets.ModelViewSet):
    queryset = HorariosAsignados.objects.select_related(
        'grupo__materia', 'grupo__carrera', 'docente', 'espacio', 'periodo', 'bloque_horario'
    ).all()
    serializer_class = HorariosAsignadosSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    # RU07: Visualización de horarios por diferentes criterios
    filterset_fields = ['periodo', 'docente', 'espacio', 'grupo', 'grupo__materia', 'grupo__carrera', 'dia_semana']

    # RD09: Permitir modificaciones manuales sobre los horarios generados automáticamente.
    # El ModelViewSet ya lo permite con PUT/PATCH. Se pueden añadir validaciones extra.

    def perform_create(self, serializer):
        # RD10: Notificar sobre conflictos (o prevenirlos)
        # Podríamos llamar al validador de conflictos aquí antes de guardar
        # validator = ConflictValidatorService()
        # conflicts = validator.validate_assignment(serializer.validated_data)
        # if conflicts:
        #    raise serializers.ValidationError(conflicts)
        serializer.save()

    def perform_update(self, serializer):
        # Similar validación para updates
        serializer.save()


class ConfiguracionRestriccionesViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionRestricciones.objects.select_related('periodo_aplicable').all()
    serializer_class = ConfiguracionRestriccionesSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

class GeneracionHorarioView(viewsets.ViewSet):
    permission_classes = [AllowAny] # Reemplaza AllowAny con un permiso adecuado

    @action(detail=False, methods=['post'], url_path='generar-horario-automatico')
    def generar_horario(self, request):
        periodo_id = request.data.get('periodo_id')
        if not periodo_id:
            logger.warning(f"Intento de generar horario sin periodo_id por usuario: {request.user.username if request.user.is_authenticated else 'Anónimo'}")
            return Response({"error": "Se requiere el ID del período académico."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            periodo = PeriodoAcademico.objects.get(pk=periodo_id)
        except PeriodoAcademico.DoesNotExist:
            logger.warning(f"Intento de generar horario para periodo_id no existente: {periodo_id} por usuario: {request.user.username if request.user.is_authenticated else 'Anónimo'}")
            return Response({"error": "Período académico no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Iniciando generación SÍNCRONA para periodo_id: {periodo_id} (Solicitado por: {request.user.username if request.user.is_authenticated else 'Anónimo'})")

        # Pasamos la instancia del logger de la vista al servicio
        generator_service = ScheduleGeneratorService(periodo=periodo, stdout_ref=logger)

        try:
            resultado = generator_service.generar_horarios_automaticos()
            logger.info(f"Generación SÍNCRONA para periodo_id: {periodo_id} completada. Stats: {resultado.get('stats')}")
            return Response({
                "message": f"Proceso de generación de horarios para {periodo.nombre_periodo} completado (síncrono).",
                "stats": resultado.get('stats', {}),
                "unresolved_conflicts": resultado.get('unresolved_conflicts', [])
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error catastrófico en generación síncrona de horario para periodo_id {periodo_id}: {str(e)}", exc_info=True)
            return Response({"error": f"Ocurrió un error crítico durante la generación síncrona: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-horarios-excel')
    def exportar_horarios(self, request):
        periodo_id = request.query_params.get('periodo_id')
        if not periodo_id:
            logger.warning(f"Intento de exportar horarios sin periodo_id por usuario: {request.user.username if request.user.is_authenticated else 'Anónimo'}")
            return Response({"error": "Se requiere el parámetro 'periodo_id'."}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Solicitud de exportación a Excel para periodo_id: {periodo_id} por usuario: {request.user.username if request.user.is_authenticated else 'Anónimo'}")
        # ... (Aquí iría la lógica de exportación a Excel) ...
        return Response({"message": "Funcionalidad de exportación a Excel pendiente de implementación detallada."}, status=status.HTTP_501_NOT_IMPLEMENTED)
