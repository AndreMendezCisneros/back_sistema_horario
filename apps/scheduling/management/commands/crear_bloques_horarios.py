from django.core.management.base import BaseCommand
from apps.scheduling.models import BloquesHorariosDefinicion
from datetime import time

class Command(BaseCommand):
    help = 'Crea bloques horarios de ejemplo para el sistema'

    def handle(self, *args, **options):
        self.stdout.write('Creando bloques horarios...')
        
        # Definir los horarios por turno
        horarios_manana = [
            ('07:00', '08:30'),
            ('08:30', '10:00'),
            ('10:00', '11:30'),
            ('11:30', '13:00'),
        ]
        
        horarios_tarde = [
            ('13:00', '14:30'),
            ('14:30', '16:00'),
            ('16:00', '17:30'),
            ('17:30', '19:00'),
        ]
        
        horarios_noche = [
            ('18:00', '19:30'),
            ('19:30', '21:00'),
            ('21:00', '22:30'),
        ]
        
        dias_semana = [
            (1, 'Lunes'),
            (2, 'Martes'),
            (3, 'Miércoles'),
            (4, 'Jueves'),
            (5, 'Viernes'),
            (6, 'Sábado'),
        ]
        
        bloques_creados = 0
        
        # Crear bloques para cada día y turno
        for dia_id, dia_nombre in dias_semana:
            # Bloques de mañana
            for hora_inicio, hora_fin in horarios_manana:
                nombre_bloque = f"{dia_nombre} {hora_inicio}-{hora_fin}"
                bloque, created = BloquesHorariosDefinicion.objects.get_or_create(
                    nombre_bloque=nombre_bloque,
                    hora_inicio=time.fromisoformat(hora_inicio),
                    hora_fin=time.fromisoformat(hora_fin),
                    turno='M',
                    dia_semana=dia_id
                )
                if created:
                    bloques_creados += 1
                    self.stdout.write(f'  ✓ Creado: {nombre_bloque} (Mañana)')
            
            # Bloques de tarde
            for hora_inicio, hora_fin in horarios_tarde:
                nombre_bloque = f"{dia_nombre} {hora_inicio}-{hora_fin}"
                bloque, created = BloquesHorariosDefinicion.objects.get_or_create(
                    nombre_bloque=nombre_bloque,
                    hora_inicio=time.fromisoformat(hora_inicio),
                    hora_fin=time.fromisoformat(hora_fin),
                    turno='T',
                    dia_semana=dia_id
                )
                if created:
                    bloques_creados += 1
                    self.stdout.write(f'  ✓ Creado: {nombre_bloque} (Tarde)')
            
            # Bloques de noche (solo lunes a viernes)
            if dia_id <= 5:  # Lunes a Viernes
                for hora_inicio, hora_fin in horarios_noche:
                    nombre_bloque = f"{dia_nombre} {hora_inicio}-{hora_fin}"
                    bloque, created = BloquesHorariosDefinicion.objects.get_or_create(
                        nombre_bloque=nombre_bloque,
                        hora_inicio=time.fromisoformat(hora_inicio),
                        hora_fin=time.fromisoformat(hora_fin),
                        turno='N',
                        dia_semana=dia_id
                    )
                    if created:
                        bloques_creados += 1
                        self.stdout.write(f'  ✓ Creado: {nombre_bloque} (Noche)')
        
        self.stdout.write(
            self.style.SUCCESS(f'¡Completado! Se crearon {bloques_creados} bloques horarios nuevos.')
        )
        self.stdout.write(f'Total de bloques en el sistema: {BloquesHorariosDefinicion.objects.count()}') 