# ServiPro - Control de Plagas

Modulo de Odoo 19 Community para la gestion integral de servicios de control de plagas. Permite gestionar sedes, planos interactivos con posicionamiento de trampas, registro de incidencias, inspecciones tecnicas, quejas de clientes y analisis de datos mediante un dashboard con 23 graficas.

## Tabla de Contenidos

- [Caracteristicas](#caracteristicas)
- [Requisitos](#requisitos)
- [Instalacion](#instalacion)
- [Configuracion](#configuracion)
- [Estructura del Modulo](#estructura-del-modulo)
- [Modelos de Datos](#modelos-de-datos)
- [Widget Interactivo (OWL)](#widget-interactivo-owl)
- [Dashboard de Graficas](#dashboard-de-graficas)
- [Reportes PDF](#reportes-pdf)
- [Seguridad y Roles](#seguridad-y-roles)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Licencia](#licencia)

## Caracteristicas

### Gestion de Sedes y Planos
- Registro de sedes/plantas con datos de ubicacion
- Carga de planos (imagenes) con procesamiento automatico en background
- Zonas poligonales dibujables sobre los planos (SVG)
- Catalogo de ubicaciones configurable

### Plano Interactivo (Widget OWL)
- Posicionamiento de trampas mediante click sobre el plano
- Drag and drop para mover trampas (con modo edicion y registro de motivo)
- Popover contextual con acciones: registrar incidencia, editar, historial, desactivar
- Zoom (+/-/reset) con soporte para Ctrl+scroll
- Panel lateral filtrable por tipo de trampa, estado y busqueda por nombre
- Leyenda de tipos de trampa con toggle de visibilidad
- Badges de incidencias sobre marcadores
- Mapa de calor (heatmap) con umbrales configurables
- Mini-tabla de detalle al seleccionar una trampa
- Deteccion automatica de zona al crear/mover trampas (ray-casting)
- Iconos configurables por tipo de trampa (FontAwesome 4)

### Registro de Datos
- Incidencias: capturas y hallazgos con tipo de plaga, cantidad de organismos, inspector
- Estados de trampas: funciona, en reparacion, no funciona
- Movimientos de trampas con historial y motivo
- Evidencias fotograficas con flujo de resolucion
- Inspecciones tecnicas
- Quejas de clientes con clasificacion de severidad

### Dashboard de Analisis (Chart.js)
- 14 graficas de analisis de sede (plagas por mes, areas con mayor incidencia, distribucion por tipo, voladores, rastreros)
- 7 graficas de estadisticas de quejas (por semana, clasificacion, estado)
- 2 graficas de ventas (por sede, por usuario)
- Filtros por sede, plano y rango de fechas
- Selector de graficas visibles
- Descarga individual en PNG
- Vista en pantalla completa por grafica
- Exportacion a PowerPoint (PptxGenJS)

### Reportes PDF (QWeb)
- Reporte de trampas por plano
- Reporte de incidencias
- Reporte completo (trampas + incidencias + estadisticas)
- Reporte de visita tecnica

### Importacion de Datos
- Import de incidencias desde Excel con plantilla descargable
- Vista previa con validacion de errores antes de confirmar
- Registro masivo de estados de trampas mediante wizard

## Requisitos

### Software
- Odoo 19.0 Community Edition
- PostgreSQL 12+ (recomendado 13+)
- Python 3.12+

### Dependencias Python
```
Pillow==10.3.0
openpyxl==3.1.2
markdown==3.6
```

### Dependencias Odoo
- base
- mail
- sale

## Instalacion

1. Clonar el repositorio en el directorio de addons de Odoo:
```bash
git clone https://github.com/PAULdGuez/Servipro.git
```

2. Agregar la ruta al `addons_path` en `odoo.conf`:
```
addons_path = /ruta/al/repositorio,...otros_addons
```

3. Instalar dependencias Python:
```bash
pip install -r requirements.txt
```

4. Reiniciar Odoo y actualizar la lista de modulos:
```bash
python odoo-bin -c odoo.conf -u pest_control -d nombre_base_datos --stop-after-init
```

5. Activar el modulo desde Aplicaciones en la interfaz web de Odoo.

### Librerias JavaScript

El modulo incluye tres librerias JavaScript que deben descargarse manualmente:

| Libreria | Version | URL de descarga | Destino |
|---|---|---|---|
| Chart.js | 4.4.7 (UMD) | https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.js | `static/lib/chart.umd.min.js` |
| chartjs-plugin-datalabels | 2.2.0 | https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js | `static/lib/chartjs-plugin-datalabels.min.js` |
| PptxGenJS | 3.12.0 (Bundle) | https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgenjs.bundle.js | `static/lib/pptxgenjs.min.js` |

Descargar cada archivo y reemplazar el contenido del stub correspondiente en `static/lib/`.

## Configuracion

### Roles de Usuario
El modulo define tres niveles de acceso jerarquicos:

| Rol | Permisos |
|---|---|
| Cliente | Solo lectura en sedes, trampas, incidencias y quejas |
| Tecnico | Lectura y escritura en operaciones diarias (sin eliminar) |
| Supervisor | Acceso completo incluyendo eliminacion y configuracion |

### Tipos de Trampa
Configurar en: ServiPro > Configuracion > Tipos de Trampa. Cada tipo tiene un codigo, nombre e icono FontAwesome que se muestra en el plano interactivo.

### Tipos de Plaga
Configurar en: ServiPro > Configuracion > Tipos de Plaga. Clasificados por categoria: volador, rastrero u otro.

### Ubicaciones
Configurar en: ServiPro > Configuracion > Ubicaciones. Catalogo de zonas/areas que se asignan a las trampas.

### Umbrales del Mapa de Calor
Configurar en cada sede, seccion "Configuracion Mapa de Calor". Define los niveles bajo, medio y alto para la escala de colores del heatmap.

## Estructura del Modulo

```
pest_control/
├── __manifest__.py
├── __init__.py
├── requirements.txt
├── models/
│   ├── pest_sede.py              # Sedes/plantas + dashboard data
│   ├── pest_blueprint.py         # Planos + widget data
│   ├── pest_trap.py              # Trampas + auto-ID
│   ├── pest_trap_type.py         # Catalogo tipos de trampa
│   ├── pest_trap_state.py        # Historial de estados
│   ├── pest_trap_movement.py     # Historial de movimientos
│   ├── pest_plague_type.py       # Catalogo tipos de plaga
│   ├── pest_incident.py          # Incidencias
│   ├── pest_evidence.py          # Evidencias fotograficas
│   ├── pest_inspection.py        # Inspecciones tecnicas
│   ├── pest_complaint.py         # Quejas
│   ├── pest_blueprint_zone.py    # Zonas poligonales del plano
│   ├── pest_zone.py              # Catalogo de ubicaciones
│   ├── pest_sale.py              # Extension de sale.order
│   ├── pest_trap_state_wizard.py # Wizard estados masivos
│   ├── pest_import_wizard.py     # Wizard import Excel
│   └── pest_trap_movement_wizard.py # Wizard movimiento
├── views/
│   ├── pest_sede_views.xml
│   ├── pest_blueprint_views.xml
│   ├── pest_trap_views.xml
│   ├── pest_incident_views.xml
│   ├── pest_dashboard_views.xml
│   ├── pest_menus.xml
│   └── ... (15 archivos XML)
├── static/
│   ├── lib/
│   │   ├── chart.umd.min.js         # Chart.js v4.4.7
│   │   ├── chartjs-plugin-datalabels.min.js
│   │   ├── pptxgenjs.min.js         # PptxGenJS v3.12.0
│   │   └── simpleheat.min.js        # Heatmap renderer
│   └── src/
│       ├── components/
│       │   ├── blueprint_canvas/     # Widget plano interactivo
│       │   ├── dashboard_chart/      # Componente grafica individual
│       │   └── pest_dashboard/       # Dashboard de analisis
│       └── css/
│           └── pest_global.scss      # Estilos globales
├── security/
│   ├── pest_security.xml             # Grupos y roles
│   └── ir.model.access.csv          # ACLs por modelo
├── data/
│   ├── pest_trap_type_data.xml       # 10 tipos de trampa
│   ├── pest_plague_type_data.xml     # 18 tipos de plaga
│   ├── pest_sequence_data.xml        # Secuencias
│   └── pest_cron_data.xml            # Cron procesamiento imagenes
├── reports/
│   ├── pest_report_traps.xml
│   ├── pest_report_incidents.xml
│   ├── pest_report_complete.xml
│   └── pest_report_visit.xml
├── controllers/
│   ├── main.py                       # Heatmap endpoint + docs
│   └── dashboard.py                  # Dashboard data (si existe)
├── tests/
│   └── test_pest_blueprint_widget.py
└── doc/
    ├── TECHNICAL_ARCHITECTURE.md
    ├── USER_MANUAL.md
    └── CONTRIBUTING.md
```

## Modelos de Datos

```
pest.sede
├── pest.blueprint (planos)
│   ├── pest.trap (trampas)
│   │   ├── pest.trap.state (historial estados)
│   │   ├── pest.trap.movement (historial movimientos)
│   │   └── pest.incident (incidencias)
│   ├── pest.evidence (evidencias)
│   └── pest.blueprint.zone (zonas poligonales)
├── pest.inspection (inspecciones)
└── pest.complaint (quejas)

Catalogos:
├── pest.trap.type (tipos de trampa)
├── pest.plague.type (tipos de plaga)
└── pest.zone (ubicaciones)
```

## Widget Interactivo (OWL)

El widget `BlueprintCanvas` es un componente OWL registrado como field widget para campos Binary. Se activa automaticamente en el formulario de planos.

### Funcionalidades
- Renderiza la imagen del plano con marcadores de trampas posicionados por coordenadas porcentuales
- Modo edicion (toggle) para crear y mover trampas
- Popover contextual con posicionamiento inteligente (se adapta a los bordes)
- SVG overlay para zonas poligonales
- Canvas overlay para mapa de calor (simpleheat)
- Panel lateral con filtros combinados (tipo + estado + busqueda)
- Mini-tabla de detalle con ultimas incidencias y estados

### Servicios OWL utilizados
- `orm`: Llamadas RPC al backend
- `action`: Apertura de formularios y acciones
- `notification`: Mensajes toast
- `dialog`: Dialogos de confirmacion nativos de Odoo

## Dashboard de Graficas

El dashboard es un componente OWL (`PestDashboard`) registrado como client action. Utiliza Chart.js v4 para renderizar 23 graficas organizadas en tres pestanas.

### Pestana Analisis de Sede (14 graficas)
Graficas de barras, donas y barras apiladas que muestran: comparacion de plagas por mes, distribucion por tipo de incidencia, areas con mayor incidencia, trampas con mayor captura, y analisis separado para voladores y rastreros.

### Pestana Quejas (7 graficas)
Graficas de linea, pie y barras que muestran: quejas por semana (comparacion anual), frecuencia de lineas afectadas, distribucion por tipo de insecto, clasificacion y estado.

### Pestana Ventas (2 graficas)
Graficas de barras para ventas por sede y por usuario. Requiere el modulo `sale` instalado.

## Reportes PDF

Cuatro reportes QWeb accesibles desde el menu Imprimir de los formularios:

1. **Reporte de Trampas**: Listado de trampas con tipo, ubicacion, estado y fecha de instalacion
2. **Reporte de Incidencias**: Incidencias ordenadas por fecha con tipo de plaga y cantidad
3. **Reporte Completo**: Combinacion de trampas + incidencias + estadisticas resumen
4. **Reporte de Visita Tecnica**: Datos de inspeccion con hallazgos y espacio para firmas

## Seguridad y Roles

### Grupos de Acceso
- **Cliente** (`group_pest_client`): Solo lectura
- **Tecnico** (`group_pest_technician`): CRUD sin eliminacion (hereda de Cliente)
- **Supervisor** (`group_pest_supervisor`): CRUD completo (hereda de Tecnico)

### Record Rules (pendiente)
Aislamiento multi-empresa mediante `company_id` en todos los modelos operativos. Los catalogos (tipos de trampa, tipos de plaga, ubicaciones) son compartidos entre empresas.

## Tecnologias Utilizadas

| Tecnologia | Version | Proposito |
|---|---|---|
| Odoo OWL | Nativo 19.0 | Framework reactivo para widgets interactivos |
| Chart.js | 4.4.7 | Renderizado de 23 graficas del dashboard |
| simpleheat | 0.4.0 | Mapa de calor sobre el plano |
| PptxGenJS | 3.12.0 | Exportacion de graficas a PowerPoint |
| openpyxl | 3.1.2 | Importacion/exportacion de datos Excel |
| QWeb | Nativo | Generacion de reportes PDF |
| ir.cron | Nativo | Procesamiento asincrono de imagenes |
| ir.sequence | Nativo | Generacion atomica de IDs de trampas |

## Licencia

Este modulo se distribuye bajo la licencia LGPL-3.

---

Desarrollado por ServiPro / IT Green.
