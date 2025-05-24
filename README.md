# API del Sistema de Gestión de Horarios - La Pontificia

Este documento describe la API RESTful para el Sistema de Gestión de Horarios de la institución La Pontificia.

# Guía de instalación y configuración del proyecto

## 1. Crear y activar un entorno virtual (opcional pero recomendado)
Para crear el entorno virtual, ejecuta:
```bash
python -m venv venv
venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver

Este es un ejemplo completo en código Markdown que puedes copiar y pegar en tu archivo `.md`. ¡Espero que te resulte útil! 

Si deseas más información o algún ajuste adicional, no dudes en decírmelo.
```
## 1. Configuración Base

### URL Base
La API está disponible (localmente) en:
`http://localhost:8000/api/`

### Autenticación
Todas las rutas protegidas requieren un Token JWT de Acceso. Este token debe ser enviado en la cabecera `Authorization` con el prefijo `Bearer`.

**Ejemplo de Cabecera:**
`Authorization: Bearer <tu_token_de_acceso_jwt>`

## 2. Autenticación

### 2.1. Iniciar Sesión (Obtener Tokens)
Permite a un usuario iniciar sesión y obtener tokens de acceso y refresco. La respuesta incluye información del usuario y sus roles (grupos).

* **Endpoint:** `/auth/login/`
* **Método:** `POST`
* **Cabeceras:**
    * `Content-Type: application/json`
* **Cuerpo de la Solicitud (Request Body):**
    ```json
    {
        "username": "tu_nombre_de_usuario",
        "password": "tu_contraseña"
    }
    ```
* **Respuesta Exitosa (200 OK):**
    ```json
    {
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user_id": 1,
        "username": "adminuser1",
        "email": "admin1@example.com",
        "first_name": "Admin",
        "last_name": "User1",
        "is_staff": true,
        "is_superuser": true,
        "groups": ["Admins"]
    }
    ```
* **Respuesta de Error (401 Unauthorized - Credenciales inválidas):**
    ```json
    {
        "detail": "No active account found with the given credentials"
    }
    ```

### 2.2. Refrescar Token de Acceso
Permite obtener un nuevo token de acceso utilizando un token de refresco válido.

* **Endpoint:** `/auth/refresh/`
* **Método:** `POST`
* **Cabeceras:**
    * `Content-Type: application/json`
* **Cuerpo de la Solicit พิจารณา (Request Body):**
    ```json
    {
        "refresh": "tu_token_de_refresco_jwt"
    }
    ```
* **Respuesta Exitosa (200 OK):**
    ```json
    {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
* **Respuesta de Error (401 Unauthorized - Token inválido o expirado):**
    ```json
    {
        "detail": "Token is invalid or expired",
        "code": "token_not_valid"
    }
    ```

## 3. Configuración Académica (`/academic/`)

### 3.1. Unidades Académicas
Gestión de unidades académicas (facultades, escuelas, etc.).

* **Endpoint:** `/academic/unidades-academicas/`
* **Métodos:**
    * `GET`: Listar todas las unidades académicas.
    * `POST`: Crear una nueva unidad académica.
* **Autenticación:** Requerida.

#### Listar Unidades Académicas (GET)
* **Respuesta Exitosa (200 OK):**
    ```json
    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "unidad_id": 1,
                "nombre_unidad": "Facultad de Ingeniería",
                "descripcion": "Unidad dedicada a las carreras de ingeniería."
            }
        ]
    }
    ```

#### Crear Unidad Académica (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "nombre_unidad": "Instituto de Idiomas",
        "descripcion": "Enseñanza de lenguas extranjeras."
    }
    ```
* **Respuesta Exitosa (201 Created):**
    ```json
    {
        "unidad_id": 2,
        "nombre_unidad": "Instituto de Idiomas",
        "descripcion": "Enseñanza de lenguas extranjeras."
    }
    ```

---
*(De manera similar, documentarías los endpoints CRUD para: `/carreras/`, `/periodos-academicos/`, `/tipos-espacio/`, `/espacios-fisicos/`, `/especialidades/`, `/materias/`, `/carrera-materias/`, `/materia-especialidades-requeridas/`. Aquí un ejemplo para Materias)*
---

