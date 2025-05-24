from django.contrib.auth.models import User, Group
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import Docentes, Roles # DocenteEspecialidades
from .serializers import UserSerializer, UserRegistrationSerializer, DocentesSerializer, RolesSerializer, GroupSerializer

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenObtainPairSerializer # Asegúrate que esta importación sea correcta

# from ..permissions import IsAdminOrSelf # Permiso personalizado

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #ppermission_classes = [permissions.IsAdminUser] # Solo admins pueden listar/modificar todos los usuarios

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Podrías retornar un token aquí también si quieres login inmediato
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class GroupViewSet(viewsets.ModelViewSet): # Para administrar los grupos de Django
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #ppermission_classes = [permissions.IsAuthenticated]

class RolesViewSet(viewsets.ModelViewSet):
    queryset = Roles.objects.all()
    serializer_class = RolesSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

class DocentesViewSet(viewsets.ModelViewSet):
    queryset = Docentes.objects.select_related('usuario', 'unidad_principal').prefetch_related('especialidades').all()
    serializer_class = DocentesSerializer
    permission_classes = [AllowAny]  #Permite acceso sin autenticación
    #permission_classes = [permissions.IsAuthenticated]

    # Ejemplo de filtrado: /api/users/docentes/?unidad_id=1&especialidad_id=2
    def get_queryset(self):
        queryset = super().get_queryset()
        unidad_id = self.request.query_params.get('unidad_id')
        especialidad_id = self.request.query_params.get('especialidad_id')
        if unidad_id:
            queryset = queryset.filter(unidad_principal_id=unidad_id)
        if especialidad_id:
            queryset = queryset.filter(especialidades__especialidad_id=especialidad_id).distinct()
        return queryset

# Para login y refresh de tokens
class CustomTokenObtainPairView(TokenObtainPairView):
    # Puedes personalizar el serializer aquí si necesitas añadir más datos al token
    serializer_class = MyTokenObtainPairSerializer
    pass

