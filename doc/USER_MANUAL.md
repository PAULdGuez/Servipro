# Manual de Usuario: Sistema de Control de Plagas ServiPro

Bienvenido al Manual de Usuario del módulo `pest_control`. Este documento explica las funciones principales del sistema para gestionar recintos, planos interactivos, trampas y eventos relacionados con incidencias de plagas.

## 1. Tipos de Accesos y Roles
El sistema detecta automáticamente los permisos que tu cuenta corporativa tiene asignados y ajusta las funcionalidades visibles en pantalla:
*   👤 **Sólo Lectura (Cliente/Auditor)**: Puede ver los planos interactivos, la ubicación visual de las trampas con sus estados mediante colores para hacer recorridos pasivos, y consultar métricas/reportes en *solo visualización*.
*   🔧 **Técnico Operario**: Todo lo del auditor, además de interactuar físicamente usando la pantalla o el teclado para fijar, mover y agregar nuevas trampas al plano. Puede levantar y registrar incidencias fotográficas in-situ usando dispositivos móviles.
*   👑 **Gerente/Supervisor**: Todo lo del técnico, agregando la responsabilidad de marcar una "Revisión Supervisada" en las evidencias recogidas y gestionar permisos para plantas ajenas.

## 2. Acceso Diario y Navegación
Todos los menús del módulo están anclados bajo la pestaña superior: **Control de Plagas -> Operaciones**.

1.  **Sedes**: Organiza las locaciones maestras de tus corporativos o naves industriales.
2.  **Planos**: Administra las vistas aéreas o croquis arquitectónicos (`.JPG`, `.PNG`) vinculados a cada Sede.
3.  **Trampas**: El inventario consolidado de toda tu red de control, con su historial histórico de movimientos.
4.  **Incidencias**: Visor y generador de eventos urgentes o periódicos reportados por las trampas.

## 3. Guía: El Plano Interactivo
El módulo cuenta con un tablero visual interactivo (Canvas) que renderiza el mapa de tu Sede, disponible bajo la ventana de detalles de cualquier _Plano_.

### ¿Cómo Operar el Plano con el Ratón?
*   Para **mover una trampa**: Simplemente haz click sostenido en tu ratón, arrástrala mediante el plano hasta una nueva zona, y sueltala. El cambio se guarda instantáneamente en toda la base de datos empresarial de Odoo.
*   Para **revisar el estado**: Pasa el ratón (hover) sobre el pincho de la trampa. Se autodesplegará una tarjeta flotante inteligente que revela: Identificador de Trampa, Tipo de Trampa, y su Estatus Operativo en tiempo real.

### Código de Colores Semántico
*   🟢 **Verde** (Funciona): La inspección reciente documenta trabajo normal.
*   🟡 **Amarillo** (En Reparación): Bajo mantenimiento.
*   🔴 **Rojo** (No Funciona): Operatividad perdida, requiere sustitución.
*   🔘 **Gris** (Sin Registro): Trampa recién instalada a la que jamás se le ha levantado reporte de incidencias o inspecciones.

### Accesibilidad para Lectores de Pantalla y Navegación Universal
Diseñamos el mapa pensando en todas las capacidades físicas (estándares W3C A11Y):
*   Presiona la tecla `Tabulador (TAB)` para entrar al plano y mover el foco sin usar el ratón.
*   Presiona `Enter` o `Espacio` con el foco en el plano vacío para crear una **nueva trampa** en el centro del campo de visión. Se abrirá automáticamente un formulario modal.
*   Para personas usando software tipo *VoiceOver/NVDA*, el sistema describe auditivamente la posición exacta y el nivel de salud de la trampa enfocada.

## 4. Evidencias e Inspecciones (Flujo Supervisor)
Cuando se atrapa a una plaga objetivo, el técnico creará una `Incidencia`, enlazando la trampa afectada, fecha, y **Evidencia Fotográfica**. 

El registro no se contará como completado en las barras de progreso analíticas, hasta que un usuario que posea Rol de *Gerente/Supervisor* entre al detalle y firme usando click en el *checkbox*  aprobatorio.
