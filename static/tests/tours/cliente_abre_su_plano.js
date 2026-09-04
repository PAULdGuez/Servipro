/** Un cliente entra, abre el plano de su planta y ve sus trampas.
 *
 * ⚠️ ESTADO: en el entorno LOCAL este tour se SALTA — no hay navegador funcional
 * dentro del contenedor. Odoo lo omite y el resumen sigue diciendo «0 failed»,
 * así que parecía estar pasando cuando en realidad nunca se ejecutó. Se descubrió
 * poniéndole un paso imposible y viendo que seguía en verde.
 *
 * En odoo.sh sí corre, porque su entorno trae Chrome. Aquí queda como protección
 * para allá, no como red local.
 *
 * 🔑 Antes de confiar en cualquier tour: ponle un selector inexistente y comprueba
 * que el test FALLA. Si no falla, no se está ejecutando.
 *
 * Es el flujo que estuvo roto: al Cliente le faltaba permiso sobre los catálogos
 * de tipo de trampa y de plaga, y el plano tronaba con un error de acceso.
 *
 * Un tour prueba lo que un test de modelo no ve: que la pantalla CARGUE de verdad,
 * con sus componentes montados, entrando por donde entra el usuario.
 */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pest_cliente_abre_su_plano", {
    url: "/odoo",
    steps: () => [
        {
            content: "Entrar a ServiPro desde el menú de aplicaciones",
            trigger: ".o_app[data-menu-xmlid='pest_control.pest_control_menu_root']",
            run: "click",
        },
        {
            content: "Abrir Operaciones",
            trigger: "button[data-menu-xmlid='pest_control.pest_control_menu_operations']",
            run: "click",
        },
        {
            content: "Ir a Planos",
            trigger: ".dropdown-item[data-menu-xmlid='pest_control.pest_control_menu_blueprints']",
            run: "click",
        },
        {
            content: "Abrir el primer plano de la lista",
            trigger: ".o_list_view .o_data_row:first-child .o_data_cell",
            run: "click",
        },
        {
            // 🔑 El paso que importa, y el selector NO puede ser laxo.
            //
            // Un primer intento usaba `[class*='blueprint']`, que matchea hasta el
            // formulario vacío: el tour pasaba aunque el widget no montara. Se comprobó
            // quitando el permiso del Cliente — los tests de modelo caían y el tour NO.
            // Un tour que pasa con el flujo roto es peor que no tenerlo.
            //
            // `blueprint-trap-marker` solo existe si el widget montó Y dibujó una trampa,
            // que es exactamente lo que fallaba sin los catálogos.
            content: "El plano dibuja sus trampas (no basta con que cargue la ficha)",
            trigger: ".blueprint-container .blueprint-trap-marker",
        },
    ],
});
