# apps/scheduling/service/schedule_generator.py
import random
from collections import defaultdict, namedtuple
from django.db.models import Q
import logging

from apps.academic_setup.models import (
    PeriodoAcademico, Materias, EspaciosFisicos, CarreraMaterias, TiposEspacio, MateriaEspecialidadesRequeridas, Ciclo
)
from apps.users.models import Docentes
from apps.scheduling.models import (
    Grupos, DisponibilidadDocentes, HorariosAsignados,
    ConfiguracionRestricciones, BloquesHorariosDefinicion
)
from .conflict_validator import ConflictValidatorService

TURNOS_CICLOS_MAP = {
    'M': [1, 2, 3],
    'T': [4, 5, 6, 7],
    'N': [8, 9, 10]
}
HORAS_ACADEMICAS_POR_SESION_ESTANDAR = 2 # Asumimos que cada bloque cubre esto

# Constantes para los códigos de restricción (para evitar errores de tipeo)
R_MAX_HORAS_DIA_DOCENTE = "MAX_HORAS_DIA_DOCENTE"
R_AULA_EXCLUSIVA_MATERIA = "AULA_EXCLUSIVA_MATERIA"
R_DOCENTE_NO_DISPONIBLE_BLOQUE_ESP = "DOCENTE_NO_DISPONIBLE_BLOQUE_ESP" # Si se quiere bloquear explícitamente un docente de un bloque
R_NO_CLASES_DIA_TURNO_CARRERA = "NO_CLASES_DIA_TURNO_CARRERA"


# Representa la unidad atómica a ser programada: una materia específica para un grupo.
ClaseParaProgramar = namedtuple('ClaseParaProgramar', [
    'grupo',
    'materia',
    'sesiones_necesarias',
    'sesiones_programadas'
])


