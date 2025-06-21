# apps/scheduling/view.py
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
    queryset = Grupos.objects.select_related(
        'carrera', 'periodo', 'docente_asignado_directamente'
    ).prefetch_related('materias').all()
    serializer_class = GruposSerializer
    permission_classes = [permissions.AllowAny] # Temporalmente abierto para pruebas
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['carrera', 'periodo', 'ciclo_semestral', 'turno_preferente']

    def update(self, request, *args, **kwargs):
        print(f"[GruposViewSet] Actualizando grupo {kwargs.get('pk')}")
        print(f"[GruposViewSet] Datos recibidos: {request.data}")
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            print(f"[GruposViewSet] Error en update: {str(e)}")
            raise

    @action(detail=True, methods=['post'], url_path='generar-horario')
    def generar_horario(self, request, pk=None):
        """
        Endpoint para disparar la generación de horario para un único grupo.
        """
        grupo = self.get_object()
        periodo_activo = grupo.periodo

        if not periodo_activo:
            return Response(
                {"error": "El grupo no está asociado a un período académico válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(f"Iniciando generador de horarios para el grupo '{grupo.codigo_grupo}' en el período '{periodo_activo.nombre_periodo}'...")
        
        # Instanciar el servicio
        generator = ScheduleGeneratorService(periodo=periodo_activo)

        # Llamar al nuevo método específico para un grupo
        resultado = generator.generar_horario_para_grupo(grupo_id=grupo.grupo_id)

        if "error" in resultado:
            return Response(resultado, status=status.HTTP_404_NOT_FOUND)
        if "warning" in resultado:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

        return Response(resultado, status=status.HTTP_200_OK)


class BloquesHorariosDefinicionViewSet(viewsets.ModelViewSet):
    queryset = BloquesHorariosDefinicion.objects.all()
    serializer_class = BloquesHorariosDefinicionSerializer
    permission_classes = [permissions.AllowAny]


class DisponibilidadDocentesViewSet(viewsets.ModelViewSet):
    queryset = DisponibilidadDocentes.objects.select_related('docente', 'periodo', 'bloque_horario').all()
    serializer_class = DisponibilidadDocentesSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['docente', 'periodo']
    pagination_class = None # Deshabilitar paginación para este ViewSet


class HorariosAsignadosViewSet(viewsets.ModelViewSet):
    queryset = HorariosAsignados.objects.select_related('grupo', 'docente', 'espacio', 'periodo', 'bloque_horario', 'materia').all()
    serializer_class = HorariosAsignadosSerializer
    permission_classes = [permissions.AllowAny]


class ConfiguracionRestriccionesViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionRestricciones.objects.select_related('periodo_aplicable').all()
    serializer_class = ConfiguracionRestriccionesSerializer
    permission_classes = [permissions.AllowAny]

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
            
            # Convertir conflictos no resueltos a formato serializable
            unresolved_conflicts_serializable = []
            for conflict in resultado.get('unresolved_conflicts', []):
                unresolved_conflicts_serializable.append({
                    'grupo_id': conflict.grupo.grupo_id,
                    'grupo_codigo': conflict.grupo.codigo_grupo,
                    'materia_id': conflict.materia.materia_id,
                    'materia_nombre': conflict.materia.nombre_materia,
                    'sesiones_necesarias': conflict.sesiones_necesarias,
                    'sesiones_programadas': conflict.sesiones_programadas,
                    'razon': f"No se pudo programar {conflict.sesiones_necesarias - conflict.sesiones_programadas} sesiones de {conflict.materia.nombre_materia}"
                })
            
            return Response({
                "message": f"Proceso de generación de horarios para {periodo.nombre_periodo} completado (síncrono).",
                "stats": resultado.get('stats', {}),
                "unresolved_conflicts": unresolved_conflicts_serializable
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