### 3.2. Materias
Gestión de materias o asignaturas.

* **Endpoint:** `/academic/materias/`
* **Métodos:** `GET`, `POST`, `GET /{id}/`, `PUT /{id}/`, `PATCH /{id}/`, `DELETE /{id}/`
* **Autenticación:** Requerida.

#### Listar Materias (GET)
* **Respuesta Exitosa (200 OK):**
    ```json
    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "materia_id": 1,
                "codigo_materia": "MAT001",
                "nombre_materia": "Programación Orientada a Objetos I",
                "descripcion": "Fundamentos de POO.",
                "horas_academicas_teoricas": 3,
                "horas_academicas_practicas": 2,
                "horas_academicas_laboratorio": 0,
                "horas_totales": 5,
                "requiere_tipo_espacio_especifico": null, // ID del TipoEspacio o null
                "requiere_tipo_espacio_nombre": null,    // Nombre del TipoEspacio o null
                "estado": true
            }
        ]
    }
    ```

#### Crear Materia (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "codigo_materia": "MAT002",
        "nombre_materia": "Física General II",
        "descripcion": "Conceptos avanzados de física.",
        "horas_academicas_teoricas": 2,
        "horas_academicas_practicas": 1,
        "horas_academicas_laboratorio": 2,
        "requiere_tipo_espacio_especifico": 3, // ID de un TipoEspacio "Laboratorio de Ciencias"
        "estado": true
    }
    ```
* **Respuesta Exitosa (201 Created):**
  *(Devuelve el objeto de la materia creada, similar al de la lista pero sin paginación)*

## 4. Usuarios y Personal (`/users/`)

### 4.1. Registro de Nuevos Usuarios
Permite registrar un nuevo usuario en el sistema.

* **Endpoint:** `/users/all/register/`
* **Método:** `POST`
* **Autenticación:** No requerida (Permitir a cualquiera registrarse, o ajustar permisos).
* **Cuerpo de la Solicitud:**
    ```json
    {
        "username": "nuevo_docente",
        "email": "nuevo.docente@example.com",
        "password": "passwordSegura123",
        "password2": "passwordSegura123",
        "first_name": "NombreDocente",
        "last_name": "ApellidoDocente"
    }
    ```
* **Respuesta Exitosa (201 Created):**
    ```json
    {
        "id": 5,
        "username": "nuevo_docente",
        "email": "nuevo.docente@example.com",
        "first_name": "NombreDocente",
        "last_name": "ApellidoDocente",
        "is_staff": false, // O true, dependiendo de la lógica de registro
        "is_active": true,
        "groups": [] // El usuario podría ser asignado a grupos por defecto aquí
    }
    ```

### 4.2. Obtener Información del Usuario Actual (`/me/`)
Devuelve información del usuario autenticado.

* **Endpoint:** `/users/all/me/`
* **Método:** `GET`
* **Autenticación:** Requerida.
* **Respuesta Exitosa (200 OK):**
    ```json
    {
        "id": 1,
        "username": "adminuser1",
        "email": "admin1@example.com",
        "first_name": "Admin",
        "last_name": "User1",
        "is_staff": true,
        "is_active": true,
        "groups": [ // Nombres de los grupos a los que pertenece
            "Admins"
        ]
    }
    ```

### 4.3. Docentes
Gestión de la información de los docentes.

* **Endpoint:** `/users/docentes/`
* **Métodos:** `GET`, `POST`, `GET /{id}/`, `PUT /{id}/`, `PATCH /{id}/`, `DELETE /{id}/`
* **Autenticación:** Requerida.

#### Crear Docente (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "usuario": 5, // ID del User de Django previamente registrado
        "codigo_docente": "DOC021",
        "nombres": "NombreDocente", // Puede ser redundante si se toma del User
        "apellidos": "ApellidoDocente", // Puede ser redundante
        "dni": "87654321",
        "email": "nuevo.docente@example.com", // Puede ser redundante
        "telefono": "+51987654321",
        "tipo_contrato": "Tiempo Completo",
        "max_horas_semanales": 40,
        "unidad_principal": 1, // ID de la UnidadAcademica
        "especialidad_ids": [2, 5] // Lista de IDs de Especialidades
    }
    ```
