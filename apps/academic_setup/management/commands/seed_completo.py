from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from datetime import time, datetime, date
import random

from apps.academic_setup.models import (
    TipoUnidadAcademica, UnidadAcademica, Carrera, Ciclo, PeriodoAcademico,
    TiposEspacio, EspaciosFisicos, Materias, CarreraMaterias
)
from apps.users.models import Docentes
from apps.scheduling.models import (
    Grupos, BloquesHorariosDefinicion, DisponibilidadDocentes, ConfiguracionRestricciones
)

class Command(BaseCommand):
    help = 'Siembra la base de datos con todos los datos necesarios para el sistema de horarios.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("=== Iniciando siembra completa de datos ===")
        
        # Limpiar datos existentes (excepto horarios asignados)
        self._limpiar_datos_previos()
        
        # Crear estructura académica
        unidades = self._crear_unidades_academicas()
        tipos_espacio = self._crear_tipos_espacio()
        espacios_fisicos = self._crear_espacios_fisicos(tipos_espacio, unidades)
        periodo = self._crear_periodo_academico()
        
        # Crear bloques horarios (7:00 AM - 10:00 PM, bloques de 1 hora)
        bloques_horarios = self._crear_bloques_horarios()
        
        # Procesar planes de estudio
        self._procesar_planes_de_estudio(unidades)
        
        # Crear grupos para todas las carreras
        grupos = self._crear_grupos_completos(periodo)
        
        # Crear docentes
        docentes = self._crear_docentes_completos()
        
        # Crear disponibilidad de docentes
        self._crear_disponibilidad_docentes(docentes, periodo, bloques_horarios)
        
        # Crear configuraciones de restricciones
        self._crear_configuraciones_restricciones(periodo)
        
        self.stdout.write(self.style.SUCCESS("=== Siembra completa finalizada exitosamente ==="))

    def _limpiar_datos_previos(self):
        self.stdout.write("Limpiando datos existentes...")
        # NO limpiar HorariosAsignados como solicitaste
        DisponibilidadDocentes.objects.all().delete()
        ConfiguracionRestricciones.objects.all().delete()
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
        BloquesHorariosDefinicion.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Datos previos eliminados."))

    def _crear_unidades_academicas(self):
        self.stdout.write("Creando Unidades Académicas...")
        tipo_facultad, _ = TipoUnidadAcademica.objects.get_or_create(nombre_tipo="Facultad")
        tipo_instituto, _ = TipoUnidadAcademica.objects.get_or_create(nombre_tipo="Instituto")
        
        ua_empresas, _ = UnidadAcademica.objects.get_or_create(
            nombre_unidad="Facultad de Ciencias Empresariales",
            defaults={'tipo_unidad': tipo_facultad}
        )
        ua_ingenieria, _ = UnidadAcademica.objects.get_or_create(
            nombre_unidad="Facultad de Ingeniería",
            defaults={'tipo_unidad': tipo_facultad}
        )
        ua_psicologia, _ = UnidadAcademica.objects.get_or_create(
            nombre_unidad="Facultad de Psicología",
            defaults={'tipo_unidad': tipo_facultad}
        )
        return {'empresas': ua_empresas, 'ingenieria': ua_ingenieria, 'psicologia': ua_psicologia}

    def _crear_tipos_espacio(self):
        self.stdout.write("Creando Tipos de Espacio...")
        teoria, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio="Aula de Teoría")
        lab, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio="Laboratorio")
        salon_c, _ = TiposEspacio.objects.get_or_create(nombre_tipo_espacio="Salón de Usos Múltiples")
        return {'teoria': teoria, 'laboratorio': lab, 'salon_c': salon_c}

    def _crear_espacios_fisicos(self, tipos_espacio, unidades):
        self.stdout.write("Creando Espacios Físicos...")
        espacios = []
        
        # Aulas de teoría (B-101 a B-512)
        for piso in range(1, 6):
            for aula_num in range(1, 13):
                nombre = f"B-{piso}{aula_num:02d}"
                espacio, _ = EspaciosFisicos.objects.get_or_create(
                    nombre_espacio=nombre,
                    defaults={
                        'tipo_espacio': tipos_espacio['teoria'], 
                        'capacidad': 40,
                        'unidad': list(unidades.values())[0]  # Asignar a primera unidad
                    }
                )
                espacios.append(espacio)
        
        # Laboratorios (D-101 a D-502)
        for piso in range(1, 6):
            for lab_num in range(1, 3):
                nombre = f"D-{piso}{lab_num:02d}"
                espacio, _ = EspaciosFisicos.objects.get_or_create(
                    nombre_espacio=nombre,
                    defaults={
                        'tipo_espacio': tipos_espacio['laboratorio'], 
                        'capacidad': 25,
                        'unidad': list(unidades.values())[1]  # Asignar a segunda unidad
                    }
                )
                espacios.append(espacio)

        # Salones C (C-101 a C-501)
        for piso in range(1, 6):
            nombre = f"C-{piso:02d}"
            espacio, _ = EspaciosFisicos.objects.get_or_create(
                nombre_espacio=nombre,
                defaults={
                    'tipo_espacio': tipos_espacio['salon_c'], 
                    'capacidad': 100,
                    'unidad': list(unidades.values())[2]  # Asignar a tercera unidad
                }
            )
            espacios.append(espacio)
        
        return espacios

    def _crear_periodo_academico(self):
        self.stdout.write("Creando Período Académico...")
        periodo, _ = PeriodoAcademico.objects.get_or_create(
            nombre_periodo="2024-II",
            defaults={
                'fecha_inicio': date(2024, 8, 1),
                'fecha_fin': date(2024, 12, 15),
                'activo': True
            }
        )
        return periodo

    def _crear_bloques_horarios(self):
        self.stdout.write("Creando Bloques Horarios (7:00 AM - 10:00 PM, bloques de 1 hora)...")
        bloques = []
        dias_semana = [1, 2, 3, 4, 5]  # Lunes a Viernes
        
        for dia in dias_semana:
            for hora in range(7, 22):  # 7:00 AM hasta 21:00 (9:00 PM) - el último bloque será 21:00-22:00
                hora_inicio = time(hora, 0)
                hora_fin = time(hora + 1, 0)
                
                # Determinar turno
                if hora < 12:
                    turno = 'M'  # Mañana (7:00-11:59)
                elif hora < 18:
                    turno = 'T'  # Tarde (12:00-17:59)
                else:
                    turno = 'N'  # Noche (18:00-21:59)
                
                nombre_bloque = f"{dict(BloquesHorariosDefinicion.DIA_SEMANA_CHOICES)[dia]} {hora_inicio.strftime('%H:%M')}-{hora_fin.strftime('%H:%M')}"
                
                bloque, _ = BloquesHorariosDefinicion.objects.get_or_create(
                    nombre_bloque=nombre_bloque,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    turno=turno,
                    dia_semana=dia,
                    defaults={}
                )
                bloques.append(bloque)
        
        self.stdout.write(f"    Creados {len(bloques)} bloques horarios (7:00 AM - 10:00 PM)")
        return bloques

    def _procesar_planes_de_estudio(self, unidades):
        self.stdout.write("Procesando planes de estudio...")
        
        # Datos de las carreras
        carreras_data = [
            {
                'nombre': 'ADMINISTRACIÓN DE EMPRESAS',
                'codigo': 'EAE',
                'unidad': unidades['empresas'],
                'materias': [
                    (1, 'EAE24-001', 'Fundamentos de Administración', 48, 32),
                    (1, 'EAE24-002', 'Matemática Básica', 48, 32),
                    (1, 'EAE24-003', 'Comunicación Efectiva', 32, 32),
                    (2, 'EAE24-004', 'Contabilidad Básica', 48, 32),
                    (2, 'EAE24-005', 'Microeconomía', 48, 32),
                    (2, 'EAE24-006', 'Estadística Descriptiva', 48, 32),
                    (3, 'EAE24-007', 'Macroeconomía', 48, 32),
                    (3, 'EAE24-008', 'Gestión de Recursos Humanos', 48, 32),
                    (3, 'EAE24-009', 'Marketing Básico', 48, 32),
                    (4, 'EAE24-010', 'Finanzas Corporativas', 48, 32),
                    (4, 'EAE24-011', 'Gestión de Operaciones', 48, 32),
                    (4, 'EAE24-012', 'Investigación de Mercados', 48, 32),
                    (5, 'EAE24-013', 'Gestión Estratégica', 48, 32),
                    (5, 'EAE24-014', 'Comercio Internacional', 48, 32),
                    (5, 'EAE24-015', 'Proyectos de Inversión', 48, 32),
                    (6, 'EAE24-016', 'Auditoría Administrativa', 48, 32),
                    (6, 'EAE24-017', 'Gestión de Calidad', 48, 32),
                    (6, 'EAE24-018', 'Seminario de Tesis', 80, 32),
                    (7, 'EAE24-019', 'Práctica Pre-Profesional I', 0, 96),
                    (8, 'EAE24-020', 'Práctica Pre-Profesional II', 0, 96),
                    (9, 'EAE24-021', 'Práctica Pre-Profesional III', 0, 96),
                    (10, 'EAE24-022', 'Práctica Pre-Profesional IV', 0, 96),
                ]
            },
            {
                'nombre': 'CONTABILIDAD Y FINANZAS',
                'codigo': 'ECF',
                'unidad': unidades['empresas'],
                'materias': [
                    (1, 'ECF24-001', 'Fundamentos de Contabilidad', 48, 32),
                    (1, 'ECF24-002', 'Matemática Financiera', 48, 32),
                    (1, 'ECF24-003', 'Informática Básica', 32, 32),
                    (2, 'ECF24-004', 'Contabilidad Intermedia', 48, 32),
                    (2, 'ECF24-005', 'Estadística Aplicada', 48, 32),
                    (2, 'ECF24-006', 'Derecho Comercial', 48, 32),
                    (3, 'ECF24-007', 'Contabilidad de Costos', 48, 32),
                    (3, 'ECF24-008', 'Análisis Financiero', 48, 32),
                    (3, 'ECF24-009', 'Auditoría I', 48, 32),
                    (4, 'ECF24-010', 'Contabilidad Avanzada', 48, 32),
                    (4, 'ECF24-011', 'Finanzas Corporativas', 48, 32),
                    (4, 'ECF24-012', 'Auditoría II', 48, 32),
                    (5, 'ECF24-013', 'Contabilidad Gubernamental', 48, 32),
                    (5, 'ECF24-014', 'Gestión Tributaria', 48, 32),
                    (5, 'ECF24-015', 'Contabilidad Internacional', 48, 32),
                    (6, 'ECF24-016', 'Auditoría Forense', 48, 32),
                    (6, 'ECF24-017', 'Sistemas de Información Contable', 48, 32),
                    (6, 'ECF24-018', 'Seminario de Tesis', 80, 32),
                    (7, 'ECF24-019', 'Práctica Pre-Profesional I', 0, 96),
                    (8, 'ECF24-020', 'Práctica Pre-Profesional II', 0, 96),
                    (9, 'ECF24-021', 'Práctica Pre-Profesional III', 0, 96),
                    (10, 'ECF24-022', 'Práctica Pre-Profesional IV', 0, 96),
                ]
            },
            {
                'nombre': 'INGENIERÍA DE SISTEMAS DE INFORMACIÓN',
                'codigo': 'EIS',
                'unidad': unidades['ingenieria'],
                'materias': [
                    (1, 'EIS24-001', 'Fundamentos de Programación', 48, 32),
                    (1, 'EIS24-002', 'Matemática Discreta', 48, 32),
                    (1, 'EIS24-003', 'Introducción a la Ingeniería', 32, 32),
                    (2, 'EIS24-004', 'Programación Orientada a Objetos', 48, 32),
                    (2, 'EIS24-005', 'Cálculo I', 48, 32),
                    (2, 'EIS24-006', 'Física I', 48, 32),
                    (3, 'EIS24-007', 'Estructuras de Datos', 48, 32),
                    (3, 'EIS24-008', 'Cálculo II', 48, 32),
                    (3, 'EIS24-009', 'Física II', 48, 32),
                    (4, 'EIS24-010', 'Algoritmos y Complejidad', 48, 32),
                    (4, 'EIS24-011', 'Probabilidad y Estadística', 48, 32),
                    (4, 'EIS24-012', 'Arquitectura de Computadoras', 48, 32),
                    (5, 'EIS24-013', 'Bases de Datos I', 48, 32),
                    (5, 'EIS24-014', 'Redes de Computadoras', 48, 32),
                    (5, 'EIS24-015', 'Ingeniería de Software I', 48, 32),
                    (6, 'EIS24-016', 'Bases de Datos II', 48, 32),
                    (6, 'EIS24-017', 'Sistemas Operativos', 48, 32),
                    (6, 'EIS24-018', 'Ingeniería de Software II', 48, 32),
                    (7, 'EIS24-019', 'Desarrollo Web', 48, 32),
                    (7, 'EIS24-020', 'Inteligencia Artificial', 48, 32),
                    (7, 'EIS24-021', 'Seguridad Informática', 48, 32),
                    (8, 'EIS24-022', 'Desarrollo Móvil', 48, 32),
                    (8, 'EIS24-023', 'Validación y pruebas de software', 48, 32),
                    (8, 'EIS24-024', 'Auditoría de sistemas', 48, 32),
                    (9, 'EIS24-025', 'Analítica con Big Data', 48, 32),
                    (9, 'EIS24-026', 'Inteligencia artificial', 48, 32),
                    (9, 'EIS24-027', 'Bases de datos', 48, 32),
                    (10, 'EIS24-028', 'Proyectos en TI', 48, 32),
                ]
            }
        ]
        
        for carrera_data in carreras_data:
            # Crear carrera
            carrera_obj, _ = Carrera.objects.get_or_create(
                codigo_carrera=carrera_data['codigo'],
                defaults={
                    'nombre_carrera': carrera_data['nombre'],
                    'unidad': carrera_data['unidad']
                }
            )
            self.stdout.write(f"  Procesando Carrera: {carrera_data['nombre']} (Código: {carrera_data['codigo']})")
            
            # Crear ciclos
            ciclos_map = {}
            for i in range(1, 11):
                ciclo_obj, _ = Ciclo.objects.get_or_create(
                    orden=i,
                    carrera=carrera_obj,
                    defaults={'nombre_ciclo': f"Ciclo {i}"}
                )
                ciclos_map[i] = ciclo_obj
            
            # Crear materias y vincular
            for ciclo_num, codigo, nombre, h_teo, h_pra in carrera_data['materias']:
                materia_obj, _ = Materias.objects.get_or_create(
                    codigo_materia=codigo,
                    defaults={
                        'nombre_materia': nombre,
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

    def _crear_grupos_completos(self, periodo):
        self.stdout.write("Creando Grupos para todas las carreras...")
        grupos = []
        
        carreras = Carrera.objects.all()
        for carrera in carreras:
            ciclos = Ciclo.objects.filter(carrera=carrera)
            for ciclo in ciclos:
                materias_ciclo = Materias.objects.filter(carreramaterias__ciclo=ciclo)
                if not materias_ciclo.exists():
                    continue
                
                # Crear 2 secciones por ciclo (A y B)
                for seccion in ['A', 'B']:
                    codigo = f"{carrera.codigo_carrera}-{ciclo.orden}-{seccion}"
                    grupo, _ = Grupos.objects.get_or_create(
                        codigo_grupo=codigo,
                        periodo=periodo,
                        defaults={
                            'carrera': carrera,
                            'ciclo_semestral': ciclo.orden,
                            'turno_preferente': random.choice(['M', 'T', 'N']),
                            'numero_estudiantes_estimado': random.randint(20, 35)
                        }
                    )
                    grupo.materias.set(materias_ciclo)
                    grupos.append(grupo)
                    self.stdout.write(f"    Grupo creado: {codigo}")
        
        return grupos

    def _crear_docentes_completos(self):
        self.stdout.write("Creando Docentes...")
        docentes = []
        
        # Crear 20 docentes
        for i in range(1, 21):
            username = f'docente{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username, 
                    password=f'password{i}', 
                    email=f'docente{i}@example.com'
                )
                docente = Docentes.objects.create(
                    usuario=user,
                    nombres=f'Nombre',
                    apellidos=f'Docente {i}',
                    codigo_docente=f'D00{i}',
                    email=f'docente{i}@example.com',
                    telefono=f'999-{i:03d}-{i:03d}',
                    tipo_contrato=random.choice(['Tiempo Completo', 'Tiempo Parcial', 'Contratado']),
                    max_horas_semanales=random.choice([20, 30, 40])
                )
                docentes.append(docente)
                self.stdout.write(f"    Docente creado: {docente}")
        
        return docentes

    def _crear_disponibilidad_docentes(self, docentes, periodo, bloques_horarios):
        self.stdout.write("Creando Disponibilidad de Docentes...")
        disponibilidades_creadas = 0
        
        for docente in docentes:
            for bloque in bloques_horarios:
                # 80% de probabilidad de estar disponible
                if random.random() < 0.8:
                    disponibilidad, created = DisponibilidadDocentes.objects.get_or_create(
                        docente=docente,
                        periodo=periodo,
                        dia_semana=bloque.dia_semana,
                        bloque_horario=bloque,
                        defaults={
                            'esta_disponible': True,
                            'preferencia': random.choice([0, 0, 0, 1, -1]),  # Más neutral
                            'origen_carga': 'MANUAL'
                        }
                    )
                    if created:
                        disponibilidades_creadas += 1
        
        self.stdout.write(f"    Creadas {disponibilidades_creadas} disponibilidades de docentes")

    def _crear_configuraciones_restricciones(self, periodo):
        self.stdout.write("Creando Configuraciones de Restricciones...")
        
        restricciones_data = [
            {
                'codigo': 'MAX_HORAS_DIA_DOCENTE',
                'descripcion': 'Ningún docente puede exceder las 6 horas de clase al día',
                'tipo': 'GLOBAL',
                'valor': '6'
            },
            {
                'codigo': 'MAX_HORAS_SEMANA_DOCENTE',
                'descripcion': 'Ningún docente puede exceder las 20 horas de clase por semana',
                'tipo': 'GLOBAL',
                'valor': '20'
            },
            {
                'codigo': 'NO_CLASES_SABADO',
                'descripcion': 'No se pueden programar clases los sábados',
                'tipo': 'GLOBAL',
                'valor': '6'  # Código del sábado
            },
            {
                'codigo': 'NO_CLASES_DOMINGO',
                'descripcion': 'No se pueden programar clases los domingos',
                'tipo': 'GLOBAL',
                'valor': '7'  # Código del domingo
            },
            {
                'codigo': 'CAPACIDAD_AULA',
                'descripcion': 'El número de estudiantes no puede exceder la capacidad del aula',
                'tipo': 'AULA',
                'valor': '100%'
            },
            {
                'codigo': 'LABORATORIO_SOLO_PRACTICAS',
                'descripcion': 'Los laboratorios solo pueden usarse para clases prácticas',
                'tipo': 'AULA',
                'valor': 'SOLO_PRACTICAS'
            }
        ]
        
        for restriccion_data in restricciones_data:
            ConfiguracionRestricciones.objects.get_or_create(
                codigo_restriccion=restriccion_data['codigo'],
                defaults={
                    'descripcion': restriccion_data['descripcion'],
                    'tipo_aplicacion': restriccion_data['tipo'],
                    'valor_parametro': restriccion_data['valor'],
                    'periodo_aplicable': periodo,
                    'esta_activa': True
                }
            )
        
        self.stdout.write(f"    Creadas {len(restricciones_data)} configuraciones de restricciones") 