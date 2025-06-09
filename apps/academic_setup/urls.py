# apps/academic_setup/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'unidades-academicas', views.UnidadAcademicaViewSet)
router.register(r'carreras', views.CarreraViewSet)
router.register(r'periodos-academicos', views.PeriodoAcademicoViewSet)
router.register(r'tipos-espacio', views.TiposEspacioViewSet)
router.register(r'espacios-fisicos', views.EspaciosFisicosViewSet)
router.register(r'especialidades', views.EspecialidadesViewSet)
router.register(r'materias', views.MateriasViewSet)
router.register(r'carrera-materias', views.CarreraMateriasViewSet)
router.register(r'materia-especialidades-requeridas', views.MateriaEspecialidadesRequeridasViewSet)
# Nuevas rutas para los modelos adicionales
router.register(r'tipos-unidad-academica', views.TipoUnidadAcademicaViewSet)
router.register(r'ciclos', views.CicloViewSet)
router.register(r'secciones', views.SeccionViewSet)


urlpatterns = [
    path('', include(router.urls)),
]