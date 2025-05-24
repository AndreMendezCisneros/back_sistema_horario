from django.contrib.auth.models import User, Group
from rest_framework import serializers
from .models import Docentes, Roles, DocenteEspecialidades # SesionesUsuario
from apps.academic_setup.serializers import EspecialidadesSerializer # Para anidar
from apps.users.models import Especialidades
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class GroupSerializer(serializers.ModelSerializer): # Para los grupos de Django
    class Meta:
        model = Group
        fields = ('id', 'name')

class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True) # Muestra los grupos del usuario
    # perfil_docente_id = serializers.IntegerField(source='perfil_docente.docente_id', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'groups') #, 'perfil_docente_id')
        read_only_fields = ('is_staff', 'is_active', 'groups')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Este correo electrónico ya está en uso."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        # Aquí podrías asignar un rol/grupo por defecto
        # default_group = Group.objects.get(name='NombreDelGrupoPorDefecto')
        # user.groups.add(default_group)
        return user

class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = '__all__'

class DocenteEspecialidadesSimpleSerializer(serializers.ModelSerializer): # Para la lista dentro de Docente
    especialidad_id = serializers.IntegerField(source='especialidad.especialidad_id')
    nombre_especialidad = serializers.CharField(source='especialidad.nombre_especialidad', read_only=True)

    class Meta:
        model = DocenteEspecialidades
        fields = ['especialidad_id', 'nombre_especialidad']


class DocentesSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True, allow_null=True)
    unidad_principal_nombre = serializers.CharField(source='unidad_principal.nombre_unidad', read_only=True, allow_null=True)
    # Mostrar especialidades de forma más detallada o simple
    especialidades_detalle = EspecialidadesSerializer(source='especialidades', many=True, read_only=True) # ManyToManyField
    # Para la creación/actualización de especialidades, podríamos necesitar un campo write_only
    especialidad_ids = serializers.PrimaryKeyRelatedField(
        queryset=Especialidades.objects.all(),
        source='especialidades',
        many=True,
        write_only=True,
        required=False
    )


    class Meta:
        model = Docentes
        fields = ['docente_id', 'usuario', 'usuario_username', 'codigo_docente', 'nombres', 'apellidos', 'dni',
                  'email', 'telefono', 'tipo_contrato', 'max_horas_semanales',
                  'unidad_principal', 'unidad_principal_nombre', 'especialidades_detalle', 'especialidad_ids']

    def create(self, validated_data):
        especialidad_data = validated_data.pop('especialidades', None)
        docente = Docentes.objects.create(**validated_data)
        if especialidad_data:
            docente.especialidades.set(especialidad_data)
        return docente

    def update(self, instance, validated_data):
        especialidad_data = validated_data.pop('especialidades', None)
        instance = super().update(instance, validated_data)
        if especialidad_data is not None: # Permite limpiar especialidades si se envía lista vacía
            instance.especialidades.set(especialidad_data)
        return instance

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Puedes añadir claims personalizados al payload del token de acceso aquí si lo deseas
        # Estos datos estarían DENTRO del token JWT decodificado.
        # token['username'] = user.username
        # token['custom_claim'] = 'valor_personalizado'
        return token

    def validate(self, attrs):
        # La llamada a super().validate(attrs) ya te da los tokens 'access' y 'refresh'
        data = super().validate(attrs)

        # Ahora, añadimos la información extra del usuario a la respuesta JSON
        # que se enviará JUNTO con los tokens.
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['first_name'] = self.user.first_name
        data['last_name'] = self.user.last_name
        data['is_staff'] = self.user.is_staff # Útil si los coordinadores son staff pero no superusers
        data['is_superuser'] = self.user.is_superuser # Para el rol de Administrador principal

        # Obtenemos los nombres de los grupos de Django a los que pertenece el usuario
        # Estos grupos los creamos en el `seed_data.py` (ej: 'Admins', 'Coordinadores', 'DocentesStaff')
        user_groups = self.user.groups.all().values_list('name', flat=True)
        data['groups'] = list(user_groups)

        # Si tuvieras un campo 'rol' FK directo en tu modelo User personalizado (no es el caso ahora):
        # if hasattr(self.user, 'rol') and self.user.rol:
        #     data['custom_rol_id'] = self.user.rol.rol_id
        #     data['custom_rol_nombre'] = self.user.rol.nombre_rol

        # Si el usuario es un docente y quieres info específica del perfil Docente:
        if hasattr(self.user, 'perfil_docente') and self.user.perfil_docente:
            data['docente_id'] = self.user.perfil_docente.docente_id
            data['codigo_docente'] = self.user.perfil_docente.codigo_docente
            # Puedes añadir más campos del perfil Docente si son necesarios en el login.

        return data