* **Respuesta Exitosa (201 Created):**
  *(Devuelve el objeto del docente creado con detalles, incluyendo `especialidades_detalle`)*

---
*(De manera similar, documentarías los endpoints CRUD para: `/roles/` (si se exponen directamente), `/groups/` (grupos de Django si se exponen))*
---

## 5. Programación de Horarios (`/scheduling/`)

### 5.1. Grupos/Secciones
Gestión de grupos o secciones de materias.

* **Endpoint:** `/scheduling/grupos/`
* **Métodos:** `GET`, `POST`, etc.
* **Autenticación:** Requerida.
* **Filtrado (GET):** Permite filtrar por `periodo`, `carrera`, `materia`, `turno_preferente`.
    * Ej: `/scheduling/grupos/?periodo=1&carrera=2`

#### Crear Grupo (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "codigo_grupo": "MAT001-INGSI-2025I-A",
        "materia": 1, // ID de Materia
        "carrera": 1, // ID de Carrera
        "periodo": 1, // ID de PeriodoAcademico
        "numero_estudiantes_estimado": 30,
        "turno_preferente": "M", // 'M', 'T', 'N', o null
        "docente_asignado_directamente": null // ID de Docente o null
    }
    ```
* **Respuesta Exitosa (201 Created):**
  *(Objeto del grupo creado con detalles anidados como `materia_detalle`, `carrera_detalle`)*

### 5.2. Bloques Horarios (Definición)
Gestión de los bloques de tiempo definidos institucionalmente.

* **Endpoint:** `/scheduling/bloques-horarios/`
* **Métodos:** `GET`, `POST`, etc.
* **Autenticación:** Requerida.

#### Crear Bloque Horario (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "nombre_bloque": "Lunes 07:00-08:40",
        "hora_inicio": "07:00:00",
        "hora_fin": "08:40:00",
        "turno": "M",
        "dia_semana": 1 // 1:Lunes, ..., 7:Domingo
    }
    ```

### 5.3. Disponibilidad de Docentes
Gestión de la disponibilidad horaria de los docentes.

* **Endpoint:** `/scheduling/disponibilidad-docentes/`
* **Métodos:** `GET`, `POST`, etc.
* **Autenticación:** Requerida.
* **Acción Adicional:** `POST /cargar-disponibilidad-excel/` (para carga masiva desde Excel, implementación pendiente).

#### Crear Disponibilidad (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "docente": 1, // ID del Docente
        "periodo": 1, // ID del PeriodoAcademico
        "dia_semana": 1, // Lunes
        "bloque_horario": 5, // ID del BloquesHorariosDefinicion
        "esta_disponible": true,
        "preferencia": 0 // -1 No preferido, 0 Neutral, 1 Preferido
    }
    ```

### 5.4. Horarios Asignados
Consulta y gestión de los horarios de clase ya programados.

* **Endpoint:** `/scheduling/horarios-asignados/`
* **Métodos:** `GET`, `POST` (manual), `PUT /{id}/`, `PATCH /{id}/`, `DELETE /{id}/`
* **Autenticación:** Requerida.
* **Filtrado (GET):** Permite filtrar por `periodo`, `docente`, `espacio`, `grupo`, `grupo__materia`, `grupo__carrera`, `dia_semana`.
    * Ej: `/scheduling/horarios-asignados/?periodo=1&docente=3`

#### Crear Horario Asignado Manualmente (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "grupo": 1, // ID de Grupo
        "docente": 3, // ID de Docente
        "espacio": 10, // ID de EspacioFisico
        "periodo": 1, // ID de PeriodoAcademico
        "dia_semana": 2, // Martes
        "bloque_horario": 7, // ID de BloquesHorariosDefinicion
        "estado": "Programado", // Opcional
        "observaciones": "Clase asignada manualmente." // Opcional
    }
    ```

