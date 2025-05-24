# apps/scheduling/service/schedule_generator.py
import random
from collections import defaultdict
from django.db.models import Q
import logging

from apps.academic_setup.models import (
    PeriodoAcademico, Materias, EspaciosFisicos, CarreraMaterias, TiposEspacio, MateriaEspecialidadesRequeridas
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

    def _check_hard_configured_constraints(self, grupo, docente, espacio, bloque):
        """
        Verifica las HARD CONSTRAINTS de la tabla ConfiguracionRestricciones.
        Devuelve True si se cumplen todas, False si alguna se viola.
        """
        for r in self.all_restricciones_config:
            # Ejemplo 1: Docente X no puede enseñar Materia Y
            if r.codigo_restriccion == "DOCENTE_NO_ENSENA_MATERIA_HARD": # Asumimos que este código es para una hard constraint
                if r.tipo_aplicacion == "DOCENTE_MATERIA" and r.entidad_id_1 == docente.docente_id and r.entidad_id_2 == grupo.materia_id:
                    self.logger.debug(f"Conflicto HARD Config: Docente {docente.codigo_docente} no puede enseñar {grupo.materia.codigo_materia}")
                    return False

            # Ejemplo 2: Materia X solo en Aula Y (HARD)
            if r.codigo_restriccion == R_AULA_EXCLUSIVA_MATERIA and r.tipo_aplicacion == "MATERIA":
                if r.entidad_id_1 == grupo.materia_id and str(espacio.espacio_id) != r.valor_parametro:
                    self.logger.debug(f"Conflicto HARD Config: Materia {grupo.materia.codigo_materia} debe estar en aula ID {r.valor_parametro}, no en {espacio.nombre_espacio}")
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

    def _calculate_soft_constraint_penalties(self, grupo_obj, docente, espacio, bloque):
        """Calcula penalizaciones por violaciones de SOFT CONSTRAINTS."""
        penalty = 0

        # Preferencia del docente (ya estaba, la mantenemos y ajustamos)
        preferencia_docente = self.docente_disponibilidad_map.get(
            (docente.docente_id, bloque.dia_semana, bloque.bloque_def_id), 0
        )
        if preferencia_docente < 0: penalty += (abs(preferencia_docente) * 10)
        elif preferencia_docente == 0: penalty += 5
        # Si es > 0 (preferido), no se suma o incluso se podría restar (bonificación)
        # elif preferencia_docente > 0: penalty -= (preferencia_docente * 2)

        # Capacidad del aula
        num_estudiantes = grupo_obj.numero_estudiantes_estimado or 0
        if num_estudiantes > 0: # Solo aplicar si hay estudiantes estimados
            if espacio.capacidad < num_estudiantes:
                penalty += (num_estudiantes - espacio.capacidad) * 5 # Penalización más alta por falta de espacio
            elif espacio.capacidad > num_estudiantes * 2.5: # Aula demasiado grande
                penalty += 10

        # Turno preferente del grupo
        if grupo_obj.turno_preferente and grupo_obj.turno_preferente != bloque.turno:
            penalty += 20

        # Aplicar ConfiguracionRestricciones de tipo SOFT
        for r in self.all_restricciones_config:
            if r.codigo_restriccion == "PREFERIR_AULA_X_PARA_MATERIA_Y": # Asumir soft
                if r.tipo_aplicacion == "MATERIA" and r.entidad_id_1 == grupo_obj.materia_id and str(espacio.espacio_id) != r.valor_parametro:
                    penalty += 15 # Penalización por no usar el aula preferida

            if r.codigo_restriccion == "EVITAR_HUECOS_LARGOS_DOCENTE": # Soft, requiere lógica más compleja
                # Lógica para chequear el horario parcial del docente y penalizar huecos
                # sesiones_docente_dia = self.horario_parcial_docentes[docente.docente_id][bloque.dia_semana]
                # ... calcular huecos ...
                pass

            # TODO: Añadir lógica para más códigos de restricción SOFT
        return penalty

    def _prioritize_grupos(self, grupos_del_turno):
        self.logger.debug(f"Priorizando {len(grupos_del_turno)} grupos para el turno...")

        grupos_info_con_sesiones = []
        for g in grupos_del_turno:
            horas_materia = g.materia.horas_totales
            sesiones_necesarias = 0
            if HORAS_ACADEMICAS_POR_SESION_ESTANDAR > 0 and horas_materia > 0:
                sesiones_necesarias = (horas_materia + HORAS_ACADEMICAS_POR_SESION_ESTANDAR - 1) // HORAS_ACADEMICAS_POR_SESION_ESTANDAR
            elif horas_materia > 0:
                sesiones_necesarias = 1

            grupos_info_con_sesiones.append({
                'objeto': g,
                'ciclo': g.ciclo_semestral or 99, # Usar el campo del modelo, fallback a 99
                'sesiones_necesarias': sesiones_necesarias,
                'sesiones_programadas': 0
            })

        def sort_key(grupo_info_dict):
            grupo = grupo_info_dict['objeto']
            ciclo = grupo_info_dict['ciclo']
            requiere_lab_especifico = 1 if grupo.materia.requiere_tipo_espacio_especifico else 0
            sesiones_req = grupo_info_dict['sesiones_necesarias']
            # Más criterios: ej. número de restricciones asociadas (requeriría pre-cálculo)
            # num_restricciones_especificas = len([r for r in self.all_restricciones_config if r.entidad_id_1 == grupo.grupo_id and r.tipo_aplicacion == "GRUPO"])
            return (ciclo, -requiere_lab_especifico, -sesiones_req, grupo.grupo_id)

        return sorted(grupos_info_con_sesiones, key=sort_key)

    def _get_docentes_candidatos(self, materia: Materias, bloque: BloquesHorariosDefinicion, grupo: Grupos): # Añadido grupo
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

            if not self._check_hard_configured_constraints(grupo, docente, None, bloque): # Chequear restricciones que solo involucran docente/grupo/bloque
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
            if not self._check_hard_configured_constraints(grupo, None, espacio, bloque): # Chequear restricciones que solo involucran espacio/grupo/bloque
                continue
            candidatos.append(espacio)

        # Ordenar por "mejor ajuste" de capacidad
        # random.shuffle(candidatos)
        return sorted(candidatos, key=lambda e: abs(e.capacidad - num_estudiantes))

    def _find_best_assignment_for_session(self, grupo_info, bloques_del_turno):
        grupo_obj = grupo_info['objeto']
        materia = grupo_obj.materia
        mejor_asignacion_info = None
        mejor_score = float('inf')

        # Iterar sobre bloques candidatos (podrían ser pre-filtrados)
        for bloque_cand in bloques_del_turno:
            # Obtener docentes candidatos para esta materia, grupo y bloque
            docentes_candidatos = self._get_docentes_candidatos(materia, bloque_cand, grupo_obj)
            if not docentes_candidatos: continue

            # Obtener espacios candidatos para esta materia, grupo y bloque
            espacios_candidatos = self._get_espacios_candidatos(materia, grupo_obj, bloque_cand)
            if not espacios_candidatos: continue

            for docente_cand in docentes_candidatos:
                for espacio_cand in espacios_candidatos:
                    # 1. Verificar Hard Conflicts del validador (cruces básicos)
                    hard_conflict_details = self.validator.check_slot_conflict(
                        docente_id=docente_cand.docente_id,
                        espacio_id=espacio_cand.espacio_id,
                        grupo_id=grupo_obj.grupo_id,
                        dia_semana=bloque_cand.dia_semana,
                        bloque_id=bloque_cand.bloque_def_id
                    )
                    if hard_conflict_details:
                        self.logger.debug(f"  Validador Conflict: G:{grupo_obj.codigo_grupo} D:{docente_cand.codigo_docente} E:{espacio_cand.nombre_espacio} B:{bloque_cand.nombre_bloque} - {hard_conflict_details['message']}")
                        continue

                    # 2. Verificar Hard Constraints de `ConfiguracionRestricciones`
                    if not self._check_hard_configured_constraints(grupo_obj, docente_cand, espacio_cand, bloque_cand):
                        continue

                    # 3. Evaluar Soft Constraints
                    current_score = self._calculate_soft_constraint_penalties(grupo_obj, docente_cand, espacio_cand, bloque_cand)

                    if current_score < mejor_score:
                        mejor_score = current_score
                        mejor_asignacion_info = {
                            "grupo": grupo_obj, "docente": docente_cand, "espacio": espacio_cand,
                            "dia_semana": bloque_cand.dia_semana, "bloque_horario": bloque_cand,
                            "score": current_score
                        }
                        # En una heurística greedy simple, podríamos tomar la primera que encontremos
                        # return mejor_asignacion_info

        return mejor_asignacion_info

    def generar_horarios_por_turno(self, turno_codigo, ciclos_del_turno):
        self.logger.info(f"--- Iniciando generación para Turno {turno_codigo} (Ciclos: {ciclos_del_turno}) ---")

        # Obtener grupos que pertenecen a los ciclos de este turno
        # ASUME que el modelo Grupo tiene un campo 'ciclo_semestral'
        grupos_para_este_turno_objetos = list(Grupos.objects.filter(
            periodo=self.periodo,
            ciclo_semestral__in=ciclos_del_turno # Usando el nuevo campo
        ).select_related('materia', 'carrera'))

        if not grupos_para_este_turno_objetos:
            self.logger.info(f"No hay grupos para programar en el Turno {turno_codigo}.")
            return

        grupos_priorizados_info = self._prioritize_grupos(grupos_para_este_turno_objetos)
        bloques_del_turno = [b for b in self.all_bloques_ordered if b.turno == turno_codigo]

        for grupo_info in grupos_priorizados_info:
            grupo_obj = grupo_info['objeto']
            self.logger.info(f"Procesando Grupo: {grupo_obj.codigo_grupo} ({grupo_obj.materia.nombre_materia}), Ciclo: {grupo_obj.ciclo_semestral}, Sesiones Requeridas: {grupo_info['sesiones_necesarias']}, Programadas: {grupo_info['sesiones_programadas']}")

            while grupo_info['sesiones_programadas'] < grupo_info['sesiones_necesarias']:
                self.logger.info(f"  Buscando sesión {grupo_info['sesiones_programadas'] + 1} de {grupo_info['sesiones_necesarias']} para {grupo_obj.codigo_grupo}...")

                mejor_asignacion = self._find_best_assignment_for_session(grupo_info, bloques_del_turno)

                if mejor_asignacion:
                    asignacion_obj = HorariosAsignados.objects.create(
                        grupo=mejor_asignacion["grupo"],
                        docente=mejor_asignacion["docente"],
                        espacio=mejor_asignacion["espacio"],
                        periodo=self.periodo,
                        dia_semana=mejor_asignacion["dia_semana"],
                        bloque_horario=mejor_asignacion["bloque_horario"],
                        estado="Programado"
                    )
                    grupo_info['sesiones_programadas'] += 1
                    self.generation_stats["sesiones_programadas_total"] +=1
                    self.generation_stats["asignaciones_exitosas"] += 1

                    # Actualizar horarios parciales para chequeos de carga y huecos
                    doc_id = mejor_asignacion["docente"].docente_id
                    esp_id = mejor_asignacion["espacio"].espacio_id
                    g_id = mejor_asignacion["grupo"].grupo_id
                    dia = mejor_asignacion["dia_semana"]
                    bloque_id = mejor_asignacion["bloque_horario"].bloque_def_id

                    self.horario_parcial_docentes[doc_id][dia].append(bloque_id)
                    self.horario_parcial_espacios[esp_id][dia].append(bloque_id)
                    self.horario_parcial_grupos[g_id][dia].append(bloque_id)

                    self.validator.mark_slot_used(docente_id=doc_id, espacio_id=esp_id, grupo_id=g_id, dia_semana=dia, bloque_id=bloque_id)

                    self.logger.info(f"    ASIGNADO: Sesión {grupo_info['sesiones_programadas']} para {grupo_obj.codigo_grupo} en {mejor_asignacion['bloque_horario'].nombre_bloque} con D:{mejor_asignacion['docente'].codigo_docente} en E:{mejor_asignacion['espacio'].nombre_espacio}. Score: {mejor_asignacion['score']}")
                else:
                    self.unresolved_conflicts.append(
                        f"Turno {turno_codigo}: No se pudo asignar la sesión {grupo_info['sesiones_programadas'] + 1} para {grupo_obj.codigo_grupo} ({grupo_obj.materia.nombre_materia})."
                    )
                    self.logger.warning(f"    FALLO: No se pudo asignar sesión {grupo_info['sesiones_programadas'] + 1} para {grupo_obj.codigo_grupo}.")
                    break

            if grupo_info['sesiones_necesarias'] > 0:
                if grupo_info['sesiones_programadas'] == grupo_info['sesiones_necesarias']:
                    self.generation_stats["grupos_totalmente_programados"] += 1
                elif grupo_info['sesiones_programadas'] > 0:
                    self.generation_stats["grupos_parcialmente_programados"] += 1
                else:
                    self.generation_stats["grupos_no_programados"] += 1

    def generar_horarios_automaticos(self):
        self.logger.info(f"=== Iniciando generación de horarios para el período: {self.periodo.nombre_periodo} ===")
        HorariosAsignados.objects.filter(periodo=self.periodo).delete()
        self.validator.clear_session_assignments()
        self.unresolved_conflicts = []
        self.generation_stats = defaultdict(int) # Reiniciar con defaultdict
        self.horario_parcial_docentes.clear()
        self.horario_parcial_espacios.clear()
        self.horario_parcial_grupos.clear()

        todos_grupos_del_periodo_obj = list(Grupos.objects.filter(periodo=self.periodo).select_related('materia'))
        total_sesiones_req = 0
        for g in todos_grupos_del_periodo_obj:
            horas_materia = g.materia.horas_totales
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
