# apps/academic_setup/models.py
from django.db import models

# Nuevo: Tipo de Unidad Académica (para el campo 'tipo' en Instituciones)
class TipoUnidadAcademica(models.Model):
    tipo_unidad_id = models.AutoField(primary_key=True)
    nombre_tipo = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_tipo

    class Meta:
        verbose_name = "Tipo de Unidad Académica"
        verbose_name_plural = "Tipos de Unidades Académicas"

# Modificado: UnidadAcademica para incluir el Tipo
class UnidadAcademica(models.Model):
    unidad_id = models.AutoField(primary_key=True)
    nombre_unidad = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    # Nuevo campo: Relación con TipoUnidadAcademica
    tipo_unidad = models.ForeignKey(TipoUnidadAcademica, on_delete=models.SET_NULL, null=True, blank=True, related_name='unidades_academicas')

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
    unidad = models.ForeignKey(UnidadAcademica, on_delete=models.PROTECT, related_name='carreras')

    def __str__(self):
        return self.nombre_carrera

    class Meta:
        unique_together = ('nombre_carrera', 'unidad')
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"

# Nuevo: Ciclo (para la jerarquía Carrera -> Ciclo)
class Ciclo(models.Model):
    ciclo_id = models.AutoField(primary_key=True)
    nombre_ciclo = models.CharField(max_length=100) # Ej: "Primer Semestre", "Ciclo 1", "Año 2"
    orden = models.IntegerField(help_text="Orden numérico para los ciclos (ej: 1, 2, 3...)")
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='ciclos')

    def __str__(self):
        return f"{self.carrera.nombre_carrera} - {self.nombre_ciclo}"

    class Meta:
        verbose_name = "Ciclo"
        verbose_name_plural = "Ciclos"
        ordering = ['orden']
        unique_together = ('carrera', 'orden')

# Nuevo: Seccion (para la granularidad de los grupos dentro de un ciclo)
class Seccion(models.Model):
    seccion_id = models.AutoField(primary_key=True)
    nombre_seccion = models.CharField(max_length=100) # Ej: "A", "B", "Grupo 1", "Mañana"
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE, related_name='secciones')
    capacidad = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.ciclo.nombre_ciclo} - {self.nombre_seccion}"

    class Meta:
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        unique_together = ('nombre_seccion', 'ciclo')

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

# Modificado: CarreraMaterias para vincular con Ciclo
class CarreraMaterias(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materias, on_delete=models.CASCADE)
    # Ahora tiene una relación con Ciclo
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE, related_name='materias_carrera_asignadas', null=True, blank=True)
    # Puedes mantener ciclo_sugerido si es solo un número para ordenación, y 'ciclo' es la FK real
    ciclo_sugerido = models.IntegerField(blank=True, null=True, help_text="Número de ciclo sugerido para la materia (1, 2, 3...)")


    class Meta:
        unique_together = ('carrera', 'materia', 'ciclo') # Ahora considera el ciclo también
        verbose_name = "Materia de Carrera"
        verbose_name_plural = "Materias de Carreras"

    def __str__(self):
        return f"{self.carrera.nombre_carrera} - {self.materia.nombre_materia} (Ciclo: {self.ciclo.nombre_ciclo if self.ciclo else 'N/A'})"


class MateriaEspecialidadesRequeridas(models.Model):
    materia = models.ForeignKey(Materias, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidades, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('materia', 'especialidad')
        verbose_name = "Especialidad Requerida por Materia"
        verbose_name_plural = "Especialidades Requeridas por Materias"

    def __str__(self):
        return f"{self.materia.nombre_materia} requiere {self.especialidad.nombre_especialidad}"