(() => {
    "use strict";

    const HEARTBEAT_INTERVAL_MS =
        60 * 1000;

    const VISITOR_KEY =
        "lungxray_visitor_id_v1";

    const SESSION_KEY =
        "lungxray_visit_session_id_v1";

    const onlineNowElement =
        document.getElementById(
            "visitor-online-now"
        );

    const onlineTodayElement =
        document.getElementById(
            "visitor-online-today"
        );

    const totalVisitsElement =
        document.getElementById(
            "visitor-total-visits"
        );


    if (
        !onlineNowElement
        || !onlineTodayElement
        || !totalVisitsElement
    ) {
        return;
    }


    const numberFormatter =
        new Intl.NumberFormat(
            "vi-VN"
        );


    function createUuid() {

        if (
            window.crypto
            && typeof (
                window.crypto.randomUUID
            ) === "function"
        ) {
            return (
                window.crypto
                .randomUUID()
            );
        }


        return (
            "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
            .replace(
                /[xy]/g,
                (character) => {
                    const random =
                        Math.floor(
                            Math.random()
                            * 16
                        );

                    const value =
                        character === "x"
                            ? random
                            : (
                                random
                                & 0x3
                            )
                            | 0x8;

                    return value.toString(
                        16
                    );
                }
            )
        );
    }


    function getOrCreateId(
        storage,
        key
    ) {

        try {
            const existing =
                storage.getItem(
                    key
                );

            if (existing) {
                return existing;
            }

            const created =
                createUuid();

            storage.setItem(
                key,
                created
            );

            return created;
        }
        catch {
            return createUuid();
        }
    }


    const visitorId =
        getOrCreateId(
            window.localStorage,
            VISITOR_KEY
        );

    const sessionId =
        getOrCreateId(
            window.sessionStorage,
            SESSION_KEY
        );


    function renderStats(
        stats
    ) {

        onlineNowElement.textContent =
            numberFormatter.format(
                Number(
                    stats.online_now
                    || 0
                )
            );

        onlineTodayElement.textContent =
            numberFormatter.format(
                Number(
                    stats.online_today
                    || 0
                )
            );

        totalVisitsElement.textContent =
            numberFormatter.format(
                Number(
                    stats.total_visits
                    || 0
                )
            );
    }


    async function loadPublicStats() {

        const response =
            await fetch(
                "/api/v1/visitor-stats",
                {
                    method: "GET",
                    cache: "no-store",
                    credentials:
                        "same-origin",
                }
            );

        if (!response.ok) {
            throw new Error(
                "Visitor stats request failed."
            );
        }

        renderStats(
            await response.json()
        );
    }


    async function heartbeat() {

        try {
            const response =
                await fetch(
                    (
                        "/api/v1/"
                        + "visitor-stats/"
                        + "heartbeat"
                    ),
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    visitor_id:
                                        visitorId,

                                    session_id:
                                        sessionId,
                                }
                            ),

                        cache: "no-store",

                        credentials:
                            "same-origin",
                    }
                );


            if (!response.ok) {
                throw new Error(
                    "Visitor heartbeat failed."
                );
            }


            renderStats(
                await response.json()
            );
        }
        catch {
            try {
                await loadPublicStats();
            }
            catch {
                // Keep the last known values.
            }
        }
    }


    void heartbeat();


    window.setInterval(
        () => {
            void heartbeat();
        },
        HEARTBEAT_INTERVAL_MS
    );


    document.addEventListener(
        "visibilitychange",
        () => {
            if (
                document.visibilityState
                === "visible"
            ) {
                void heartbeat();
            }
        }
    );
})();
