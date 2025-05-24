from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'all', views.UserViewSet, basename='user-all') # Para /api/users/all/ y /api/users/all/register/
router.register(r'groups', views.GroupViewSet)
router.register(r'roles', views.RolesViewSet)
router.register(r'docentes', views.DocentesViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # El endpoint /api/users/all/me/ está en UserViewSet
    # El endpoint /api/users/all/register/ está en UserViewSet
]
