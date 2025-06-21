import re
from django.core.management.base import BaseCommand
from django.db import transaction
import datetime

# Importar todos los modelos necesarios de ambas aplicaciones
from apps.academic_setup.models import (
    UnidadAcademica, TipoUnidadAcademica, Carrera, Ciclo, Seccion,
    PeriodoAcademico, TiposEspacio, EspaciosFisicos, Materias, CarreraMaterias
)
from apps.scheduling.models import Grupos, HorariosAsignados
from apps.users.models import Docentes
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Siembra la base de datos con los planes de estudio y datos de ejemplo personalizados.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Iniciando siembra de datos del plan de estudios ---"))

        self._limpiar_datos_previos()
        unidades = self._crear_unidades_academicas()
        tipos_espacio = self._crear_tipos_espacio()
        self._crear_espacios_fisicos(tipos_espacio, unidades)
        periodo = self._crear_periodo_academico()
        
        planes_de_estudio_texto = """Carrera: ADMINISTRACIÓN DE EMPRESAS
Código de Plan de Estudio: 20241
Total Créditos: 200
Ciclo	Código	Materia	H TEO	H PRA
1	EAE24-001	Administración General	48	32
1	EAE24-002	Matemática para los Negocios	48	32
1	EAE24-003	Introducción a la Contabilidad	48	32
1	ETR24-001	Intercomunicación Inicial	48	32
1	ETR24-002	Ofimática Inicial	48	32
2	EAE24-004	Fundamentos de Marketing	48	32
2	EAE24-005	Matemática Financiera	48	32
2	EAE24-006	Contabilidad General	48	32
2	ETR24-003	Intercomunicación Avanzada	48	32
2	ETR24-004	Ofimática Avanzada	48	32
3	EAE24-007	Fundamentos de Finanzas	48	32
3	EAE24-008	Investigación de Mercados	48	32
3	EAE24-009	Derecho Empresarial	48	32
3	EAE24-010	Estadística General	48	32
3	ETR24-005	Psicología Organizacional	32	32
3	ETR24-010	Introducción a la Ética	32	32
4	EAE24-011	Elaboración de Procesos	48	32
4	EAE24-012	Costos y Presupuestos	48	32
4	EAE24-013	Análisis Cuantitativo para los Negocios	48	32
4	EAE24-014	Estadística para los Negocios	48	32
4	ETR24-006	Autorealización Personal	32	32
4	ETR24-011	Ética Profesional	32	32
5	EAE24-015	Derecho Laboral	48	32
5	EAE24-016	Finanzas Empresariales	48	32
5	EAE24-017	Administración de Operaciones	48	32
5	ETR24-007	Atención al usuario	48	32
5	ETR24-012	Didáctica del Razonamiento	32	32
5	ETR24-020	Experiencia Formativa en Situación Real de Trabajo I	0	96
6	EAE24-018	Talento Humano	48	32
6	EAE24-019	Gestión de la Calidad	48	32
6	EAE24-020	Contabilidad Gerencial	48	32
6	ETR24-008	Sistema de medición de la atención al usuario	48	32
6	ETR24-013	Análisis de Situaciones Reales	32	32
6	ETR24-021	Experiencia Formativa en Situación Real de Trabajo II	0	96
7	EAE24-021	Administración Estratégica	48	32
7	EAE24-022	Evaluación y Gestión de Proyectos	48	32
7	EAE24-023	Cadena de suministro	48	32
7	ETR24-014	Introducción a la Innovación	32	32
7	ETR24-019	Desarrollo Emprendedor	48	32
7	ETR24-022	Experiencia Formativa en Situación Real de Trabajo III	0	96
8	EAE24-024	Estrategia Comercial	48	32
8	EAE24-025	Micro y Pequeña Empresa	48	32
8	ETR24-009	Plan de Negocios	48	32
8	ETR24-015	Innovación en productos y servicios	32	32
8	ETR24-023	Experiencia Formativa en Situación Real de Trabajo IV	0	96
9	EAE24-026	Marketing Estratégico	48	32
9	EAE24-027	Administración Pública	48	32
9	EAE24-028	E-business y Transformación Digital en las Empresas	48	32
9	ETR24-024	Experiencia Formativa en Situación Real de Trabajo V	0	96
10	ETR24-016	Fundamentos de Investigación Aplicada	48	32
10	ETR24-017	Técnicas de Investigación Aplicada	48	32
10	ETR24-018	Seminario de Tesis	80	32
10	ETR24-025	Experiencia Formativa en Situación Real de Trabajo VI	0	96

Carrera: CONTABILIDAD Y FINANZAS
Código de Plan de Estudio: 20241
Total Créditos: 200
Ciclo	Código	Materia	H TEO	H PRA
1	ECF24-001	Introducción a la Contabilidad	48	32
1	ECF24-002	Matemática para los Negocios	48	32
1	ECF24-003	Introducción al Sistema Tributario	48	32
1	ETR24-001	Intercomunicación Inicial	48	32
1	ETR24-002	Ofimática Inicial	48	32
2	ECF24-004	Registros y Operaciones Contables	48	32
2	ECF24-005	Matemática Financiera	48	32
2	ECF24-006	Fundamentos de Finanzas	48	32
2	ETR24-003	Intercomunicación Avanzada	48	32
2	ETR24-004	Ofimática Avanzada	48	32
3	ECF24-007	Contabilidad de Sociedades	48	32
3	ECF24-008	Sistema Tributario	48	32
3	ECF24-009	Registro de Planillas	48	32
3	ECF24-010	Finanzas Empresariales	48	32
3	ETR24-005	Psicología Organizacional	32	32
3	ETR24-010	Introducción a la Ética	32	32
4	ECF24-011	Contabilidad de Costos	48	32
4	ECF24-012	Derecho Tributario	48	32
4	ECF24-013	Derecho Comercial	48	32
4	ECF24-014	Declaraciones Juradas Mensuales	48	32
4	ETR24-006	Autorealización Personal	32	32
4	ETR24-011	Ética Profesional	32	32
5	ECF24-015	Análisis de Reportes Contables	48	32
5	ECF24-016	Contabilidad de MYPES	48	32
5	ECF24-017	Contabilidad Financiera	48	32
5	ETR24-007	Atención al usuario	48	32
5	ETR24-012	Didáctica del Razonamiento	32	32
5	ETR24-020	Experiencia Formativa en Situación Real de Trabajo I	0	96
6	ECF24-018	Evaluación financiera de proyectos	48	32
6	ECF24-019	Contabilidad de Costos Avanzada	48	32
6	ECF24-020	Elaboración de Estados Financieros	48	32
6	ECF24-021	Introducción a la Contabilidad Pública	48	32
6	ETR24-013	Análisis de Situaciones Reales	32	32
6	ETR24-021	Experiencia Formativa en Situación Real de Trabajo II	0	96
7	ECF24-022	Aplicación de las Normas Internacionales de Contabilidad	48	32
7	ECF24-023	Contabilidad Pública	48	32
7	ECF24-024	Auditoría y Control Interno	48	32
7	ETR24-008	Sistema de medición de la atención al usuario	48	32
7	ETR24-014	Introducción a la Innovación	32	32
7	ETR24-022	Experiencia Formativa en Situación Real de Trabajo III	0	96
8	ECF24-025	Análisis de Riesgos	48	32
8	ECF24-026	Valorización de Empresas	32	32
8	ECF24-027	Auditoría Tributaria	32	32
8	ETR24-015	Innovación en productos y servicios	32	32
8	ETR24-023	Experiencia Formativa en Situación Real de Trabajo IV	0	96
9	ECF24-028	Portafolio de Inversiones	16	32
9	ECF24-029	Planificación Financiera	16	32
9	ECF24-030	Contabilidad Gerencial	16	32
9	ETR24-009	Plan de Negocios	48	32
9	ETR24-019	Desarrollo Emprendedor	48	32
9	ETR24-024	Experiencia Formativa en Situación Real de Trabajo V	0	96
10	ETR24-016	Fundamentos de Investigación Aplicada	48	32
10	ETR24-017	Técnicas de Investigación Aplicada	48	32
10	ETR24-018	Seminario de Tesis	80	32
10	ETR24-025	Experiencia Formativa en Situación Real de Trabajo VI	0	96

Carrera: INGENIERÍA DE SISTEMAS DE INFORMACIÓN
Código de Plan de Estudio: 20241
Total Créditos: 200
Ciclo	Código	Materia	H TEO	H PRA
1	EIS24-001	Arquitectura Web	48	32
1	EIS24-002	Introducción a la Programación	48	32
1	EIS24-003	Matemática Aplicada	48	32
1	ETR24-001	Intercomunicación Inicial	48	32
1	ETR24-002	Ofimática Inicial	48	32
2	EIS24-004	Fundamentos de Algoritmia	48	32
2	EIS24-005	Configuración de Aplicaciones	48	32
2	EIS24-006	Introducción al Modelamiento de Procesos	48	32
2	ETR24-003	Intercomunicación Avanzada	48	32
2	ETR24-004	Ofimática Avanzada	48	32
3	EIS24-007	Fundamentos de Estructura de Datos	48	32
3	EIS24-008	Estadística Aplicada	48	32
3	EIS24-009	Diseño de Sistemas en TI	48	32
3	EIS24-010	Modelado de procesos en TI	48	32
3	ETR24-005	Psicología Organizacional	32	32
3	ETR24-010	Introducción a la Ética	32	32
4	EIS24-011	Cyberseguridad	48	32
4	EIS24-012	Gestión de Servicios en TI	48	32
4	EIS24-013	Lenguaje de Programación	48	32
4	EIS24-014	Programación orientada a Objetos	48	32
4	ETR24-006	Autorealización Personal	32	32
4	ETR24-011	Ética Profesional	32	32
5	EIS24-015	Arquitectura de sistemas operativos	48	32
5	EIS24-016	Programación de aplicaciones web	48	32
5	EIS24-017	Sistemas Distribuidos	48	32
5	ETR24-007	Atención al usuario	48	32
5	ETR24-012	Didáctica del Razonamiento	32	32
5	ETR24-020	Experiencia Formativa en Situación Real de Trabajo I	0	96
6	EIS24-018	Soluciones móviles y cloud	48	32
6	EIS24-019	Gestión de Proyectos en TI	48	32
6	EIS24-020	Legislación en sistemas de información	48	32
6	ETR24-013	Análisis de Situaciones Reales	32	32
6	ETR24-021	Experiencia Formativa en Situación Real de Trabajo II	0	96
7	EIS24-021	Arquitectura de software	48	32
7	EIS24-022	Modelamiento de base de datos	48	32
7	EIS24-023	Validación y pruebas de software	48	32
7	ETR24-008	Sistema de medición de la atención al usuario	48	32
7	ETR24-014	Introducción a la Innovación	32	32
7	ETR24-022	Experiencia Formativa en Situación Real de Trabajo III	0	96
8	EIS24-024	Auditoría de sistemas	48	32
8	EIS24-025	Analítica con Big Data	48	32
8	EIS24-026	Inteligencia artificial	48	32
8	ETR24-015	Innovación en productos y servicios	32	32
8	ETR24-023	Experiencia Formativa en Situación Real de Trabajo IV	0	96
9	EIS24-027	Bases de datos	48	32
9	EIS24-028	Proyectos en TI	48	32
9	ETR24-009	Plan de Negocios	48	32
9	ETR24-019	Desarrollo Emprendedor	48	32
9	ETR24-024	Experiencia Formativa en Situación Real de Trabajo V	0	96
10	ETR24-016	Fundamentos de Investigación Aplicada	48	32
10	ETR24-017	Técnicas de Investigación Aplicada	48	32
10	ETR24-018	Seminario de Tesis	80	32
10	ETR24-025	Experiencia Formativa en Situación Real de Trabajo VI	0	96
"""

        self._procesar_planes_de_estudio(planes_de_estudio_texto, unidades)
        self._crear_grupos_de_ejemplo(periodo)
        self._crear_docentes_de_ejemplo()

        self.stdout.write(self.style.SUCCESS("--- Siembra de datos completada exitosamente. ---"))

    def _limpiar_datos_previos(self):
        self.stdout.write("Limpiando datos existentes...")
        HorariosAsignados.objects.all().delete()
        Grupos.objects.all().delete()
        CarreraMaterias.objects.all().delete()
        Materias.objects.all().delete()
        Ciclo.objects.all().delete()
        Carrera.objects.all().delete()
        EspaciosFisicos.objects.all().delete()
        TiposEspacio.objects.all().delete()
        Docentes.objects.all().delete()
        UnidadAcademica.objects.all().delete()
        TipoUnidadAcademica.objects.all().delete()
        PeriodoAcademico.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Datos previos eliminados."))

    def _crear_unidades_academicas(self):
        self.stdout.write("Creando Unidades Académicas...")
        tipo_facultad, _ = TipoUnidadAcademica.objects.get_or_create(nombre_tipo="Facultad")
        
        ua_empresas, _ = UnidadAcademica.objects.get_or_create(
            nombre_unidad="Facultad de Ciencias Empresariales",
            defaults={'tipo_unidad': tipo_facultad}
        )
        ua_ingenieria, _ = UnidadAcademica.objects.get_or_create(
            nombre_unidad="Facultad de Ingeniería",
            defaults={'tipo_unidad': tipo_facultad}
        )
        return {'empresas': ua_empresas, 'ingenieria': ua_ingenieria}

    def _crear_tipos_espacio(self):
        self.stdout.write("Creando Tipos de Espacio...")
        teoria, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio="Aula de Teoría")
        lab, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio="Laboratorio")
        salon_c, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio="Salón de Usos Múltiples")
        return {'teoria': teoria, 'laboratorio': lab, 'salon_c': salon_c}

    def _crear_espacios_fisicos(self, tipos_espacio, unidades):
        self.stdout.write("Creando Espacios Físicos (Aulas, Laboratorios)...")
        # 5 pisos, 12 aulas de teoría por piso (B-101 a B-512)
        for piso in range(1, 6):
            for aula_num in range(1, 13):
                nombre = f"B-{piso}{aula_num:02d}"
                EspaciosFisicos.objects.get_or_create(
                    nombre_espacio=nombre,
                    defaults={'tipo_espacio': tipos_espacio['teoria'], 'capacidad': 40}
                )
        
        # 5 pisos, 2 laboratorios por piso (D-101 a D-502)
        for piso in range(1, 6):
            for lab_num in range(1, 3):
                nombre = f"D-{piso}{lab_num:02d}"
                EspaciosFisicos.objects.get_or_create(
                    nombre_espacio=nombre,
                    defaults={'tipo_espacio': tipos_espacio['laboratorio'], 'capacidad': 25}
                )

        # 5 pisos, 1 salón C por piso (C-101 a C-501)
        for piso in range(1, 6):
            nombre = f"C-{piso:02d}"
            EspaciosFisicos.objects.get_or_create(
                nombre_espacio=nombre,
                defaults={'tipo_espacio': tipos_espacio['salon_c'], 'capacidad': 100}
            )

    def _crear_periodo_academico(self):
        self.stdout.write("Creando Período Académico de ejemplo...")
        periodo, _ = PeriodoAcademico.objects.get_or_create(
            nombre_periodo="2024-II",
            defaults={
                'fecha_inicio': datetime.date(2024, 8, 1),
                'fecha_fin': datetime.date(2024, 12, 15),
                'activo': True
            }
        )
        return periodo

    def _procesar_planes_de_estudio(self, texto_planes, unidades):
        self.stdout.write("Procesando planes de estudio...")
        # Separar el texto por cada carrera. Usamos una expresión regular para buscar el patrón.
        bloques_carrera = re.split(r'Carrera: ', texto_planes.strip())[1:]

        for bloque in bloques_carrera:
            lineas = bloque.strip().split('\n')
            nombre_carrera = lineas[0].strip()
            # Asignar a unidad académica basado en el nombre de la carrera
            unidad_academica = unidades['ingenieria'] if 'INGENIERÍA' in nombre_carrera.upper() else unidades['empresas']
            
            # Corregido: Buscar el código en la primera línea de datos (índice 4)
            codigo_carrera_match = re.search(r'EAE|ECF|EIS', lineas[4]) 
            codigo_carrera_base = codigo_carrera_match.group(0) if codigo_carrera_match else 'GEN'

            # Corregido: Usar update_or_create con el código único para más robustez
            carrera_obj, created = Carrera.objects.update_or_create(
                codigo_carrera=codigo_carrera_base,
                defaults={
                    'nombre_carrera': nombre_carrera,
                    'unidad': unidad_academica
                }
            )
            self.stdout.write(f"  Procesando Carrera: {nombre_carrera} (Código: {codigo_carrera_base})")

            # Crear ciclos para la carrera
            ciclos_map = {}
            for i in range(1, 11):
                ciclo_obj, _ = Ciclo.objects.get_or_create(
                    orden=i,
                    carrera=carrera_obj,
                    defaults={'nombre_ciclo': f"Ciclo {i}"}
                )
                ciclos_map[i] = ciclo_obj

            # Procesar materias
            for linea in lineas[2:]: # Empezar desde la línea de las materias
                if not linea or linea.startswith('Ciclo'): continue
                
                partes = re.split(r'\s{2,}', linea.strip())
                if len(partes) < 5: continue

                ciclo_num = int(partes[0])
                codigo_materia = partes[1]
                nombre_materia = partes[2]
                h_teo = int(partes[3])
                h_pra = int(partes[4])

                materia_obj, _ = Materias.objects.get_or_create(
                    codigo_materia=codigo_materia,
                    defaults={
                        'nombre_materia': nombre_materia,
                        'horas_academicas_teoricas': h_teo,
                        'horas_academicas_practicas': h_pra
                    }
                )
                
                # Vincular materia con carrera y ciclo
                CarreraMaterias.objects.get_or_create(
                    carrera=carrera_obj,
                    materia=materia_obj,
                    ciclo=ciclos_map[ciclo_num]
                )

    def _crear_grupos_de_ejemplo(self, periodo):
        self.stdout.write("Creando Grupos de ejemplo...")
        carrera_sistemas = Carrera.objects.get(codigo_carrera='EIS')
        ciclo_8_sistemas = Ciclo.objects.get(carrera=carrera_sistemas, orden=8)
        materias_ciclo_8 = Materias.objects.filter(carreramaterias__ciclo=ciclo_8_sistemas)

        secciones = ['A', 'B']
        for seccion in secciones:
            codigo = f"EIS-8-{seccion}"
            grupo, created = Grupos.objects.get_or_create(
                codigo_grupo=codigo,
                periodo=periodo,
                defaults={
                    'carrera': carrera_sistemas,
                    'ciclo_semestral': 8,
                    'turno_preferente': 'N' # Ejemplo de turno Noche
                }
            )
            if created:
                grupo.materias.set(materias_ciclo_8)
                self.stdout.write(f"    Grupo creado: {codigo}")

    def _crear_docentes_de_ejemplo(self):
        self.stdout.write("Creando Docentes de ejemplo...")
        for i in range(1, 11):
            username = f'docente{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, password=f'password{i}', email=f'docente{i}@example.com')
                Docentes.objects.create(
                    usuario=user,
                    nombres=f'Nombre',
                    apellidos=f'Docente {i}',
                    codigo_docente=f'D00{i}',
                    email=f'docente{i}@example.com'
                ) 