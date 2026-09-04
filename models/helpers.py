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


def _sedes_con_planos_archivados(sedes):
    """Los planos archivados de estas sedes. Base común de los dos conteos de abajo."""
    if not sedes.ids:
        return sedes.env['pest.blueprint']
    return sedes.env['pest.blueprint'].with_context(active_test=False).search([
        ('sede_id', 'in', sedes.ids), ('active', '=', False),
    ])


def contar_trampas_archivadas(sedes):
    """{id de sede: trampas que cuelgan de un plano ARCHIVADO}.

    🔑 **Existe porque arreglar solo las incidencias dejó el gemelo roto.** Al cerrar el descuadre
    de incidencias no se tocó el de trampas, y quedó peor que antes: la ficha de Bimbo Azcapotzalco
    decía 582 trampas y sus planos visibles sumaban 243 — **339 de diferencia, sin nada que la
    explicara**, mientras las incidencias de esa misma pantalla ya cuadraban.

    Es exactamente el patrón que este módulo viene persiguiendo: dos hechos hermanos, se arregla
    uno y el otro se queda viejo. Por eso los dos conteos comparten la misma base de planos
    archivados en vez de repetir la consulta.
    """
    archivados = _sedes_con_planos_archivados(sedes)
    if not archivados:
        return {}
    datos = sedes.env['pest.trap'].sudo()._read_group(
        [('blueprint_id', 'in', archivados.ids)], ['sede_id'], ['__count'],
    )
    return {sede.id: cuantas for sede, cuantas in datos}


def contar_incidencias_archivadas(sedes):
    """{id de sede: incidencias que cuelgan de un plano ARCHIVADO}.

    POR QUÉ ES UN CONTEO APARTE Y NO SE RESTA DEL TOTAL
    ---------------------------------------------------
    Al archivar un plano, sus incidencias siguen existiendo y siguen siendo del histórico de esa
    sede — pero **dejan de ser alcanzables desde la pantalla**, porque los planos archivados no se
    listan. El resultado es que la sede dice 2,289 y los planos que el usuario tiene delante suman
    2,278, sin nada que explique la diferencia.

    Medido: 16 planos archivados, 45 incidencias y 342 trampas dentro. En Bimbo Azcapotzalco son
    11; en Bimbo México Santa María, 34.

    **Descontarlas del total sería esconder histórico real para que cuadre una suma** — y de paso,
    archivar un plano por error haría desaparecer sus datos del total sin que nada avise. Se
    cuentan aparte y se dicen en pantalla: *«2,289, de las cuales 11 en planos archivados»*.
    Ningún dato se pierde y el número deja de parecer un error.
    """
    archivados = _sedes_con_planos_archivados(sedes)
    if not archivados:
        return {}
    datos = sedes.env['pest.incident'].sudo()._read_group(
        [('blueprint_id', 'in', archivados.ids)], ['sede_id'], ['__count'],
    )
    return {sede.id: cuantas for sede, cuantas in datos}


def solo_si_puede(operacion='read'):
    """Decorador para métodos llamables por RPC: comprueba el permiso ANTES de ejecutar.

    EL AGUJERO QUE CIERRA
    ---------------------
    Odoo protege la LECTURA de campos y la ESCRITURA, pero **no impide invocar un método**
    sobre un registro que no puedes ver. Un cliente puede llamar por RPC a
    `pest.sede(<id de otro cliente>).get_dashboard_data()` y el método se ejecuta: devuelve
    vacío —las reglas hacen su trabajo dentro— pero **no da error**.

    Eso no filtra datos, y por eso es leve. Pero permite **averiguar qué identificadores
    existen**: uno que no existe truena de otra forma que uno que existe y no te toca. Es
    enumeración, y es de las cosas que un senior no deja abiertas «porque no filtra nada».

    Va como decorador y no copiado en cada método a propósito: son cinco hoy, y el sexto que
    alguien añada nace protegido solo si el guard es una pieza y no una costumbre.

    Detectado por una auditoría independiente el 2026-09-04.
    """
    def envolver(metodo):
        from functools import wraps

        @wraps(metodo)
        def interior(self, *args, **kwargs):
            if self.ids:
                self.check_access(operacion)
            return metodo(self, *args, **kwargs)
        return interior
    return envolver


def etiqueta_de(env, modelo, campo, valor):
    """La etiqueta que el usuario lee, no el valor que guarda la base.

    Un `Selection` guarda `en_reparacion` y muestra «En Reparación». Si el valor crudo llega a la
    pantalla, el cliente lee `en_reparacion` —con guion bajo y sin acento— y el sistema parece a
    medio terminar justo donde se le está enseñando.

    Vivía en `pest.sede`, que era el sitio equivocado: el hecho «cómo se lee este valor» no es de
    las sedes, es de cualquier pantalla. Estando allí, el visor del plano no lo encontró y pintó el
    valor crudo en tres sitios. Por eso ahora está aquí, que es donde se busca un helper.
    """
    if not valor:
        return 'Sin especificar'
    etiquetas = dict(env[modelo]._fields[campo]._description_selection(env))
    return etiquetas.get(valor, str(valor))
