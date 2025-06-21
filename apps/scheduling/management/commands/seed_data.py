# apps/scheduling/management/commands/seed_data.py

import random
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group # Usaremos el User de Django
from django.utils import timezone
from faker import Faker

# Importa tus modelos (asegúrate que las rutas sean correctas)
from apps.academic_setup.models import (
    UnidadAcademica, Carrera, PeriodoAcademico, TiposEspacio,
    EspaciosFisicos, Especialidades, Materias, CarreraMaterias,
    MateriaEspecialidadesRequeridas
)
from apps.users.models import Roles, Docentes, DocenteEspecialidades
from apps.scheduling.models import (
    Grupos, BloquesHorariosDefinicion, DisponibilidadDocentes,
    ConfiguracionRestricciones, HorariosAsignados
)

fake = Faker(['en_US', 'es_ES']) # Usar localizaciones en español para nombres, etc.

# --- Constantes para la generación ---
NUM_UNIDADES_ACADEMICAS = 2
NUM_CARRERAS_POR_UNIDAD = 3
NUM_PERIODOS = 2
NUM_TIPOS_ESPACIO = 4
NUM_ESPACIOS_POR_TIPO_Y_UNIDAD = 5 # Por cada tipo y unidad
NUM_ESPECIALIDADES = 10
NUM_MATERIAS = 30
NUM_DOCENTES = 20
NUM_GRUPOS_POR_MATERIA_Y_PERIODO = 2
NUM_USUARIOS_ADMIN = 2
DIAS_SEMANA = [1, 2, 3, 4, 5] # Lunes a Viernes
TURNOS_BLOQUES = {
    'M': [time(7, 0), time(9, 0), time(9, 0), time(11, 0), time(11,0), time(13,0)],
    'T': [time(14, 0), time(16, 0), time(16, 0), time(18, 0), time(18,0), time(20,0)],
    'N': [time(19, 0), time(21, 0), time(21,0), time(23,0)] # Ajustado para no superponer con Tarde
}


