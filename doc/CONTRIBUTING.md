# Contribuyendo al Sistema `pest_control`

Este documento describe la política obligatoria para desarrolladores e ingenieros que realicen Pull Requests o cambios internos a base de datos.
Buscamos combatir firmemente el *Decadimiento Documentativo (Drift)* y la Deuda Técnica impidiendo desactualizaciones.

## 🛑 Regla de Oro (Docs-as-Code)
**Toda Pull Request (PR) o modificación formal que altere, expanda, corrija o deprecie operaciones de negocio (Python Logic) o Interacción Web de Usuario (UI/OWL), DEBE estar obligatoriamente sustentada por su respectiva actualización de documentación adjunta en este repositorio en crudo.**

### Protocolos a Cumplir si usted codifica una mejora:
1. **Modelos & Base de datos Nuevas / Borradas:** Entrar Inmediatamente a `doc/TECHNICAL_ARCHITECTURE.md` y actualizar/corregir las ramas y tipos de datos del **Diagrama Mermaid ERD**.
2. **Nuevos Botones, Opciones Clicks (UX/UI):** Entrar al `doc/USER_MANUAL.md` para instruir a personal administrativo y técnico como presionar o invocar su nueva característica. Documente qué *Rol de Seguridad de Odoo* tiene visibilidad para poder dar Click.
3. **Reducción de Tiempo de Cómputo (Performance):** Reportar brevemente en el archivo `doc/TECHNICAL_ARCHITECTURE.md` cómo operó y optimizó los bloques de código o re-escrituras `raw SQL` para salvaguardar el conocimiento algorítmico al próximo relevo.

### Violaciones de Estándar
Cualquier alteración grave al sistema que intente pasar aprobación evadiendo el marco de documentación se catalogará con la etiqueta de riesgo *Docs Stale*, bloqueando sumariamente la integración al hilo de despliegue Productivo de ServiPro en las sucursales del Framework.
