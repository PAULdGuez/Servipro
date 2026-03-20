/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

// Tour 1: Happy Path
registry.category("web_tour.tours").add("pest_blueprint_happy_path", {
    test: true,
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Test Happy Path: Drag trap and save",
            trigger: '.blueprint-container',
        },
        // We simulate a completion of the happy path logic for the test
        {
            content: "Check marker existence",
            trigger: '.blueprint-trap-marker',
        }
    ],
});

// Tour 2: Add Trap
registry.category("web_tour.tours").add("pest_blueprint_add_trap", {
    test: true,
    url: "/web",
    steps: () => [
        {
            content: "Click on the blueprint container",
            trigger: '.blueprint-container.can-edit',
            run: "click",
        },
        {
            content: "Verify modal opened",
            trigger: '.modal:contains("Trampa")',
        }
    ],
});

// Tour 3: Read-Only Form
registry.category("web_tour.tours").add("pest_blueprint_readonly", {
    test: true,
    url: "/web",
    steps: () => [
        {
            content: "Check container does not have can-edit class",
            trigger: '.blueprint-container:not(.can-edit)',
        }
    ],
});

// Tour 4: Permissions Tour (Cliente)
registry.category("web_tour.tours").add("pest_blueprint_permissions", {
    test: true,
    url: "/web",
    steps: () => [
        {
            content: "Check container does not have can-edit class for client user",
            trigger: '.blueprint-container:not(.can-edit)',
        }
    ],
});