class ScheduleGeneratorService:
    def __init__(self, periodo: PeriodoAcademico, stdout_ref=None):
        self.periodo = periodo
        self.validator = ConflictValidatorService(periodo=self.periodo)
        self.unresolved_conflicts = []
        self.generation_stats = defaultdict(int) # Usar defaultdict para estadísticas

        if stdout_ref and all(hasattr(stdout_ref, attr) for attr in ['info', 'warning', 'error', 'debug']):
            self.logger = stdout_ref
        else:
            self.logger = logging.getLogger(f"schedule_generator_service.{self.periodo.id if self.periodo else 'default_period'}")
            if not self.logger.hasHandlers():
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
                self.logger.propagate = False

        self.horario_parcial_docentes = defaultdict(lambda: defaultdict(list)) # {docente_id: {dia_semana: [bloque_def_id_asignado, ...]}}
        self.horario_parcial_espacios = defaultdict(lambda: defaultdict(list)) # {espacio_id: {dia_semana: [bloque_def_id_asignado, ...]}}
        self.horario_parcial_grupos = defaultdict(lambda: defaultdict(list)) # {grupo_id: {dia_semana: [bloque_def_id_asignado, ...]}}
        self.horario_parcial_clases = defaultdict(int) # {(grupo_id, materia_id): sesiones_programadas}


        self._load_initial_data()

    def _load_initial_data(self):
        self.logger.info("Cargando datos iniciales para el generador de horarios...")
        self.all_docentes = list(Docentes.objects.prefetch_related('especialidades', 'disponibilidades__bloque_horario').filter(usuario__is_active=True))
        self.all_espacios = list(EspaciosFisicos.objects.select_related('tipo_espacio').all())
        self.all_bloques_ordered = list(BloquesHorariosDefinicion.objects.all().order_by('dia_semana', 'hora_inicio'))

        self.all_restricciones_config = list(ConfiguracionRestricciones.objects.filter(
            (Q(periodo_aplicable=self.periodo) | Q(periodo_aplicable__isnull=True)),
            esta_activa=True
        ).select_related('periodo_aplicable'))

        self.docente_disponibilidad_map = self._map_docente_disponibilidad()
        self.docente_especialidades_map = self._map_docente_especialidades()
        self.materia_especialidades_req_map = self._map_materia_especialidades_requeridas()
        self.logger.info("Datos iniciales cargados exitosamente.")

    def _map_docente_disponibilidad(self): # Sin cambios
        self.logger.debug("Mapeando disponibilidad de docentes...")
        disponibilidades = DisponibilidadDocentes.objects.filter(periodo=self.periodo, esta_disponible=True) \
            .select_related('docente', 'bloque_horario')
        dispo_map = defaultdict(lambda: -999)
        for d in disponibilidades:
            key = (d.docente_id, d.dia_semana, d.bloque_horario_id)
            dispo_map[key] = d.preferencia
        return dispo_map

    def _map_docente_especialidades(self): # Sin cambios
        self.logger.debug("Mapeando especialidades de docentes...")
        doc_esp_map = defaultdict(set)
        for de in Docentes.especialidades.through.objects.all().values('docente_id', 'especialidad_id'):
            doc_esp_map[de['docente_id']].add(de['especialidad_id'])
        return doc_esp_map

    def _map_materia_especialidades_requeridas(self): # Sin cambios
        self.logger.debug("Mapeando especialidades requeridas por materias...")
        mat_esp_req_map = defaultdict(set)
        for mer in MateriaEspecialidadesRequeridas.objects.all().values('materia_id', 'especialidad_id'):
            mat_esp_req_map[mer['materia_id']].add(mer['especialidad_id'])
        return mat_esp_req_map

    def _check_hard_configured_constraints(self, grupo, materia, docente, espacio, bloque):
        """
        Verifica las HARD CONSTRAINTS de la tabla ConfiguracionRestricciones.
        Ahora recibe 'materia' explícitamente.
        """
        for r in self.all_restricciones_config:
            # Ejemplo 1: Docente X no puede enseñar Materia Y
            if r.codigo_restriccion == "DOCENTE_NO_ENSENA_MATERIA_HARD": # Asumimos que este código es para una hard constraint
                if r.tipo_aplicacion == "DOCENTE_MATERIA" and docente and r.entidad_id_1 == docente.docente_id and r.entidad_id_2 == materia.materia_id:
                    self.logger.debug(f"Conflicto HARD Config: Docente {docente.codigo_docente} no puede enseñar {materia.codigo_materia}")
                    return False

            # Ejemplo 2: Materia X solo en Aula Y (HARD)
            if r.codigo_restriccion == R_AULA_EXCLUSIVA_MATERIA and r.tipo_aplicacion == "MATERIA":
                if espacio and r.entidad_id_1 == materia.materia_id and str(espacio.espacio_id) != r.valor_parametro:
                    self.logger.debug(f"Conflicto HARD Config: Materia {materia.codigo_materia} debe estar en aula ID {r.valor_parametro}, no en {espacio.nombre_espacio}")
                    return False

            # Ejemplo 3: No clases en un día/turno para una carrera
            if r.codigo_restriccion == R_NO_CLASES_DIA_TURNO_CARRERA and r.tipo_aplicacion == "CARRERA_DIA_TURNO":
                # Asumimos valor_parametro como "DIA_NUM-TURNO_COD", ej. "5-T" para Viernes Tarde
                dia_restringido, turno_restringido = r.valor_parametro.split('-')
                if r.entidad_id_1 == grupo.carrera_id and \
                        str(bloque.dia_semana) == dia_restringido and \
                        bloque.turno == turno_restringido:
                    self.logger.debug(f"Conflicto HARD Config: Carrera {grupo.carrera.codigo_carrera} no tiene clases el {dia_restringido} turno {turno_restringido}")
                    return False

            # TODO: Añadir lógica para más códigos de restricción HARD
        return True

    def _calculate_soft_constraint_penalties(self, grupo, materia, docente, espacio, bloque):
        """Calcula penalizaciones por violaciones de SOFT CONSTRAINTS. Ahora recibe 'materia'"""
        penalty = 0

        # Preferencia del docente (ya estaba, la mantenemos y ajustamos)
        preferencia_docente = self.docente_disponibilidad_map.get(
            (docente.docente_id, bloque.dia_semana, bloque.bloque_def_id), 0
        )
        if preferencia_docente < 0: penalty += (abs(preferencia_docente) * 10)
        elif preferencia_docente == 0: penalty += 5
        # Si es > 0 (preferido), no se podría restar (bonificación)
        # elif preferencia_docente > 0: penalty -= (preferencia_docente * 2)

        # Capacidad del aula
        num_estudiantes = grupo.numero_estudiantes_estimado or 0
        if num_estudiantes > 0: # Solo aplicar si hay estudiantes estimados
            if espacio.capacidad < num_estudiantes:
                penalty += (num_estudiantes - espacio.capacidad) * 5 # Penalización más alta por falta de espacio
            elif espacio.capacidad > num_estudiantes * 2.5: # Aula demasiado grande
                penalty += 10

        # Turno preferente del grupo
        if grupo.turno_preferente and grupo.turno_preferente != bloque.turno:
            penalty += 20

        # Aplicar ConfiguracionRestricciones de tipo SOFT
        for r in self.all_restricciones_config:
            if r.codigo_restriccion == "PREFERIR_AULA_X_PARA_MATERIA_Y": # Asumir soft
                if r.tipo_aplicacion == "MATERIA" and r.entidad_id_1 == materia.materia_id and str(espacio.espacio_id) != r.valor_parametro:
                    penalty += 15 # Penalización por no usar el aula preferida

            if r.codigo_restriccion == "EVITAR_HUECOS_LARGOS_DOCENTE": # Soft, requiere lógica más compleja
                # Lógica para chequear el horario parcial del docente y penalizar huecos
                # sesiones_docente_dia = self.horario_parcial_docentes[docente.docente_id][bloque.dia_semana]
                # ... calcular huecos ...
                pass

            # TODO: Añadir lógica para más códigos de restricción SOFT
        return penalty

    def _crear_lista_clases_para_programar(self, grupos_del_turno):
        self.logger.debug(f"Creando lista de clases a programar desde {len(grupos_del_turno)} grupos...")

        clases_a_programar = []
        for g in grupos_del_turno:
            for materia_obj in g.materias.all(): # Iterar sobre todas las materias del grupo
                horas_materia = materia_obj.horas_totales
            sesiones_necesarias = 0
            if HORAS_ACADEMICAS_POR_SESION_ESTANDAR > 0 and horas_materia > 0:
                sesiones_necesarias = (horas_materia + HORAS_ACADEMICAS_POR_SESION_ESTANDAR - 1) // HORAS_ACADEMICAS_POR_SESION_ESTANDAR
            elif horas_materia > 0:
                sesiones_necesarias = 1

                if sesiones_necesarias > 0:
                    clase = ClaseParaProgramar(
                        grupo=g,
                        materia=materia_obj,
                        sesiones_necesarias=sesiones_necesarias,
                        sesiones_programadas=0
                    )
                    clases_a_programar.append(clase)

        def sort_key(clase: ClaseParaProgramar):
            ciclo = clase.grupo.ciclo_semestral or 99
            requiere_lab_especifico = 1 if clase.materia.requiere_tipo_espacio_especifico else 0
            # num_restricciones = ... (lógica más compleja si se necesita)
            return (ciclo, -requiere_lab_especifico, -clase.sesiones_necesarias, clase.grupo.grupo_id, clase.materia.materia_id)

        self.logger.info(f"Se generaron {len(clases_a_programar)} clases únicas para programar.")
        return sorted(clases_a_programar, key=sort_key)

    def _get_docentes_candidatos(self, materia: Materias, grupo: Grupos, bloque: BloquesHorariosDefinicion): # Añadido grupo
        candidatos = []
        especialidades_requeridas = self.materia_especialidades_req_map.get(materia.materia_id, set())

        for docente in self.all_docentes:
            preferencia = self.docente_disponibilidad_map.get(
                (docente.docente_id, bloque.dia_semana, bloque.bloque_def_id), -999
            )
            if preferencia < -900: continue

            if especialidades_requeridas:
                docente_especialidades = self.docente_especialidades_map.get(docente.docente_id, set())
                if not especialidades_requeridas.issubset(docente_especialidades): # Docente debe tener TODAS las especialidades requeridas
                    continue

            # Verificar MAX_HORAS_DIA_DOCENTE (HARD)
            # Esta es una implementación de ejemplo, puede ser más sofisticada
            sesiones_hoy_docente = len(self.horario_parcial_docentes[docente.docente_id][bloque.dia_semana])
            max_horas_dia_str = "6" # Default
            for r in self.all_restricciones_config:
                if r.codigo_restriccion == R_MAX_HORAS_DIA_DOCENTE and \
                        (r.tipo_aplicacion == "GLOBAL" or (r.tipo_aplicacion == "DOCENTE" and r.entidad_id_1 == docente.docente_id)):
                    max_horas_dia_str = r.valor_parametro
                    break # Tomar la más específica o la primera global

            max_sesiones_dia = int(max_horas_dia_str) // HORAS_ACADEMICAS_POR_SESION_ESTANDAR # Convertir horas a sesiones
            if sesiones_hoy_docente >= max_sesiones_dia:
                self.logger.debug(f"Docente {docente.codigo_docente} ha alcanzado max sesiones ({max_sesiones_dia}) para día {bloque.dia_semana}")
                continue

            if not self._check_hard_configured_constraints(grupo, materia, docente, None, bloque): # Chequear restricciones que solo involucran docente/grupo/bloque
                continue

            candidatos.append(docente)

        # Ordenar candidatos por alguna preferencia (ej. menor carga actual, mayor preferencia por el bloque)
        # random.shuffle(candidatos) # O simplemente aleatorizar
        return candidatos

    def _get_espacios_candidatos(self, materia: Materias, grupo: Grupos, bloque: BloquesHorariosDefinicion): # Añadido bloque
        candidatos = []
        num_estudiantes = grupo.numero_estudiantes_estimado or 15

        for espacio in self.all_espacios:
            if materia.requiere_tipo_espacio_especifico and materia.requiere_tipo_espacio_especifico != espacio.tipo_espacio:
                continue
            if espacio.capacidad < num_estudiantes:
                continue
            if not self._check_hard_configured_constraints(grupo, materia, None, espacio, bloque): # Chequear restricciones que solo involucran espacio/grupo/bloque
                continue
            candidatos.append(espacio)

        # Ordenar por "mejor ajuste" de capacidad
        # random.shuffle(candidatos)
        return sorted(candidatos, key=lambda e: abs(e.capacidad - num_estudiantes))

    def _find_best_assignment_for_session(self, clase: ClaseParaProgramar, bloques_del_turno):
        """Intenta encontrar el mejor docente, espacio y bloque para una sesión de una clase."""
        grupo = clase.grupo
        materia = clase.materia
        mejor_opcion = None
        menor_penalizacion = float('inf')

        for bloque in bloques_del_turno:
            # 1. Verificar si el bloque ya está ocupado para el grupo
            if bloque.bloque_def_id in self.horario_parcial_grupos.get(grupo.grupo_id, {}).get(bloque.dia_semana, []):
                continue

            # 2. Obtener candidatos (docentes y espacios)
            docentes_candidatos = self._get_docentes_candidatos(materia, grupo, bloque)
            espacios_candidatos = self._get_espacios_candidatos(materia, grupo, bloque)

            if not docentes_candidatos or not espacios_candidatos:
                continue

            # 3. Evaluar combinaciones para encontrar la de menor penalización
            for docente in docentes_candidatos:
                # Verificar si el docente está ocupado en ese bloque
                if bloque.bloque_def_id in self.horario_parcial_docentes.get(docente.docente_id, {}).get(bloque.dia_semana, []):
                    continue

                for espacio in espacios_candidatos:
                    # Verificar si el espacio está ocupado en ese bloque
                    if bloque.bloque_def_id in self.horario_parcial_espacios.get(espacio.espacio_id, {}).get(bloque.dia_semana, []):
                        continue

                    # 3.1 Verificar Hard Constraints (ya se hace dentro de get_candidatos, pero podemos re-verificar por si acaso)
                    if not self._check_hard_configured_constraints(grupo, materia, docente, espacio, bloque):
                        continue

                    # 3.2 Calcular penalizaciones de Soft Constraints
                    penalizacion = self._calculate_soft_constraint_penalties(grupo, materia, docente, espacio, bloque)

                    if penalizacion < menor_penalizacion:
                        menor_penalizacion = penalizacion
                        mejor_opcion = (docente, espacio, bloque)

        return mejor_opcion, menor_penalizacion

    def generar_horarios_por_turno(self, turno_codigo, ciclos_del_turno):
        self.logger.info(f"--- Iniciando generación para TURNO: {turno_codigo} (Ciclos: {ciclos_del_turno}) ---")
        grupos_del_turno = Grupos.objects.filter(
            periodo=self.periodo,
            ciclo_semestral__in=ciclos_del_turno
        ).prefetch_related('materias__requiere_tipo_espacio_especifico').order_by('ciclo_semestral')

        if not grupos_del_turno:
            self.logger.warning(f"No se encontraron grupos para el turno {turno_codigo}. Saltando...")
            return

        bloques_del_turno = [b for b in self.all_bloques_ordered if b.turno == turno_codigo]
        clases_priorizadas = self._crear_lista_clases_para_programar(grupos_del_turno)

        clases_a_reintentar = []

        for clase_idx, clase_info in enumerate(clases_priorizadas):
            # Necesitamos un objeto mutable para actualizar las sesiones programadas
            clase_actual = clase_info

            sesiones_ya_programadas = self.horario_parcial_clases.get((clase_actual.grupo.grupo_id, clase_actual.materia.materia_id), 0)

            for i in range(clase_actual.sesiones_necesarias - sesiones_ya_programadas):
                mejor_opcion, penalizacion = self._find_best_assignment_for_session(clase_actual, bloques_del_turno)

                if mejor_opcion:
                    docente, espacio, bloque = mejor_opcion
                    self.logger.debug(
                        f"[ASIGNACIÓN OK] Clase: {clase_actual.grupo.codigo_grupo}/{clase_actual.materia.codigo_materia} "
                        f"en Bloque: {bloque.nombre_bloque} con Doc: {docente.codigo_docente}, "
                        f"Esp: {espacio.nombre_espacio} (Penalización: {penalizacion})"
                    )

                    # Guardar en la base de datos
                    HorariosAsignados.objects.create(
                        grupo=clase_actual.grupo,
                        materia=clase_actual.materia, # ¡Añadir la materia al horario!
                        docente=docente,
                        espacio=espacio,
                        periodo=self.periodo,
                        dia_semana=bloque.dia_semana,
                        bloque_horario=bloque,
                        estado='Programado'
                    )

                    # Actualizar estado parcial
                    self.horario_parcial_docentes[docente.docente_id][bloque.dia_semana].append(bloque.bloque_def_id)
                    self.horario_parcial_espacios[espacio.espacio_id][bloque.dia_semana].append(bloque.bloque_def_id)
                    self.horario_parcial_grupos[clase_actual.grupo.grupo_id][bloque.dia_semana].append(bloque.bloque_def_id)
                    self.horario_parcial_clases[(clase_actual.grupo.grupo_id, clase_actual.materia.materia_id)] += 1

                else:
                    self.logger.warning(
                        f"[ASIGNACIÓN FALLIDA] No se encontró asignación para la sesión {i+1}/{clase_actual.sesiones_necesarias} "
                        f"de la clase {clase_actual.grupo.codigo_grupo}/{clase_actual.materia.codigo_materia}. Se reintentará más tarde."
                    )
                    # Si no se encuentra una sesión, se podría añadir a una cola de reintento.
                    # Por ahora, simplemente lo registramos.
                    self.unresolved_conflicts.append(clase_actual)
                    break # Dejar de intentar programar más sesiones para esta clase si una falla

        self.logger.info(f"--- Finalizada generación para TURNO: {turno_codigo} ---")
        self.generation_stats["sesiones_programadas_total"] += len(clases_priorizadas)
        self.generation_stats["asignaciones_exitosas"] += len(clases_priorizadas) - len(clases_a_reintentar)
        self.generation_stats["grupos_totalmente_programados"] += 1 if not clases_a_reintentar else 0
        self.generation_stats["grupos_parcialmente_programados"] += 1 if clases_a_reintentar else 0
        self.generation_stats["grupos_no_programados"] += 1 if not clases_priorizadas else 0

    def generar_horario_para_grupo(self, grupo_id: int):
        """
        Genera el horario para un único grupo específico y sus materias asociadas.
        Este es un punto de entrada más específico que el generador masivo por turnos.
        """
        self.logger.info(f"--- Iniciando generación específica para Grupo ID: {grupo_id} ---")
        try:
            grupo_obj = Grupos.objects.prefetch_related(
                'materias__requiere_tipo_espacio_especifico'
            ).get(grupo_id=grupo_id, periodo=self.periodo)
        except Grupos.DoesNotExist:
            self.logger.error(f"No se encontró el grupo con ID {grupo_id} en el período actual.")
            return {"error": f"Grupo {grupo_id} no encontrado."}

        # Borrar horario previo solo para este grupo
        HorariosAsignados.objects.filter(grupo=grupo_obj).delete()
        self.logger.info(f"Horario previo del grupo {grupo_obj.codigo_grupo} eliminado.")

        clases_a_programar = self._crear_lista_clases_para_programar([grupo_obj])
        if not clases_a_programar:
            self.logger.warning(f"El grupo {grupo_obj.codigo_grupo} no tiene clases para programar.")
            return {"warning": "El grupo no tiene clases para programar."}
        
        # Usar todos los bloques o filtrar por turno preferente del grupo si existe
        bloques_disponibles = self.all_bloques_ordered
        if grupo_obj.turno_preferente:
            bloques_disponibles = [b for b in self.all_bloques_ordered if b.turno == grupo_obj.turno_preferente]
            self.logger.info(f"Filtrando bloques para el turno preferente del grupo: {grupo_obj.turno_preferente}")

        sesiones_exitosas = 0
        sesiones_fallidas = 0

        for clase_actual in clases_a_programar:
            for i in range(clase_actual.sesiones_necesarias):
                mejor_opcion, penalizacion = self._find_best_assignment_for_session(clase_actual, bloques_disponibles)

                if mejor_opcion:
                    docente, espacio, bloque = mejor_opcion
                    self.logger.debug(f"[ASIGNACIÓN OK] Clase: {clase_actual.grupo.codigo_grupo}/{clase_actual.materia.codigo_materia} en Bloque: {bloque.nombre_bloque}")
                    
                    HorariosAsignados.objects.create(
                        grupo=clase_actual.grupo, materia=clase_actual.materia,
                        docente=docente, espacio=espacio, periodo=self.periodo,
                        dia_semana=bloque.dia_semana, bloque_horario=bloque, estado='Programado'
                    )

                    self.horario_parcial_docentes[docente.docente_id][bloque.dia_semana].append(bloque.bloque_def_id)
                    self.horario_parcial_espacios[espacio.espacio_id][bloque.dia_semana].append(bloque.bloque_def_id)
                    self.horario_parcial_grupos[clase_actual.grupo.grupo_id][bloque.dia_semana].append(bloque.bloque_def_id)
                    sesiones_exitosas += 1
                else:
                    self.logger.warning(f"[ASIGNACIÓN FALLIDA] No se encontró hueco para la sesión {i+1} de {clase_actual.materia.codigo_materia}.")
                    self.unresolved_conflicts.append(clase_actual)
                    sesiones_fallidas += 1
                    break

        resumen = {
            "grupo_procesado": grupo_obj.codigo_grupo,
            "sesiones_exitosas": sesiones_exitosas,
            "sesiones_fallidas": sesiones_fallidas,
            "conflictos": [f"No se pudo programar la materia {c.materia.codigo_materia}" for c in self.unresolved_conflicts]
        }
        self.logger.info(f"--- Finalizada generación para Grupo ID: {grupo_id}. Resumen: {resumen} ---")
        return resumen

    def generar_horarios_para_ciclo(self, ciclo_id: int):
        """
        Genera el horario para TODOS los grupos que pertenecen a un ciclo específico
        dentro del período académico del servicio.
        """
        self.logger.info(f"--- Iniciando generación masiva para Ciclo ID: {ciclo_id} en Período: {self.periodo.nombre_periodo} ---")
        
        # 1. Encontrar la carrera y el orden del ciclo
        try:
            ciclo_obj = Ciclo.objects.get(pk=ciclo_id)
            carrera_obj = ciclo_obj.carrera
            ciclo_orden = ciclo_obj.orden
        except Ciclo.DoesNotExist:
            self.logger.error(f"El ciclo con ID {ciclo_id} no fue encontrado.")
            return {"error": f"Ciclo {ciclo_id} no encontrado."}

        # 2. Encontrar todos los grupos de la app 'scheduling' que corresponden a ese ciclo, carrera y período.
        grupos_del_ciclo = Grupos.objects.filter(
            periodo=self.periodo,
            carrera=carrera_obj,
            ciclo_semestral=ciclo_orden
        ).prefetch_related('materias')

        if not grupos_del_ciclo.exists():
            msg = f"No se encontraron grupos para el ciclo {ciclo_orden} de la carrera '{carrera_obj.nombre_carrera}' en el período '{self.periodo.nombre_periodo}'."
            self.logger.warning(msg)
            return {"warning": msg}
        
        self.logger.info(f"Se encontraron {len(grupos_del_ciclo)} grupos para procesar: {[g.codigo_grupo for g in grupos_del_ciclo]}")

        # 3. Borrar los horarios existentes para estos grupos
        HorariosAsignados.objects.filter(grupo__in=grupos_del_ciclo).delete()
        self.logger.info(f"Eliminados los horarios previos para los {len(grupos_del_ciclo)} grupos del ciclo.")

        # 4. Crear la lista completa de clases a programar para todos los grupos
        clases_a_programar = self._crear_lista_clases_para_programar(grupos_del_ciclo)
        
        bloques_disponibles = self.all_bloques_ordered # Usar todos los bloques
        
        # 5. Iterar y asignar
        resumen_total = {"grupos_procesados": [], "total_sesiones_exitosas": 0, "total_sesiones_fallidas": 0}

        for grupo in grupos_del_ciclo:
            clases_del_grupo = [c for c in clases_a_programar if c.grupo.grupo_id == grupo.grupo_id]
            sesiones_exitosas_grupo = 0
            sesiones_fallidas_grupo = 0

            for clase_actual in clases_del_grupo:
                for i in range(clase_actual.sesiones_necesarias):
                    mejor_opcion, _ = self._find_best_assignment_for_session(clase_actual, bloques_disponibles)
                    if mejor_opcion:
                        docente, espacio, bloque = mejor_opcion
                        HorariosAsignados.objects.create(
                            grupo=clase_actual.grupo, materia=clase_actual.materia,
                            docente=docente, espacio=espacio, periodo=self.periodo,
                            dia_semana=bloque.dia_semana, bloque_horario=bloque, estado='Programado'
                        )
                        self.horario_parcial_docentes[docente.docente_id][bloque.dia_semana].append(bloque.bloque_def_id)
                        self.horario_parcial_espacios[espacio.espacio_id][bloque.dia_semana].append(bloque.bloque_def_id)
                        self.horario_parcial_grupos[grupo.grupo_id][bloque.dia_semana].append(bloque.bloque_def_id)
                        sesiones_exitosas_grupo += 1
                else:
                        self.unresolved_conflicts.append(clase_actual)
                        sesiones_fallidas_grupo += 1
                        break # No seguir con esta materia si una sesión falla
            
            resumen_total["grupos_procesados"].append({
                "codigo_grupo": grupo.codigo_grupo,
                "sesiones_exitosas": sesiones_exitosas_grupo,
                "sesiones_fallidas": sesiones_fallidas_grupo
            })
            resumen_total["total_sesiones_exitosas"] += sesiones_exitosas_grupo
            resumen_total["total_sesiones_fallidas"] += sesiones_fallidas_grupo

        self.logger.info(f"--- Finalizada generación masiva para Ciclo ID: {ciclo_id}. Resumen: {resumen_total} ---")
        return resumen_total

    def generar_horarios_automaticos(self):
        self.logger.info(f"=== Iniciando generación de horarios para el período: {self.periodo.nombre_periodo} ===")
        HorariosAsignados.objects.filter(periodo=self.periodo).delete()
        self.validator.clear_session_assignments()
        self.unresolved_conflicts = []
        self.generation_stats = defaultdict(int) # Reiniciar con defaultdict
        self.horario_parcial_docentes.clear()
        self.horario_parcial_espacios.clear()
        self.horario_parcial_grupos.clear()
        self.horario_parcial_clases.clear()

        todos_grupos_del_periodo_obj = list(Grupos.objects.filter(periodo=self.periodo).prefetch_related('materias'))
        total_sesiones_req = 0
        for g in todos_grupos_del_periodo_obj:
            # Ahora cada grupo puede tener múltiples materias
            for materia in g.materias.all():
                horas_materia = materia.horas_totales
            sesiones_para_este_grupo = 0
            if HORAS_ACADEMICAS_POR_SESION_ESTANDAR > 0 and horas_materia > 0:
                sesiones_para_este_grupo = (horas_materia + HORAS_ACADEMICAS_POR_SESION_ESTANDAR - 1) // HORAS_ACADEMICAS_POR_SESION_ESTANDAR
            elif horas_materia > 0:
                sesiones_para_este_grupo = 1
            total_sesiones_req += sesiones_para_este_grupo
        self.generation_stats["sesiones_requeridas_total"] = total_sesiones_req

        for turno_cod, ciclos_del_turno in TURNOS_CICLOS_MAP.items():
            self.generar_horarios_por_turno(turno_codigo=turno_cod, ciclos_del_turno=ciclos_del_turno)

        self.logger.info("=== Proceso de generación finalizado. ===")
        self.logger.info(f"Estadísticas: {dict(self.generation_stats)}") # Convertir a dict para logging
        if self.unresolved_conflicts:
            self.logger.warning("Conflictos no resueltos / Sesiones no asignadas:")
            for conflict in self.unresolved_conflicts:
                self.logger.warning(f"  - {conflict}")

        return {
            "stats": dict(self.generation_stats), # Convertir a dict para la respuesta JSON
            "unresolved_conflicts": self.unresolved_conflicts
        }