class Command(BaseCommand):
    help = 'Genera datos de prueba para la aplicación de horarios de La Pontificia'

    def handle(self, *args, **kwargs):
        self.stdout.write("Limpiando datos antiguos (excepto usuarios y grupos base)...")
        # Es importante el orden de limpieza por las dependencias ForeignKey
        HorariosAsignados.objects.all().delete()
        DisponibilidadDocentes.objects.all().delete()
        ConfiguracionRestricciones.objects.all().delete()
        Grupos.objects.all().delete()
        BloquesHorariosDefinicion.objects.all().delete()
        DocenteEspecialidades.objects.all().delete()
        Docentes.objects.all().delete() # No borra los User de Django
        MateriaEspecialidadesRequeridas.objects.all().delete()
        CarreraMaterias.objects.all().delete()
        Materias.objects.all().delete()
        Especialidades.objects.all().delete()
        EspaciosFisicos.objects.all().delete()
        TiposEspacio.objects.all().delete()
        PeriodoAcademico.objects.all().delete()
        Carrera.objects.all().delete()
        UnidadAcademica.objects.all().delete()
        Roles.objects.all().delete() # Borra los roles personalizados

        self.stdout.write("Creando datos base (Roles, Grupos de Django)...")
        self._crear_roles_y_grupos_base()

        self.stdout.write("Generando Unidades Académicas...")
        unidades = self._crear_unidades_academicas()

        self.stdout.write("Generando Carreras...")
        carreras = self._crear_carreras(unidades)

        self.stdout.write("Generando Períodos Académicos...")
        periodos = self._crear_periodos_academicos()

        self.stdout.write("Generando Tipos de Espacio...")
        tipos_espacio = self._crear_tipos_espacio()

        self.stdout.write("Generando Espacios Físicos...")
        espacios = self._crear_espacios_fisicos(tipos_espacio, unidades)

        self.stdout.write("Generando Especialidades...")
        especialidades_doc = self._crear_especialidades()

        self.stdout.write("Generando Materias...")
        materias = self._crear_materias(tipos_espacio, carreras, especialidades_doc)

        self.stdout.write("Generando Docentes y Usuarios (Docente)...")
        docentes = self._crear_docentes_y_usuarios(unidades, especialidades_doc)

        self.stdout.write("Generando Bloques Horarios...")
        bloques = self._crear_bloques_horarios()

        self.stdout.write("Generando Grupos...")
        grupos = self._crear_grupos(materias, carreras, periodos, docentes)

        self.stdout.write("Generando Disponibilidad de Docentes...")
        self._crear_disponibilidad_docentes(docentes, periodos, bloques)

        self.stdout.write("Generando Configuraciones de Restricciones (ejemplos)...")
        self._crear_configuracion_restricciones(docentes, materias, espacios, periodos)

        self.stdout.write("Generando Usuarios Administradores...")
        self._crear_usuarios_admin()


        self.stdout.write(self.style.SUCCESS('¡Datos de prueba generados exitosamente!'))

    def _crear_roles_y_grupos_base(self):
        # Roles personalizados
        Roles.objects.create(nombre_rol='Administrador')
        Roles.objects.create(nombre_rol='Coordinador Académico')
        Roles.objects.create(nombre_rol='Docente')
        Roles.objects.create(nombre_rol='Estudiante')

        # Grupos de Django (puedes mapearlos a tus roles si lo deseas)
        Group.objects.get_or_create(name='Admins')
        Group.objects.get_or_create(name='Coordinadores')
        Group.objects.get_or_create(name='DocentesStaff')

    def _crear_unidades_academicas(self):
        unidades_data = ["Escuela superior la pontificia", "La pontificia", "Instituto de Idiomas"]
        unidades = []
        for i in range(NUM_UNIDADES_ACADEMICAS):
            nombre = unidades_data[i % len(unidades_data)] + (f" {i//len(unidades_data) + 1}" if i >= len(unidades_data) else "")
            ua, _ = UnidadAcademica.objects.get_or_create(
                nombre_unidad=nombre,
                defaults={'descripcion': fake.bs()}
            )
            unidades.append(ua)
        return unidades

    def _crear_carreras(self, unidades_academicas):
        carreras_nombres = ["Ingeniería de Sistemas", "Ingeniería Industrial", "Administración de Empresas", "Contabilidad", "Marketing"]
        carreras = []
        for unidad in unidades_academicas:
            for i in range(NUM_CARRERAS_POR_UNIDAD):
                nombre = random.choice(carreras_nombres) + f" ({unidad.nombre_unidad.split()[0][0:3]})"
                # Asegurar unicidad del nombre de carrera dentro de la unidad
                codigo_carrera_base = "".join(filter(str.isupper, nombre))
                counter = 1
                codigo_carrera = f"{codigo_carrera_base}{counter:02d}"
                while Carrera.objects.filter(codigo_carrera=codigo_carrera).exists():
                    counter +=1
                    codigo_carrera = f"{codigo_carrera_base}{counter:02d}"

                carrera, _ = Carrera.objects.get_or_create(
                    nombre_carrera=nombre,
                    unidad=unidad,
                    defaults={
                        'codigo_carrera': codigo_carrera,
                        'horas_totales_curricula': random.randint(3000, 5000)
                    }
                )
                carreras.append(carrera)
        return carreras

    def _crear_periodos_academicos(self):
        periodos = []
        current_year = timezone.now().year
        for i in range(NUM_PERIODOS):
            year = current_year + (i // 2)
            semestre = "I" if i % 2 == 0 else "II"
            nombre = f"{year}-{semestre}"
            start_month = 3 if semestre == "I" else 8

            p, _ = PeriodoAcademico.objects.get_or_create(
                nombre_periodo=nombre,
                defaults={
                    'fecha_inicio': date(year, start_month, random.randint(1,15)),
                    'fecha_fin': date(year, start_month + 4, random.randint(15,28)),
                    'activo': (i == 0) # El primer periodo como activo
                }
            )
            periodos.append(p)
        return periodos

    def _crear_tipos_espacio(self):
        tipos_data = [
            ("Aula Común", "Aula estándar para clases teóricas."),
            ("Laboratorio de Cómputo", "Sala con computadoras para prácticas."),
            ("Laboratorio de Ciencias", "Laboratorio equipado para experimentos."),
            ("Auditorio", "Sala grande para conferencias o clases magistrales.")
        ]
        tipos = []
        for i in range(NUM_TIPOS_ESPACIO):
            nombre, desc = tipos_data[i % len(tipos_data)]
            te, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio=nombre, defaults={'descripcion': desc})
            tipos.append(te)
        return tipos

    def _crear_espacios_fisicos(self, tipos_espacio, unidades_academicas):
        espacios = []
        for unidad in unidades_academicas:
            for tipo_e in tipos_espacio:
                for i in range(NUM_ESPACIOS_POR_TIPO_Y_UNIDAD):
                    letra_pabellon = chr(ord('A') + random.randint(0, 3))

                    # ---- MODIFICACIÓN PARA HACER numero_aula MÁS ÚNICO ----
                    # Hacemos que numero_aula dependa del ID del tipo de espacio y del índice 'i'
                    # Esto asegura que para diferentes tipos de espacio, los números de aula base serán diferentes.
                    # Y para el mismo tipo, 'i' los diferenciará.
                    # El random.randint(0,9) añade una pequeña variación final.
                    numero_aula = (tipo_e.tipo_espacio_id * 100) + ((i + 1) * 10) + random.randint(0, 9)
                    # ---- FIN DE LA MODIFICACIÓN ----

                    # Usar el primer token del nombre del tipo puede seguir siendo problemático
                    # si diferentes tipos tienen el mismo primer token.
                    # Para mayor robustez, podríamos usar una abreviatura o el nombre completo del tipo.
                    # Por ahora, intentemos con la corrección de numero_aula.
                    # Si sigue fallando, haremos el prefijo del nombre más único.
                    prefijo_nombre_tipo = tipo_e.nombre_tipo_espacio.split()[0]
                    nombre = f"{prefijo_nombre_tipo} {letra_pabellon}-{numero_aula}"

                    esp, created = EspaciosFisicos.objects.get_or_create(
                        nombre_espacio=nombre,
                        unidad=unidad,
                        defaults={
                            'tipo_espacio': tipo_e, # tipo_espacio es parte de los defaults
                            'capacidad': random.choice([20, 30, 40, 50, 100 if tipo_e.nombre_tipo_espacio == "Auditorio" else 30]),
                            'ubicacion': f"Pabellón {letra_pabellon}, Piso {i+1}", # 'i' se reinicia por tipo_e
                            'recursos_adicionales': fake.sentence(nb_words=5) if random.choice([True, False]) else ""
                        }
                    )

                    if not created:
                        # Si no fue creado, significa que ya existía.
                        # Esto es aceptable y get_or_create lo maneja.
                        # El error IntegrityError sugiere que el 'get' falló y el 'create' intentó insertar un duplicado.
                        # La corrección en 'numero_aula' debería evitar que se genere la misma tupla (nombre, unidad)
                        # que lleve a esta condición.
                        pass

                    espacios.append(esp)
        return espacios


    def _crear_especialidades(self):
        nombres_especialidades = [
            "Desarrollo de Software", "Redes y Comunicaciones", "Inteligencia Artificial",
            "Base de Datos", "Gestión de Proyectos TI", "Matemáticas Aplicadas",
            "Física Moderna", "Química Orgánica", "Finanzas Corporativas", "Marketing Digital"
        ]
        especialidades = []
        for i in range(NUM_ESPECIALIDADES):
            nombre = nombres_especialidades[i % len(nombres_especialidades)]
            esp, _ = Especialidades.objects.get_or_create(nombre_especialidad=nombre, defaults={'descripcion': fake.sentence(nb_words=4)})
            especialidades.append(esp)
        return especialidades

    def _crear_materias(self, tipos_espacio, carreras, especialidades_doc):
        nombres_materias = [
            "Programación Orientada a Objetos", "Arquitectura de Software", "Cálculo I", "Física II",
            "Contabilidad de Costos", "Marketing Estratégico", "Algoritmos Avanzados", "Sistemas Operativos"
        ]
        materias = []
        lab_computo = TiposEspacio.objects.filter(nombre_tipo_espacio__icontains="Cómputo").first()
        lab_ciencias = TiposEspacio.objects.filter(nombre_tipo_espacio__icontains="Ciencias").first()

        for i in range(NUM_MATERIAS):
            # Opción 1: Usar una lista de sufijos romanos simples
            sufijos_romanos = ["I", "II", "III", "IV", "V", "VI"]
            nombre = f"{random.choice(nombres_materias)} {random.choice(sufijos_romanos)}"
            #nombre = f"{random.choice(nombres_materias)} {fake.roman_numeral()}"
            codigo = f"MAT{i+1:03d}"

            requiere_espacio = None
            if "Programación" in nombre or "Algoritmos" in nombre or "Sistemas Operativos" in nombre:
                requiere_espacio = lab_computo
            elif "Física" in nombre or "Química" in nombre:
                requiere_espacio = lab_ciencias

            mat, _ = Materias.objects.get_or_create(
                codigo_materia=codigo,
                defaults={
                    'nombre_materia': nombre,
                    'descripcion': fake.sentence(nb_words=6),
                    'horas_academicas_teoricas': random.randint(2, 3),
                    'horas_academicas_practicas': random.randint(1, 2),
                    'horas_academicas_laboratorio': random.randint(0, 2) if requiere_espacio else 0,
                    'requiere_tipo_espacio_especifico': requiere_espacio,
                    'estado': True
                }
            )
            materias.append(mat)

            # Asignar materia a 1 o 2 carreras aleatorias
            for _ in range(random.randint(1,2)):
                carrera_sel = random.choice(carreras)
                CarreraMaterias.objects.get_or_create(carrera=carrera_sel, materia=mat, defaults={'ciclo_sugerido': random.randint(1,10)})

            # Asignar 1 o 2 especialidades requeridas
            for _ in range(random.randint(1,2)):
                MateriaEspecialidadesRequeridas.objects.get_or_create(materia=mat, especialidad=random.choice(especialidades_doc))
        return materias

    def _crear_docentes_y_usuarios(self, unidades, especialidades_doc):
        docentes = []
        grupo_docentes, _ = Group.objects.get_or_create(name='DocentesStaff')
        rol_docente, _ = Roles.objects.get_or_create(nombre_rol='Docente')


        for i in range(NUM_DOCENTES):
            nombre = fake.first_name()
            apellido = fake.last_name()
            username = f"{nombre.lower().split(' ')[0][0:4]}{apellido.lower().split(' ')[0][0:4]}{i:02d}"
            email = f"{username}@{fake.domain_name()}"

            # Crear usuario de Django
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': nombre,
                    'last_name': apellido,
                    'is_active': True # Activamos el usuario por defecto
                }
            )
            if created:
                user.set_password('password123') # Contraseña por defecto
                user.save()
            user.groups.add(grupo_docentes)

            doc, _ = Docentes.objects.get_or_create(
                usuario=user,
                defaults={
                    'codigo_docente': f"DOC{i+1:03d}",
                    'nombres': nombre,
                    'apellidos': apellido,
                    'email': email, # Puede ser el mismo que el del usuario
                    'dni': fake.numerify(text="########"),
                    'telefono': fake.phone_number(),
                    'tipo_contrato': random.choice(["Tiempo Completo", "Tiempo Parcial", "Por Horas"]),
                    'max_horas_semanales': random.randint(10,40),
                    'unidad_principal': random.choice(unidades) if unidades else None,
                }
            )
            docentes.append(doc)

            # Asignar 1 a 3 especialidades al docente
            num_esp_doc = random.randint(1,3)
            espec_asignadas = random.sample(especialidades_doc, min(num_esp_doc, len(especialidades_doc)))
            for esp in espec_asignadas:
                DocenteEspecialidades.objects.get_or_create(docente=doc, especialidad=esp)
        return docentes

    def _crear_bloques_horarios(self):
        bloques = []
        for dia_idx, dia_num in enumerate(DIAS_SEMANA): # Lunes a Viernes
            dia_nombre = BloquesHorariosDefinicion.DIA_SEMANA_CHOICES[dia_idx][1]
            for turno_cod, horas_turno in TURNOS_BLOQUES.items():
                for i in range(0, len(horas_turno), 2):
                    h_inicio = horas_turno[i]
                    h_fin = horas_turno[i+1]
                    nombre = f"{dia_nombre} {h_inicio.strftime('%H:%M')}-{h_fin.strftime('%H:%M')}"

                    bloque, _ = BloquesHorariosDefinicion.objects.get_or_create(
                        nombre_bloque=nombre,
                        dia_semana=dia_num,
                        turno=turno_cod,
                        defaults={
                            'hora_inicio': h_inicio,
                            'hora_fin': h_fin,
                        }
                    )
                    bloques.append(bloque)
        return bloques

    def _crear_grupos(self, materias, carreras, periodos, docentes):
        self.stdout.write(self.style.HTTP_INFO("Generando Grupos y asignando ciclo semestral...")) # Usar HTTP_INFO para logs
        grupos = []
        for periodo in periodos:
            for materia in materias:
                carreras_con_materia = Carrera.objects.filter(carreramaterias__materia=materia).distinct()
                if not carreras_con_materia:
                    continue

                for i in range(NUM_GRUPOS_POR_MATERIA_Y_PERIODO): # Usar la constante que definiste
                    carrera_sel = random.choice(list(carreras_con_materia))

                    # Intentar obtener el ciclo sugerido de CarreraMaterias
                    ciclo_sugerido_val = None
                    try:
                        cm_entry = CarreraMaterias.objects.filter(carrera=carrera_sel, materia=materia).first()
                        if cm_entry and cm_entry.ciclo_sugerido:
                            ciclo_sugerido_val = cm_entry.ciclo_sugerido
                    except CarreraMaterias.DoesNotExist:
                        pass

                    # Fallback si no hay ciclo sugerido en CarreraMaterias
                    if ciclo_sugerido_val is None:
                        # Intenta inferir del código de la materia o asignar aleatoriamente un ciclo plausible
                        # Esta lógica es de ejemplo, ajústala a tus necesidades.
                        if materia.codigo_materia and len(materia.codigo_materia) > 3 and materia.codigo_materia[3].isdigit():
                            try:
                                ciclo_sugerido_val = int(materia.codigo_materia[3])
                                if not (1 <= ciclo_sugerido_val <= 10): # Asegurar que esté en un rango válido
                                    ciclo_sugerido_val = random.randint(1, 10)
                            except ValueError:
                                ciclo_sugerido_val = random.randint(1, 10)
                        else:
                            ciclo_sugerido_val = random.randint(1, 10) # Ciclo aleatorio si no se puede inferir

                    # Asegurar que el código del grupo sea único para el período
                    counter = i + 1
                    cod_grupo_base = f"G{materia.codigo_materia[3:] if len(materia.codigo_materia)>3 else materia.materia_id}{carrera_sel.codigo_carrera[:2]}{periodo.nombre_periodo.replace('-', '')}"
                    cod_grupo = f"{cod_grupo_base}{counter}"
                    while Grupos.objects.filter(codigo_grupo=cod_grupo, periodo=periodo).exists():
                        counter +=1
                        cod_grupo = f"{cod_grupo_base}{counter}"


                    grupo, created = Grupos.objects.get_or_create(
                        codigo_grupo=cod_grupo,
                        periodo=periodo,
                        carrera=carrera_sel,
                        defaults={
                            'ciclo_semestral': ciclo_sugerido_val,
                            'numero_estudiantes_estimado': random.randint(15, 40),
                            'turno_preferente': random.choice(['M', 'T', 'N', None]),
                            'docente_asignado_directamente': random.choice(docentes) if random.random() < 0.1 else None
                        }
                    )

                    # Asignar la materia después de crear el grupo
                    if created:
                        grupo.materias.set([materia])
                        grupos.append(grupo)
                    else:
                        if grupo.ciclo_semestral != ciclo_sugerido_val:
                            grupo.ciclo_semestral = ciclo_sugerido_val
                            grupo.save()
                        # Asegurarse de que la materia esté asignada incluso si el grupo ya existía
                        grupo.materias.add(materia)
                        grupos.append(grupo)

        self.stdout.write(self.style.SUCCESS(f"Se generaron/actualizaron {len(grupos)} grupos."))
        return grupos

    def _crear_disponibilidad_docentes(self, docentes, periodos, bloques_horarios):
        for docente in docentes:
            for periodo in periodos:
                for bloque in bloques_horarios:
                    # 70% de probabilidad de estar disponible en un bloque
                    if random.random() < 0.7:
                        DisponibilidadDocentes.objects.get_or_create(
                            docente=docente,
                            periodo=periodo,
                            dia_semana=bloque.dia_semana,
                            bloque_horario=bloque,
                            defaults={
                                'esta_disponible': True,
                                'preferencia': random.choice([0, 0, 0, 1, -1]) # Más neutral
                            }
                        )
                    # else: No disponible (se asume por defecto o puedes crear un registro con esta_disponible=False)

    def _crear_configuracion_restricciones(self, docentes, materias, espacios, periodos):
        if docentes:
            docente_ejemplo = random.choice(docentes)
            ConfiguracionRestricciones.objects.get_or_create(
                codigo_restriccion=f"MAX_HORAS_DIA_{docente_ejemplo.codigo_docente}",
                defaults={
                    'descripcion': f"Docente {docente_ejemplo} no puede exceder 5 horas al día.",
                    'tipo_aplicacion': "DOCENTE",
                    'entidad_id_1': docente_ejemplo.pk,
                    'valor_parametro': "5",
                    'esta_activa': True
                }
            )

        if materias and espacios:
            materia_ejemplo = random.choice(materias)
            espacio_ejemplo = random.choice(espacios)
            if materia_ejemplo.requiere_tipo_espacio_especifico and espacio_ejemplo.tipo_espacio == materia_ejemplo.requiere_tipo_espacio_especifico :
                ConfiguracionRestricciones.objects.get_or_create(
                    codigo_restriccion=f"ASIGNAR_{materia_ejemplo.codigo_materia}_A_{espacio_ejemplo.nombre_espacio.replace(' ','_')}",
                    defaults={
                        'descripcion': f"Materia {materia_ejemplo.nombre_materia} debe usar el espacio {espacio_ejemplo.nombre_espacio}.",
                        'tipo_aplicacion': "MATERIA",
                        'entidad_id_1': materia_ejemplo.pk,
                        'valor_parametro': str(espacio_ejemplo.pk), # ID del espacio
                        'esta_activa': True
                    }
                )

        ConfiguracionRestricciones.objects.get_or_create(
            codigo_restriccion="NO_CLASES_DOMINGO",
            defaults={
                'descripcion': "No se programan clases los domingos.",
                'tipo_aplicacion': "GLOBAL",
                'valor_parametro': "DIA_7_BLOQUEADO", # El generador debe interpretar esto
                'esta_activa': True
            }
        )

    def _crear_usuarios_admin(self):
        admin_group, _ = Group.objects.get_or_create(name='Admins')
        admin_rol, _ = Roles.objects.get_or_create(nombre_rol='Administrador')

        for i in range(NUM_USUARIOS_ADMIN):
            username = f'adminuser{i+1}'
            email = f'admin{i+1}@example.com'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': 'Admin',
                    'last_name': f'User{i+1}',
                    'is_staff': True,
                    'is_superuser': True # Para que pueda acceder a todo en el admin de Django
                }
            )
            if created:
                user.set_password('adminpass123')
                user.save()
            user.groups.add(admin_group)

# Agrega esto arriba en tu archivo
def int_to_roman(input):
    if not isinstance(input, int):
        raise TypeError("expected integer")
    if not 0 < input < 4000:
        raise ValueError("Argument must be between 1 and 3999")
    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ("M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I")
    result = []
    for i in range(len(ints)):
        count = int(input / ints[i])
        result.append(nums[i] * count)
        input -= ints[i] * count
    return ''.join(result)
