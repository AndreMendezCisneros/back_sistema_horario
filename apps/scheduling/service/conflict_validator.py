from apps.scheduling.models import HorariosAsignados

class ConflictValidatorService:
    def __init__(self, periodo):
        self.periodo = periodo
        # Para validaciones dentro de una misma sesión de generación, sin golpear la BD constantemente
        self.current_session_assignments = {
            "docentes": set(), # (docente_id, dia, bloque_id)
            "espacios": set(), # (espacio_id, dia, bloque_id)
            "grupos": set()    # (grupo_id, dia, bloque_id)
        }

    def check_slot_conflict(self, docente_id, espacio_id, grupo_id, dia_semana, bloque_id):
        """Verifica si un slot propuesto tiene conflictos con asignaciones existentes o de la sesión actual."""
        # Conflicto con asignaciones en la BD
        if HorariosAsignados.objects.filter(
                periodo=self.periodo, dia_semana=dia_semana, bloque_horario_id=bloque_id,
                docente_id=docente_id
        ).exists():
            return {"type": "docente_conflict", "message": "Docente ya asignado en este bloque."}

        if HorariosAsignados.objects.filter(
                periodo=self.periodo, dia_semana=dia_semana, bloque_horario_id=bloque_id,
                espacio_id=espacio_id
        ).exists():
            return {"type": "espacio_conflict", "message": "Espacio ya asignado en este bloque."}

        if HorariosAsignados.objects.filter(
                periodo=self.periodo, dia_semana=dia_semana, bloque_horario_id=bloque_id,
                grupo_id=grupo_id
        ).exists():
            return {"type": "grupo_conflict", "message": "Grupo ya tiene una clase en este bloque."}

        # Conflicto con asignaciones de la sesión actual de generación
        if (docente_id, dia_semana, bloque_id) in self.current_session_assignments["docentes"]:
            return {"type": "docente_session_conflict", "message": "Docente ya asignado en este bloque (sesión actual)."}
        if (espacio_id, dia_semana, bloque_id) in self.current_session_assignments["espacios"]:
            return {"type": "espacio_session_conflict", "message": "Espacio ya asignado en este bloque (sesión actual)."}
        if (grupo_id, dia_semana, bloque_id) in self.current_session_assignments["grupos"]:
            return {"type": "grupo_session_conflict", "message": "Grupo ya asignado en este bloque (sesión actual)."}

        return None # Sin conflictos

    def mark_slot_used(self, docente_id, espacio_id, grupo_id, dia_semana, bloque_id):
        """Marca un slot como usado durante la sesión actual de generación."""
        self.current_session_assignments["docentes"].add((docente_id, dia_semana, bloque_id))
        self.current_session_assignments["espacios"].add((espacio_id, dia_semana, bloque_id))
        self.current_session_assignments["grupos"].add((grupo_id, dia_semana, bloque_id))

    def clear_session_assignments(self):
        """Limpia las asignaciones de la sesión actual."""
        self.current_session_assignments = {"docentes": set(), "espacios": set(), "grupos": set()}

    # Podrías añadir más métodos para validar todas las restricciones de `ConfiguracionRestricciones`
    def validate_all_constraints(self, horario_propuesto_data):
        # horario_propuesto_data es un diccionario con info de la propuesta
        # ...
        pass