### 5.5. Configuración de Restricciones
Gestión de las reglas y restricciones para la generación de horarios.

* **Endpoint:** `/scheduling/configuracion-restricciones/`
* **Métodos:** `GET`, `POST`, `GET /{id}/`, `PUT /{id}/`, `PATCH /{id}/`, `DELETE /{id}/`
* **Autenticación:** Requerida (probablemente solo Administradores).

#### Crear Restricción (POST)
* **Cuerpo de la Solicitud:**
    ```json
    {
        "codigo_restriccion": "MAX_HORAS_DIA_DOCENTE_GLOBAL",
        "descripcion": "Ningún docente puede exceder las 6 horas de clase al día.",
        "tipo_aplicacion": "GLOBAL", // DOCENTE, MATERIA, AULA, CARRERA, PERIODO
        "entidad_id_1": null, // ID de la entidad si no es GLOBAL
        "valor_parametro": "6",
        "periodo_aplicable": null, // ID de PeriodoAcademico o null
        "esta_activa": true
    }
    ```
  *Ver la respuesta anterior para más ejemplos de cuerpos de restricciones.*

### 5.6. Acciones de Horario
Endpoints para acciones especiales como la generación automática.

* **Endpoint:** `/scheduling/acciones-horario/`

#### 5.6.1. Generar Horario Automático
Dispara el proceso de generación automática de horarios para un período.

* **Endpoint:** `/scheduling/acciones-horario/generar-horario-automatico/`
* **Método:** `POST`
* **Autenticación:** Requerida (probablemente solo Administradores/Coordinadores).
* **Cuerpo de la Solicitud:**
    ```json
    {
        "periodo_id": 1 // ID del PeriodoAcademico
    }
    ```
* **Respuesta Exitosa (200 OK):**
    ```json
    {
        "message": "Proceso de generación de horarios para 2025-I completado.",
        "stats": {
            "asignaciones_exitosas": 150,
            "intentos_fallidos": 12,
            "grupos_programados": 30,
            "grupos_no_programados": 2
        },
        "unresolved_conflicts": [
            "No se pudo asignar una sesión para el grupo GRP00X (materia: Ejemplo)."
        ]
    }
    ```

#### 5.6.2. Exportar Horarios a Excel
(Implementación del backend pendiente)

* **Endpoint:** `/scheduling/acciones-horario/exportar-horarios-excel/`
* **Método:** `GET`
* **Autenticación:** Requerida.
* **Parámetros de URL:**
    * `periodo_id` (obligatorio): ID del PeriodoAcademico a exportar.
    * Ej: `/scheduling/acciones-horario/exportar-horarios-excel/?periodo_id=1`
* **Respuesta Exitosa (200 OK):**
    * Un archivo Excel (`.xlsx`) para descargar.

## 6. Consideraciones Adicionales

* **Paginación:** Las respuestas de listado (`GET` a colecciones) están paginadas. La respuesta incluye `count`, `next` (URL a la siguiente página), `previous` (URL a la página anterior) y `results` (la lista de objetos de la página actual).
* **Errores Comunes:**
    * `400 Bad Request`: Datos de solicitud inválidos (ej. campos faltantes, formato incorrecto). La respuesta usualmente incluye detalles de los errores por campo.
        ```json
        {
            "nombre_materia": ["This field is required."]
        }
        ```
    * `401 Unauthorized`: Autenticación requerida o token inválido.
    * `403 Forbidden`: Autenticado pero sin permisos para realizar la acción.
    * `404 Not Found`: El recurso solicitado no existe.
    * `500 Internal Server Error`: Error inesperado en el servidor.

Este README te servirá como una guía inicial. Deberás completarlo con todos los endpoints y detalles específicos a medida que desarrolles y refines tu API. Puedes usar herramientas como Swagger/OpenAPI para generar documentación más interactiva y formal a partir de tu código Django REST framework si lo deseas en el futuro.
