#apps/scheduling/models.py
from django.db import models
from apps.academic_setup.models import Materias, Carrera, PeriodoAcademico, TiposEspacio, EspaciosFisicos
from apps.users.models import Docentes

class Grupos(models.Model):
    TURNO_CHOICES = [('M', 'Mañana'), ('T', 'Tarde'), ('N', 'Noche')]

    grupo_id = models.AutoField(primary_key=True)
    codigo_grupo = models.CharField(max_length=50)
    materias = models.ManyToManyField(Materias, related_name='grupos')
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='grupos')
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE, related_name='grupos')
    numero_estudiantes_estimado = models.IntegerField(blank=True, null=True)
    turno_preferente = models.CharField(max_length=1, choices=TURNO_CHOICES, blank=True, null=True)
    docente_asignado_directamente = models.ForeignKey(Docentes, on_delete=models.SET_NULL, null=True, blank=True, related_name='grupos_asignados_directo') # Para asignación manual previa
    ciclo_semestral = models.IntegerField(
        null=True, blank=True,
        help_text="Ciclo académico al que pertenece este grupo/materia (ej. 1, 2, ..., 10)"
    )

    def __str__(self):
        nombre_materias = ", ".join([m.nombre_materia for m in self.materias.all()])
        return f"{self.codigo_grupo} ({nombre_materias}) - {self.periodo.nombre_periodo}"

    class Meta:
        unique_together = ('codigo_grupo', 'periodo')
        verbose_name = "Grupo/Sección"
        verbose_name_plural = "Grupos/Secciones"
        ordering = ['-grupo_id']

class BloquesHorariosDefinicion(models.Model):
    TURNO_CHOICES = [('M', 'Mañana'), ('T', 'Tarde'), ('N', 'Noche')]
    DIA_SEMANA_CHOICES = [
        (1, 'Lunes'), (2, 'Martes'), (3, 'Miércoles'),
        (4, 'Jueves'), (5, 'Viernes'), (6, 'Sábado'), (7, 'Domingo')
    ]

    bloque_def_id = models.AutoField(primary_key=True)
    nombre_bloque = models.CharField(max_length=50) # Ej: Lunes 07:00-09:00
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    turno = models.CharField(max_length=1, choices=TURNO_CHOICES)
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES, null=True, blank=True) # Opcional, si los bloques son genéricos y no por día

    def __str__(self):
        dia_str = dict(self.DIA_SEMANA_CHOICES).get(self.dia_semana, '')
        return f"{self.nombre_bloque} ({dia_str} {self.hora_inicio}-{self.hora_fin})"

    class Meta:
        unique_together = ('nombre_bloque', 'hora_inicio', 'hora_fin', 'turno', 'dia_semana')
        verbose_name = "Bloque Horario (Definición)"
        verbose_name_plural = "Bloques Horarios (Definiciones)"
        ordering = ['dia_semana', 'hora_inicio']


class DisponibilidadDocentes(models.Model):
    DIA_SEMANA_CHOICES = BloquesHorariosDefinicion.DIA_SEMANA_CHOICES
    ORIGEN_CARGA_CHOICES = [('MANUAL', 'Manual'), ('EXCEL', 'Excel')]

    disponibilidad_id = models.AutoField(primary_key=True)
    docente = models.ForeignKey(Docentes, on_delete=models.CASCADE, related_name='disponibilidades')
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE, related_name='disponibilidades_docentes')
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES)
    bloque_horario = models.ForeignKey(BloquesHorariosDefinicion, on_delete=models.CASCADE, related_name='disponibilidades_en_bloque')
    esta_disponible = models.BooleanField(default=True)
    preferencia = models.SmallIntegerField(default=0, help_text="Ej: 0=Neutral, 1=Preferido, -1=No preferido")
    origen_carga = models.CharField(max_length=10, choices=ORIGEN_CARGA_CHOICES, default='MANUAL')

    def __str__(self):
        return f"{self.docente} - {self.periodo} - {dict(self.DIA_SEMANA_CHOICES)[self.dia_semana]} {self.bloque_horario.hora_inicio}-{self.bloque_horario.hora_fin} ({'Disp' if self.esta_disponible else 'No Disp'})"

    class Meta:
        unique_together = ('docente', 'periodo', 'dia_semana', 'bloque_horario')
        verbose_name = "Disponibilidad de Docente"
        verbose_name_plural = "Disponibilidades de Docentes"


class HorariosAsignados(models.Model):
    DIA_SEMANA_CHOICES = BloquesHorariosDefinicion.DIA_SEMANA_CHOICES
    ESTADO_CHOICES = [('Programado', 'Programado'), ('Confirmado', 'Confirmado'), ('Cancelado', 'Cancelado')]

    horario_id = models.AutoField(primary_key=True)
    grupo = models.ForeignKey(Grupos, on_delete=models.CASCADE, related_name='clases_programadas')
    materia = models.ForeignKey(Materias, on_delete=models.CASCADE, related_name='clases_impartidas', null=True)
    docente = models.ForeignKey(Docentes, on_delete=models.CASCADE, related_name='clases_asignadas')
    espacio = models.ForeignKey(EspaciosFisicos, on_delete=models.CASCADE, related_name='horarios_en_espacio')
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE, related_name='horarios_del_periodo') # Denormalizado para facilidad de consulta
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES)
    bloque_horario = models.ForeignKey(BloquesHorariosDefinicion, on_delete=models.CASCADE, related_name='clases_en_bloque')
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='Programado')
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        materia_str = self.materia.codigo_materia if self.materia else "SIN_MATERIA"
        return f"{self.grupo.codigo_grupo} / {materia_str} en {self.espacio} ({dict(self.DIA_SEMANA_CHOICES)[self.dia_semana]} {self.bloque_horario.hora_inicio})"

    class Meta:
        # RD01, RD02: Cruces de horarios
        unique_together = [
            ('docente', 'periodo', 'dia_semana', 'bloque_horario'),
            ('espacio', 'periodo', 'dia_semana', 'bloque_horario'),
            ('grupo', 'periodo', 'dia_semana', 'bloque_horario'), # Un grupo no puede tener dos clases distintas al mismo tiempo
            ('grupo', 'materia', 'periodo', 'dia_semana', 'bloque_horario'), # Una materia de un grupo no se puede programar dos veces en el mismo bloque
        ]
        verbose_name = "Horario Asignado"
        verbose_name_plural = "Horarios Asignados"


class ConfiguracionRestricciones(models.Model):
    TIPO_APLICACION_CHOICES = [
        ('GLOBAL', 'Global'), ('DOCENTE', 'Docente'), ('MATERIA', 'Materia'),
        ('AULA', 'Aula/Espacio'), ('CARRERA', 'Carrera'), ('PERIODO', 'Período')
    ]
    restriccion_id = models.AutoField(primary_key=True)
    codigo_restriccion = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField()
    tipo_aplicacion = models.CharField(max_length=50, choices=TIPO_APLICACION_CHOICES)
    entidad_id_1 = models.IntegerField(blank=True, null=True, help_text="ID del docente, materia, aula, etc.")
    entidad_id_2 = models.IntegerField(blank=True, null=True, help_text="ID secundario para relaciones")
    valor_parametro = models.CharField(max_length=255, blank=True, null=True, help_text="Valor de la restricción")
    periodo_aplicable = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE, null=True, blank=True, related_name='restricciones_configuradas')
    esta_activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo_restriccion}: {self.descripcion}"

    class Meta:
        verbose_name = "Configuración de Restricción"
        verbose_name_plural = "Configuraciones de Restricciones"
