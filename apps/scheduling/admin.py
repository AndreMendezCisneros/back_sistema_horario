# apps/scheduling/admin.py

from django.contrib import admin
from .models import (
    Grupos,
    BloquesHorariosDefinicion,
    DisponibilidadDocentes,
    HorariosAsignados,
    
    ConfiguracionRestricciones
)

# Registrar los modelos para que aparezcan en el panel de administración de Django
admin.site.register(Grupos)
admin.site.register(BloquesHorariosDefinicion)
admin.site.register(DisponibilidadDocentes)
admin.site.register(HorariosAsignados)
admin.site.register(ConfiguracionRestricciones)

