from django.db import models

class UnidadAcademica(models.Model):
    unidad_id = models.AutoField(primary_key=True)
    nombre_unidad = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_unidad

    class Meta:
        verbose_name = "Unidad Académica"
        verbose_name_plural = "Unidades Académicas"

class Carrera(models.Model):
    carrera_id = models.AutoField(primary_key=True)
    nombre_carrera = models.CharField(max_length=255)
    codigo_carrera = models.CharField(max_length=20, unique=True, blank=True, null=True)
    horas_totales_curricula = models.IntegerField(blank=True, null=True)
    unidad = models.ForeignKey(UnidadAcademica, on_delete=models.CASCADE, related_name='carreras')

    def __str__(self):
        return self.nombre_carrera

    class Meta:
        unique_together = ('nombre_carrera', 'unidad')
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"

class PeriodoAcademico(models.Model):
    periodo_id = models.AutoField(primary_key=True)
    nombre_periodo = models.CharField(max_length=50, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_periodo

    class Meta:
        verbose_name = "Período Académico"
        verbose_name_plural = "Períodos Académicos"
        ordering = ['-fecha_inicio', 'nombre_periodo']

class TiposEspacio(models.Model):
    tipo_espacio_id = models.AutoField(primary_key=True)
    nombre_tipo_espacio = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_tipo_espacio

    class Meta:
        verbose_name = "Tipo de Espacio"
        verbose_name_plural = "Tipos de Espacios"

class EspaciosFisicos(models.Model):
    espacio_id = models.AutoField(primary_key=True)
    nombre_espacio = models.CharField(max_length=100)
    tipo_espacio = models.ForeignKey(TiposEspacio, on_delete=models.RESTRICT, related_name='espacios')
    capacidad = models.IntegerField(blank=True, null=True)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    recursos_adicionales = models.TextField(blank=True, null=True)
    unidad = models.ForeignKey(UnidadAcademica, on_delete=models.SET_NULL, null=True, blank=True, related_name='espacios_fisicos')

    def __str__(self):
        return f"{self.nombre_espacio} ({self.tipo_espacio.nombre_tipo_espacio})"

    class Meta:
        unique_together = ('nombre_espacio', 'unidad')
        verbose_name = "Espacio Físico"
        verbose_name_plural = "Espacios Físicos"

class Especialidades(models.Model):
    especialidad_id = models.AutoField(primary_key=True)
    nombre_especialidad = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_especialidad

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"


class Materias(models.Model):
    materia_id = models.AutoField(primary_key=True)
    codigo_materia = models.CharField(max_length=50, unique=True)
    nombre_materia = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    horas_academicas_teoricas = models.IntegerField(default=0)
    horas_academicas_practicas = models.IntegerField(default=0)
    horas_academicas_laboratorio = models.IntegerField(default=0)
    requiere_tipo_espacio_especifico = models.ForeignKey(TiposEspacio, on_delete=models.SET_NULL, null=True, blank=True, related_name='materias_requeridas')
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo_materia} - {self.nombre_materia}"

    @property
    def horas_totales(self):
        return self.horas_academicas_teoricas + self.horas_academicas_practicas + self.horas_academicas_laboratorio

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"

class CarreraMaterias(models.Model):
    # carrera_materia_id = models.AutoField(primary_key=True) # Opcional si prefieres ID explícito
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materias, on_delete=models.CASCADE)
    ciclo_sugerido = models.IntegerField(blank=True, null=True)

    class Meta:
        unique_together = ('carrera', 'materia')
        verbose_name = "Materia de Carrera"
        verbose_name_plural = "Materias de Carreras"

    def __str__(self):
        return f"{self.carrera.nombre_carrera} - {self.materia.nombre_materia}"


class MateriaEspecialidadesRequeridas(models.Model):
    materia = models.ForeignKey(Materias, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidades, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('materia', 'especialidad')
        verbose_name = "Especialidad Requerida por Materia"
        verbose_name_plural = "Especialidades Requeridas por Materias"

    def __str__(self):
        return f"{self.materia.nombre_materia} requiere {self.especialidad.nombre_especialidad}"
