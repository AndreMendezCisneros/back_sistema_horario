from rest_framework import viewsets, permissions
from rest_framework.permissions import AllowAny
from .models import UnidadAcademica, Carrera, PeriodoAcademico, TiposEspacio, EspaciosFisicos, Especialidades, Materias, CarreraMaterias, MateriaEspecialidadesRequeridas
from .serializers import (
    UnidadAcademicaSerializer, CarreraSerializer, PeriodoAcademicoSerializer,
    TiposEspacioSerializer, EspaciosFisicosSerializer, EspecialidadesSerializer,
    MateriasSerializer, CarreraMateriasSerializer, MateriaEspecialidadesRequeridasSerializer
)
# from ..permissions import IsAdminOrReadOnly # Ejemplo de permiso personalizado

class UnidadAcademicaViewSet(viewsets.ModelViewSet):
    queryset = UnidadAcademica.objects.all()
    serializer_class = UnidadAcademicaSerializer
    permission_classes = [AllowAny]  # Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

    #permission_classes = [permissions.IsAuthenticated] # Ajustar permisos según rol

class CarreraViewSet(viewsets.ModelViewSet):
    queryset = Carrera.objects.select_related('unidad').all()
    serializer_class = CarreraSerializer
    # Permite acceso sin autenticación
    permission_classes = [AllowAny]
    #permission_classes = [permissions.IsAuthenticated]

class PeriodoAcademicoViewSet(viewsets.ModelViewSet):
    queryset = PeriodoAcademico.objects.all().order_by('-fecha_inicio')
    serializer_class = PeriodoAcademicoSerializer
     # Permite acceso sin autenticación
    permission_classes = [AllowAny]
    #permission_classes = [permissions.IsAuthenticated]

class TiposEspacioViewSet(viewsets.ModelViewSet):
    queryset = TiposEspacio.objects.all()
    serializer_class = TiposEspacioSerializer
    permission_classes = [AllowAny] # Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

class EspaciosFisicosViewSet(viewsets.ModelViewSet):
    queryset = EspaciosFisicos.objects.select_related('tipo_espacio', 'unidad').all()
    serializer_class = EspaciosFisicosSerializer
    permission_classes = [AllowAny]  # Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]
    # Ejemplo de filtrado: /api/academic_setup/espacios-fisicos/?unidad_id=1
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
    permission_classes = [AllowAny]   #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

class MateriasViewSet(viewsets.ModelViewSet):
    queryset = Materias.objects.select_related('requiere_tipo_espacio_especifico').all()
    serializer_class = MateriasSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #ermission_classes = [permissions.IsAuthenticated]

class CarreraMateriasViewSet(viewsets.ModelViewSet):
    queryset = CarreraMaterias.objects.select_related('carrera', 'materia').all()
    serializer_class = CarreraMateriasSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

class MateriaEspecialidadesRequeridasViewSet(viewsets.ModelViewSet):
    queryset = MateriaEspecialidadesRequeridas.objects.select_related('materia', 'especialidad').all()
    serializer_class = MateriaEspecialidadesRequeridasSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

# ... (Vistas para Users y Scheduling de forma similar)
