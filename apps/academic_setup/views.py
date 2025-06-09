# apps/academic_setup/views.py
from rest_framework import viewsets, permissions
from rest_framework.permissions import AllowAny
from .models import (
    UnidadAcademica, Carrera, PeriodoAcademico, TiposEspacio, EspaciosFisicos,
    Especialidades, Materias, CarreraMaterias, MateriaEspecialidadesRequeridas,
    TipoUnidadAcademica, Ciclo, Seccion # Importar los nuevos modelos
)
from .serializers import (
    UnidadAcademicaSerializer, CarreraSerializer, PeriodoAcademicoSerializer,
    TiposEspacioSerializer, EspaciosFisicosSerializer, EspecialidadesSerializer,
    MateriasSerializer, CarreraMateriasSerializer, MateriaEspecialidadesRequeridasSerializer,
    TipoUnidadAcademicaSerializer, CicloSerializer, SeccionSerializer # Importar los nuevos serializadores
)

# Nuevo ViewSet para TipoUnidadAcademica
class TipoUnidadAcademicaViewSet(viewsets.ModelViewSet):
    queryset = TipoUnidadAcademica.objects.all()
    serializer_class = TipoUnidadAcademicaSerializer
    permission_classes = [AllowAny] # Ajusta los permisos según tu sistema de autenticación

# Modificado: UnidadAcademicaViewSet para incluir el tipo_unidad
class UnidadAcademicaViewSet(viewsets.ModelViewSet):
    queryset = UnidadAcademica.objects.select_related('tipo_unidad').all()
    serializer_class = UnidadAcademicaSerializer
    permission_classes = [AllowAny] # Ajusta los permisos

# Nuevo ViewSet para Ciclo
class CicloViewSet(viewsets.ModelViewSet):
    queryset = Ciclo.objects.select_related('carrera').all()
    serializer_class = CicloSerializer
    permission_classes = [AllowAny] # Ajusta los permisos

    # Permite filtrar ciclos por carrera_id: /api/academic_setup/ciclos/?carrera_id=X
    def get_queryset(self):
        queryset = super().get_queryset()
        carrera_id = self.request.query_params.get('carrera_id')
        if carrera_id:
            queryset = queryset.filter(carrera_id=carrera_id)
        return queryset

# Nuevo ViewSet para Seccion
class SeccionViewSet(viewsets.ModelViewSet):
    # Utilizamos '__' para acceder a campos de modelos relacionados (ciclo y carrera a través del ciclo)
    queryset = Seccion.objects.select_related('ciclo__carrera').all()
    serializer_class = SeccionSerializer
    permission_classes = [AllowAny] # Ajusta los permisos

    # Permite filtrar secciones por ciclo_id o carrera_id:
    # /api/academic_setup/secciones/?ciclo_id=X
    # /api/academic_setup/secciones/?carrera_id=Y
    def get_queryset(self):
        queryset = super().get_queryset()
        ciclo_id = self.request.query_params.get('ciclo_id')
        carrera_id = self.request.query_params.get('carrera_id')
        if ciclo_id:
            queryset = queryset.filter(ciclo_id=ciclo_id)
        if carrera_id:
            queryset = queryset.filter(ciclo__carrera_id=carrera_id)
        return queryset

# Modificado: CarreraMateriasViewSet (si ajustaste el modelo CarreraMaterias)
class CarreraMateriasViewSet(viewsets.ModelViewSet):
    # Asegúrate de incluir 'ciclo' en el select_related si lo añadiste a CarreraMaterias
    queryset = CarreraMaterias.objects.select_related('carrera', 'materia', 'ciclo').all()
    serializer_class = CarreraMateriasSerializer
    permission_classes = [AllowAny] # Ajusta los permisos

    # Opcional: Filtrar por carrera, materia o ciclo
    def get_queryset(self):
        queryset = super().get_queryset()
        carrera_id = self.request.query_params.get('carrera_id')
        materia_id = self.request.query_params.get('materia_id')
        ciclo_id = self.request.query_params.get('ciclo_id')
        if carrera_id:
            queryset = queryset.filter(carrera_id=carrera_id)
        if materia_id:
            queryset = queryset.filter(materia_id=materia_id)
        if ciclo_id:
            queryset = queryset.filter(ciclo_id=ciclo_id)
        return queryset

# Los ViewSets existentes (sin cambios en la lógica, solo para completitud)
class CarreraViewSet(viewsets.ModelViewSet):
    queryset = Carrera.objects.select_related('unidad').all()
    serializer_class = CarreraSerializer
    permission_classes = [AllowAny]

class PeriodoAcademicoViewSet(viewsets.ModelViewSet):
    queryset = PeriodoAcademico.objects.all().order_by('-fecha_inicio')
    serializer_class = PeriodoAcademicoSerializer
    permission_classes = [AllowAny]

class TiposEspacioViewSet(viewsets.ModelViewSet):
    queryset = TiposEspacio.objects.all()
    serializer_class = TiposEspacioSerializer
    permission_classes = [AllowAny]

class EspaciosFisicosViewSet(viewsets.ModelViewSet):
    queryset = EspaciosFisicos.objects.select_related('tipo_espacio', 'unidad').all()
    serializer_class = EspaciosFisicosSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        queryset = super().get_queryset()
        unidad_id = self.request.query_params.get('unidad_id')
        tipo_espacio_id = self.request.query_params.get('tipo_espacio_id')
        if unidad_id:
            queryset = queryset.filter(unidad_id=unidad_id)
        if tipo_espacio_id:
            queryset = queryset.filter(tipo_espacio_id=tipo_espacio_id)
        return queryset


class EspecialidadesViewSet(viewsets.ModelViewSet):
    queryset = Especialidades.objects.all()
    serializer_class = EspecialidadesSerializer
    permission_classes = [AllowAny]

class MateriasViewSet(viewsets.ModelViewSet):
    queryset = Materias.objects.select_related('requiere_tipo_espacio_especifico').all()
    serializer_class = MateriasSerializer
    permission_classes = [AllowAny]

class MateriaEspecialidadesRequeridasViewSet(viewsets.ModelViewSet):
    queryset = MateriaEspecialidadesRequeridas.objects.select_related('materia', 'especialidad').all()
    serializer_class = MateriaEspecialidadesRequeridasSerializer
    permission_classes = [AllowAny]