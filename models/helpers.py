"""Helpers compartidos. **Consúltalos antes de derivar cualquier hecho.**

POR QUÉ EXISTE ESTE ARCHIVO
---------------------------
No es organización: es que el módulo ya tenía **tres cálculos distintos para el mismo hecho**, y
daban tres números distintos sobre los datos reales.

«¿Cuántas incidencias tiene esto?» se contestaba de tres formas:

- La **sede** contaba por `sede_id` — le entraban todas.
- El **plano** no contaba: *sumaba* el contador de cada una de sus trampas, así que las
  incidencias **sin trampa** (los hallazgos sueltos) se le escapaban. Y además **ignoraba
  `blueprint_id`**, el campo que existe justo para eso.
- La **trampa** contaba por `trap_id`.

Medido sobre los datos de producción: **Bimbo Azcapotzalco decía 2,289 en la ficha de la sede y
2,278 sumando sus planos. Bimbo México Santa María, 380 contra 346.**

Ninguno de los tres estaba «mal» leído por separado. Ese es justo el problema: **dos cálculos que
opinan lo mismo no fallan al nacer, fallan al arreglarse** — alguien corrige uno, el otro se queda
viejo, y el viejo es el que sigue dando el número que nadie cuadra.

LA REGLA
--------
**Un hecho, un lugar donde se decide.** Antes de escribir un `compute` que derive algo —un
conteo, un estado, una vigencia, un total— **grep por el HECHO que responde, no por el nombre que
le ibas a poner**. Si de verdad hacen falta dos, que uno llame al otro.
"""


def dominio_incidencias(registro):
    """El dominio de «las incidencias de esto», sea una sede, un plano o una trampa.

    Es el ÚNICO sitio donde se decide qué incidencias pertenecen a qué. Que el contador y la
    lista que abre el botón salgan de aquí es lo que impide que el número diga 8 y la lista
    muestre 7 — y a partir de ahí nadie vuelve a creerle a ningún número de la pantalla.
    """
    campo = {
        'pest.sede': 'sede_id',
        'pest.blueprint': 'blueprint_id',
        'pest.trap': 'trap_id',
    }.get(registro._name)
    if not campo:
        raise ValueError(
            'No sé contar incidencias de %s. Añádelo aquí, no escribas otro cálculo.'
            % registro._name
        )
    return [(campo, 'in', registro.ids)]


def contar_incidencias(registros):
    """{id: nº de incidencias} para sedes, planos o trampas.

    Una sola consulta agrupada para todo el conjunto — no una por registro.
    """
    if not registros.ids:
        return {}
    campo = dominio_incidencias(registros)[0][0]
    datos = registros.env['pest.incident'].sudo()._read_group(
        dominio_incidencias(registros), [campo], ['__count'],
    )
    return {agrupado.id: cuantas for agrupado, cuantas in datos}
