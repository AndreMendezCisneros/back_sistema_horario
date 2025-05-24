# apps/scheduling/tasks.py
from celery import shared_task
from apps.academic_setup.models import PeriodoAcademico
from .service.schedule_generator import ScheduleGeneratorService
import logging # Usar el sistema de logging de Python/Django

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def generar_horarios_task(self, periodo_id):
    logger.info(f"Iniciando tarea de generación de horarios para periodo_id: {periodo_id} (Task ID: {self.request.id})")
    try:
        periodo = PeriodoAcademico.objects.get(pk=periodo_id)
        # Crear una instancia del logger de Django o Python para pasar al servicio
        # para que los logs del servicio vayan al sistema de logging de Celery/Django.
        task_logger = logging.getLogger(f"schedule_generator_task.{self.request.id}")

        generator_service = ScheduleGeneratorService(periodo=periodo, stdout_ref=task_logger) # Pasa el logger
        resultado = generator_service.generar_horarios_automaticos()

        logger.info(f"Generación para periodo_id: {periodo_id} completada. Stats: {resultado.get('stats')}")
        # Aquí podrías guardar el resultado en algún lugar (BD, caché) o enviar una notificación.
        return {"status": "COMPLETED", "periodo_id": periodo_id, "resultado": resultado}
    except PeriodoAcademico.DoesNotExist:
        logger.error(f"Error en tarea: Período académico {periodo_id} no encontrado.")
        return {"status": "FAILED", "periodo_id": periodo_id, "error": "Período no encontrado"}
    except Exception as e:
        logger.error(f"Error catastrófico en tarea de generación para periodo_id: {periodo_id}. Error: {str(e)}", exc_info=True)
        return {"status": "FAILED", "periodo_id": periodo_id, "error": str(e)}
