/*
 * ROLE VISIBILITY CONTROLLER v1
 *
 * GUEST -> Project Overview only
 * USER  -> Sections 3-7 only
 * ADMIN -> Sections 9-10 only
 */

(function () {
    "use strict";


    const VALID_ROLES =
        new Set([
            "GUEST",
            "USER",
            "ADMIN",
        ]);


    function normalizeRole(value) {

        const role =
            String(
                value || ""
            )
            .trim()
            .toUpperCase();

        if (
            VALID_ROLES.has(
                role
            )
        ) {
            return role;
        }

        return "GUEST";
    }


    function applyRoleVisibility(role) {

        const normalizedRole =
            normalizeRole(
                role
            );

        document.body.dataset.appRole =
            normalizedRole;
    }


    window.addEventListener(
        "lungxray:auth-user",
        function (event) {

            const user =
                event
                && event.detail
                && event.detail.user
                    ? event.detail.user
                    : null;

            applyRoleVisibility(
                user
                    ? user.role
                    : "GUEST"
            );
        }
    );


    window.addEventListener(
        "lungxray:auth-guest",
        function () {

            applyRoleVisibility(
                "GUEST"
            );
        }
    );


    window.LungXrayRoleVisibility =
        Object.freeze({
            applyRoleVisibility:
                applyRoleVisibility,
        });


    applyRoleVisibility(
        "GUEST"
    );

})();
