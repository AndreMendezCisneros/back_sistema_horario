from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'grupos', views.GruposViewSet)
router.register(r'bloques-horarios', views.BloquesHorariosDefinicionViewSet)
router.register(r'disponibilidad-docentes', views.DisponibilidadDocentesViewSet)
router.register(r'horarios-asignados', views.HorariosAsignadosViewSet)
router.register(r'configuracion-restricciones', views.ConfiguracionRestriccionesViewSet)
# Para la generación de horarios (no es un ModelViewSet estándar)
router.register(r'acciones-horario', views.GeneracionHorarioView, basename='acciones-horario')


urlpatterns = [
    path('', include(router.urls)),
]
