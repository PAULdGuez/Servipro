from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    """Qué sedes puede ver cada persona.

    POR QUÉ EN LA FICHA DEL USUARIO Y NO EN UNA PANTALLA APARTE
    -----------------------------------------------------------
    Al dar de alta a alguien, en la MISMA pantalla donde se elige su rol se marcan sus sedes. Un
    menú separado obliga a recordar que hay un segundo paso, y el segundo paso que nadie ve es el
    que no se hace — con el agravante de que aquí «no hacerlo» deja a la persona sin ver nada.

    EL CORTE ES FAIL-CLOSED, Y ES DELIBERADO
    ----------------------------------------
    Un cliente sin sedes marcadas **no ve nada**, ni siquiera lo de su propia empresa. Al revés
    —que sin marcar nada lo vea todo— un alta a medias se convierte en una fuga silenciosa que
    nadie descubre. Así se nota el primer día. Para que no sorprenda, guardar sin sedes **avisa en
    la misma pantalla**.
    """
    _inherit = 'res.users'

    pest_sede_ids = fields.Many2many(
        'pest.sede',
        'pest_sede_users_rel', 'user_id', 'sede_id',
        string='Sedes que puede ver',
        # 🔴 `groups=` NO es cosmética aquí: sin él, **la pantalla de usuarios de Odoo se rompe
        # para cualquier administrador que no pertenezca a este módulo.** Al abrir la ficha de
        # alguien, Odoo intenta leer este campo, no tiene permiso sobre `pest.sede` y lanza un
        # error de acceso — no puede abrir a NADIE.
        #
        # Con `groups`, Odoo omite el campo para quien no está en el grupo, en vez de intentar
        # leerlo y fallar. Se descubrió navegando: 41 pruebas en verde no lo vieron, porque
        # todas creaban usuarios CON los grupos del módulo. Nunca uno sin ellos, que es
        # exactamente el administrador que instala el sistema.
        groups='pest_control.group_pest_client',
        help='Las plantas de las que esta persona puede ver información. '
             'Si no se marca ninguna, no verá ninguna.',
    )
    pest_es_personal = fields.Boolean(
        string='Es personal de ServiPro',
        compute='_compute_pest_es_personal',
        help='El personal de la empresa de servicio ve todas las sedes sin asignarlas una por una.',
    )

    @api.depends('group_ids')
    def _compute_pest_es_personal(self):
        grupo = self.env.ref('pest_control.group_pest_staff', raise_if_not_found=False)
        for user in self:
            user.pest_es_personal = bool(grupo) and grupo in user.all_group_ids

    def write(self, vals):
        """Un reemplazo de sedes tiene que reemplazarlas TODAS, archivadas incluidas.

        🔴 **El agujero que cierra:** un Many2many escribe sobre lo que ve, y por defecto no ve
        los archivados. Un `(6, 0, [...])` —el comando que manda la pantalla al reemplazar la
        lista— **deja dentro las sedes archivadas**. Quien quita todas las sedes de un usuario
        cree habérselo quitado todo, y el usuario conserva acceso al histórico de las archivadas
        sin que nada lo muestre.

        Medido en la base real: al dejar a un usuario con una sola planta, conservó 3 sedes
        archivadas y 139 trampas de más.

        La vista ya las muestra para que el administrador las vea, pero eso es comodidad: por RPC
        o por importación se entra por debajo de la pantalla. Esto es la regla.
        """
        resultado = super().write(vals)

        comandos = vals.get('pest_sede_ids')
        reemplazo = [c for c in (comandos or []) if isinstance(c, (list, tuple)) and c[0] == 6]
        if reemplazo:
            nuevas = list(reemplazo[-1][2] or [])
            # 🔑 Se borra la fila de la tabla de relación con SQL. No es capricho: el comando
            # «desvincular» del ORM **también** filtra los archivados, así que quitarlos por ahí
            # no funciona — se probó. Una tabla de relación pura no tiene reglas ni lógica de
            # negocio que saltarse: solo pares de identificadores.
            #
            # Va parametrizado, nunca interpolado.
            self.env.cr.execute(
                'DELETE FROM pest_sede_users_rel WHERE user_id IN %s'
                + (' AND sede_id NOT IN %s' if nuevas else ''),
                (tuple(self.ids),) + ((tuple(nuevas),) if nuevas else ()),
            )
            # `pest.sede` no declara el lado inverso, así que solo hay que invalidar este.
            self.invalidate_recordset(['pest_sede_ids'])
        return resultado

    @api.constrains('pest_sede_ids')
    def _check_sedes_de_su_empresa(self):
        """No se le puede asignar a alguien de Bimbo una planta de Totis, ni por error.

        La vista ya filtra el desplegable, pero un `domain` de vista no es una garantía: por RPC o
        por importación se entra por debajo. La vista es comodidad; esto es la regla.
        """
        for user in self:
            ajenas = user.pest_sede_ids.filtered(
                lambda s: s.company_id and s.company_id not in user.company_ids)
            if ajenas:
                raise ValidationError(_(
                    'No se puede dar acceso a %(sedes)s: pertenecen a una empresa distinta '
                    'de las de %(usuario)s.',
                    sedes=', '.join(ajenas.mapped('name')), usuario=user.name,
                ))

    def _sedes_visibles_del_usuario(self):
        """Los ids de sede que ESTE usuario puede ver. **El único sitio donde se decide.**

        Lo consultan las reglas de registro de los once modelos que cuelgan de una sede. Si cada
        una lo resolviera por su cuenta, el día que cambie el criterio habría que acordarse de
        once sitios — y el que se olvide es justo por donde se escapa el dato.

        🔴 **Las reglas que lo usan son GLOBALES, y no es un detalle.** Odoo une con **OR** las
        reglas de un mismo modelo que apliquen por grupo: basta cumplir UNA. Como ya existía la
        regla «solo tu empresa» sobre el grupo Cliente, añadir el corte por sede como otra regla
        de grupo **no restringía nada** — la de empresa dejaba pasar las 16 sedes de Bimbo, y el
        recorte parecía instalado y no recortaba. Las globales se unen con **AND**, que es lo que
        hace falta para acumular dos condiciones.

        🔴 **Trabaja sobre `self`, NUNCA sobre `self.env.user`.** Odoo evalúa el `domain_force` de
        una `ir.rule` **con el entorno del superusuario** e inyecta al usuario real en la variable
        `user`. Si aquí dentro se preguntara por `self.env.user`, la respuesta sería OdooBot —que
        es superusuario— y el método devolvería «sin recorte» para todo el mundo.

        Y ese fallo **no se nota**: la regla existe, está activa, su dominio se ve correcto en la
        pantalla de reglas, y no recorta nada. Una función de seguridad que no protege es peor que
        no tenerla, porque nadie vuelve a mirarla.
        """
        self.ensure_one()
        if self._is_superuser() or self.pest_es_personal:
            # Todas las sedes **de sus empresas**, no «None» ni todas las del sistema.
            #
            # No «None» porque la regla es GLOBAL —tiene que serlo, ver abajo— y una global se
            # evalúa siempre: devolver «sin recorte» dejaría el dominio vacío y el personal de
            # ServiPro sería el único que no vería nada.
            #
            # Y **de sus empresas**, no todas: con `search([])` a secas se colaron las sedes de la
            # empresa de demostración en la vista del personal, que es exactamente saltarse la
            # regla de empresa por la puerta que abrimos para arreglar otra cosa.
            # `active_test=False` por la misma razón que en la migración: una sede archivada
            # sigue teniendo trampas e incidencias, y el personal tiene que poder llegar a su
            # histórico. Sin esto, archivar una sede se la esconde también a quien la gestiona.
            return self.env['pest.sede'].sudo().with_context(active_test=False).search(
                [('company_id', 'in', self.company_ids.ids)]).ids
        # ⚠️ **`active_test=False` también AQUÍ, al leer el campo.** Un Many2many filtra los
        # archivados al leerse, no solo al buscarse: con las 19 sedes de Bimbo asignadas
        # —16 activas y 3 archivadas— este `.ids` devolvía 16, y las 139 trampas de las
        # archivadas desaparecían del corte.
        #
        # Es la TERCERA vez que lo archivado muerde en esta misma función: al buscar las sedes
        # del personal, al asignarlas en la migración, y al leerlas aquí. ⇒ En cuanto algo
        # filtra por una LISTA de registros, hay que preguntarse qué pasa con los archivados
        # en cada uno de los tres momentos: buscar, guardar y leer.
        return self.with_context(active_test=False).pest_sede_ids.ids   # vacío = no ve nada
