(() => {
    "use strict";


    const STORAGE_KEY =
        "lungxray.auth.access_token";


    const fieldDefinitions = [
        [
            "current_complaint_hpi",
            "mhi-current-complaint",
            "Current Complaint / HPI",
        ],
        [
            "past_medical_history",
            "mhi-past-medical-history",
            "Past Medical History",
        ],
        [
            "past_medication_history",
            "mhi-past-medication-history",
            "Past Medication History",
        ],
        [
            "allergy_history",
            "mhi-allergy-history",
            "Allergy History",
        ],
        [
            "diseases",
            "mhi-diseases",
            "Diseases",
        ],
        [
            "smoking_status",
            "mhi-smoking-status",
            "Smoking",
        ],
        [
            "alcohol_status",
            "mhi-alcohol-status",
            "Alcohol",
        ],
        [
            "occupational_exposure",
            "mhi-occupational-exposure",
            "Occupational Exposure",
        ],
        [
            "diet",
            "mhi-diet",
            "Diet",
        ],
        [
            "appetite",
            "mhi-appetite",
            "Appetite",
        ],
        [
            "sleep",
            "mhi-sleep",
            "Sleep",
        ],
        [
            "exercise",
            "mhi-exercise",
            "Exercise",
        ],
        [
            "bowel_bladder",
            "mhi-bowel-bladder",
            "Bowel / Bladder",
        ],
        [
            "habits",
            "mhi-habits",
            "Habits",
        ],
        [
            "family_history",
            "mhi-family-history",
            "Family History",
        ],
    ];


    const fields =
        fieldDefinitions.map(
            (
                [
                    key,
                    id,
                    label,
                ]
            ) => {
                return {
                    key,
                    label,
                    element:
                        document.getElementById(
                            id
                        ),
                };
            }
        );


    const editorSource =
        document.getElementById(
            "mhi-editor-source"
        );

    const editorStatus =
        document.getElementById(
            "mhi-editor-status"
        );

    const updateButton =
        document.getElementById(
            "mhi-update-button"
        );

    const createButton =
        document.getElementById(
            "mhi-create-button"
        );

    const clearButton =
        document.getElementById(
            "mhi-clear-button"
        );

    const limitInput =
        document.getElementById(
            "mhi-limit"
        );

    const loadButton =
        document.getElementById(
            "mhi-load-button"
        );

    const previousButton =
        document.getElementById(
            "mhi-previous-button"
        );

    const nextButton =
        document.getElementById(
            "mhi-next-button"
        );

    const historyStatus =
        document.getElementById(
            "mhi-history-status"
        );

    const results =
        document.getElementById(
            "mhi-results"
        );


    if (
        fields.some(
            (field) => {
                return !field.element;
            }
        )
        || !editorSource
        || !editorStatus
        || !updateButton
        || !createButton
        || !clearButton
        || !limitInput
        || !loadButton
        || !previousButton
        || !nextButton
        || !historyStatus
        || !results
    ) {
        console.error(
            "Medical History UI initialization failed."
        );

        return;
    }


    let currentUser =
        null;

    let latestHistoryId =
        null;

    let editing =
        false;

    let currentOffset =
        0;

    let currentHasMore =
        false;

    let historyLoaded =
        false;


    function getToken() {
        const stored =
            String(
                sessionStorage.getItem(
                    STORAGE_KEY
                )
                || ""
            ).trim();


        if (stored) {
            return stored;
        }


        const tokenInput =
            document.getElementById(
                "token-input"
            );


        if (!tokenInput) {
            return "";
        }


        return String(
            tokenInput.value
            || ""
        )
            .replace(
                /^Bearer\s+/i,
                ""
            )
            .trim();
    }


    async function parseResponse(
        response
    ) {
        const text =
            await response.text();


        if (!text) {
            return {};
        }


        try {
            return JSON.parse(
                text
            );

        } catch {
            return {
                detail:
                    text,
            };
        }
    }


    function errorMessage(
        payload
    ) {
        if (
            payload
            && typeof (
                payload.detail
            ) === "string"
        ) {
            return payload.detail;
        }


        return "Request failed.";
    }


    async function request(
        path,
        options = {}
    ) {
        const token =
            getToken();


        if (!token) {
            throw new Error(
                "Please sign in first."
            );
        }


        const headers = {
            Authorization:
                `Bearer ${token}`,
            ...(
                options.headers
                || {}
            ),
        };


        const response =
            await fetch(
                path,
                {
                    ...options,
                    headers,
                }
            );


        const payload =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                errorMessage(
                    payload
                )
            );
        }


        return payload;
    }


    function setEditing(
        enabled
    ) {
        editing =
            Boolean(
                enabled
            );


        for (
            const field
            of fields
        ) {
            field.element.readOnly =
                !editing;
        }


        updateButton.disabled =
            (
                !currentUser
                || editing
            );

        createButton.disabled =
            (
                !currentUser
                || !editing
            );

        clearButton.disabled =
            !currentUser;
    }


    function clearFields() {
        for (
            const field
            of fields
        ) {
            field.element.value =
                "";
        }
    }


    function populateEditor(
        history
    ) {
        for (
            const field
            of fields
        ) {
            const sourceValue =
                history[
                    field.key
                ];

            field.element.value =
                (
                    Array.isArray(
                        sourceValue
                    )
                        ? sourceValue.join(", ")
                        : (
                            sourceValue
                            ?? ""
                        )
                );
        }


        latestHistoryId =
            history.id;


        editorSource.textContent =
            (
                "Latest source: Medical History #"
                + history.id
                + " ? "
                + formatDate(
                    history.recorded_at
                )
            );


        setEditing(
            false
        );
    }


    function buildPayload() {
        const payload = {};


        for (
            const field
            of fields
        ) {
            const value =
                field.element
                    .value
                    .trim();


            if (
                field.key === "diseases"
            ) {
                const items =
                    value
                        ? value
                            .split(/[,;\n]+/)
                            .map(
                                item =>
                                    item.trim()
                            )
                            .filter(Boolean)
                        : [];

                payload[
                    field.key
                ] = (
                    items.length
                        ? items
                        : null
                );
            }
            else {
                payload[
                    field.key
                ] = (
                    value
                    || null
                );
            }
        }


        return payload;
    }


    function normalizeDate(
        value
    ) {
        const text =
            String(
                value
                || ""
            ).trim();


        if (!text) {
            return "";
        }


        if (
            /(?:Z|[+-]\d{2}:\d{2})$/.test(
                text
            )
        ) {
            return text;
        }


        return text + "Z";
    }


    function formatDate(
        value
    ) {
        const normalized =
            normalizeDate(
                value
            );


        if (!normalized) {
            return "?";
        }


        const date =
            new Date(
                normalized
            );


        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return String(
                value
            );
        }


        return date.toLocaleString();
    }


    async function loadLatest() {
        editorStatus.textContent =
            (
                "Loading latest "
                + "Medical History..."
            );


        try {
            const page =
                await request(
                    (
                        "/api/v1/"
                        + "medical-histories/"
                        + "intake?limit=1&offset=0"
                    )
                );


            if (
                Array.isArray(
                    page.items
                )
                && page.items.length > 0
            ) {
                populateEditor(
                    page.items[0]
                );


                editorStatus.textContent =
                    (
                        "Latest Medical History "
                        + "loaded automatically."
                    );

                return;
            }


            latestHistoryId =
                null;

            clearFields();

            editorSource.textContent =
                "No Medical History exists yet.";

            setEditing(
                true
            );


            editorStatus.textContent =
                (
                    "No Medical History found. "
                    + "Enter information and "
                    + "Create History."
                );

        } catch (error) {
            editorStatus.textContent =
                (
                    "Medical History auto-load failed: "
                    + error.message
                );
        }
    }


    function getLimit() {
        const limit =
            Number.parseInt(
                limitInput.value,
                10
            );


        if (
            !Number.isInteger(
                limit
            )
            || limit < 1
            || limit > 100
        ) {
            throw new Error(
                "Limit must be between 1 and 100."
            );
        }


        return limit;
    }


    function createHistoryCard(
        history
    ) {
        const card =
            document.createElement(
                "article"
            );

        card.className =
            "medical-history-card";


        const header =
            document.createElement(
                "div"
            );

        header.className =
            "medical-history-card-header";


        const title =
            document.createElement(
                "strong"
            );

        title.textContent =
            (
                "Medical History #"
                + history.id
            );


        const date =
            document.createElement(
                "span"
            );

        date.textContent =
            formatDate(
                history.recorded_at
            );


        header.append(
            title,
            date
        );


        const details =
            document.createElement(
                "div"
            );

        details.className =
            "medical-history-details";


        for (
            const field
            of fieldDefinitions
        ) {
            const [
                key,
                ,
                label,
            ] = field;


            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "medical-history-detail";


            const strong =
                document.createElement(
                    "strong"
                );

            strong.textContent =
                label + ": ";


            const value =
                document.createElement(
                    "span"
                );

            const rawValue =
                history[
                    key
                ];

            value.textContent =
                (
                    Array.isArray(
                        rawValue
                    )
                        ? (
                            rawValue.length
                                ? rawValue.join(", ")
                                : "?"
                        )
                        : (
                            rawValue
                            || "?"
                        )
                );


            row.append(
                strong,
                value
            );


            details.appendChild(
                row
            );
        }


        card.append(
            header,
            details
        );


        return card;
    }


    function renderPage(
        page
    ) {
        results.replaceChildren();


        const items =
            Array.isArray(
                page.items
            )
                ? page.items
                : [];


        if (
            items.length === 0
        ) {
            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "history-empty";

            empty.textContent =
                "No Medical History records found.";


            results.appendChild(
                empty
            );

        } else {
            for (
                const history
                of items
            ) {
                results.appendChild(
                    createHistoryCard(
                        history
                    )
                );
            }
        }


        currentOffset =
            page.offset;

        currentHasMore =
            Boolean(
                page.has_more
            );

        historyLoaded =
            true;


        previousButton.disabled =
            currentOffset === 0;

        nextButton.disabled =
            !currentHasMore;


        historyStatus.textContent =
            (
                items.length
                + " Medical History record(s) loaded."
            );
    }


    async function loadPage(
        offset
    ) {
        let limit;


        try {
            limit =
                getLimit();

        } catch (error) {
            historyStatus.textContent =
                error.message;

            return;
        }


        loadButton.disabled =
            true;

        previousButton.disabled =
            true;

        nextButton.disabled =
            true;


        historyStatus.textContent =
            "Loading Medical History...";


        try {
            const page =
                await request(
                    (
                        "/api/v1/"
                        + "medical-histories/intake"
                        + "?limit="
                        + encodeURIComponent(
                            limit
                        )
                        + "&offset="
                        + encodeURIComponent(
                            offset
                        )
                    )
                );


            renderPage(
                page
            );

        } catch (error) {
            historyStatus.textContent =
                (
                    "Medical History request failed: "
                    + error.message
                );


            previousButton.disabled =
                currentOffset === 0;

            nextButton.disabled =
                !currentHasMore;

        } finally {
            loadButton.disabled =
                !currentUser;
        }
    }


    async function createHistory() {
        if (
            !editing
            || !currentUser
        ) {
            return;
        }


        createButton.disabled =
            true;

        updateButton.disabled =
            true;


        editorStatus.textContent =
            "Creating Medical History...";


        try {
            const history =
                await request(
                    (
                        "/api/v1/"
                        + "medical-histories/"
                        + "intake"
                    ),
                    {
                        method:
                            "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                buildPayload()
                            ),
                    }
                );


            populateEditor(
                history
            );


            editorStatus.textContent =
                (
                    "Medical History #"
                    + history.id
                    + " created successfully."
                );


            if (
                historyLoaded
            ) {
                currentOffset =
                    0;

                await loadPage(
                    0
                );
            }

        } catch (error) {
            setEditing(
                true
            );


            editorStatus.textContent =
                (
                    "Create History failed: "
                    + error.message
                );
        }
    }


    function resetForGuest() {
        currentUser =
            null;

        latestHistoryId =
            null;

        currentOffset =
            0;

        currentHasMore =
            false;

        historyLoaded =
            false;


        clearFields();

        results.replaceChildren();


        editorSource.textContent =
            (
                "Sign in to load your latest "
                + "Medical History."
            );

        editorStatus.textContent =
            (
                "Sign in to load your latest "
                + "medical information."
            );

        historyStatus.textContent =
            (
                "Medical histories "
                + "have not been loaded."
            );


        setEditing(
            false
        );


        updateButton.disabled =
            true;

        createButton.disabled =
            true;

        clearButton.disabled =
            true;

        loadButton.disabled =
            true;

        previousButton.disabled =
            true;

        nextButton.disabled =
            true;
    }


    async function activateUser(
        user
    ) {
        if (
            !user
            || user.role !== "USER"
        ) {
            resetForGuest();

            return;
        }


        currentUser =
            user;


        loadButton.disabled =
            false;

        clearButton.disabled =
            false;

        updateButton.disabled =
            false;


        await loadLatest();
    }


    updateButton.addEventListener(
        "click",
        () => {
            if (!currentUser) {
                return;
            }


            setEditing(
                true
            );


            editorStatus.textContent =
                (
                    "Update mode enabled. "
                    + "Edit the information, then "
                    + "click Create History "
                    + "to save a new record."
                );
        }
    );


    createButton.addEventListener(
        "click",
        createHistory
    );


    clearButton.addEventListener(
        "click",
        () => {
            if (!currentUser) {
                return;
            }


            latestHistoryId =
                null;

            clearFields();

            editorSource.textContent =
                "New blank Medical History";


            setEditing(
                true
            );


            editorStatus.textContent =
                (
                    "Editor cleared. "
                    + "Enter new information."
                );
        }
    );


    loadButton.addEventListener(
        "click",
        () => {
            currentOffset =
                0;

            void loadPage(
                0
            );
        }
    );


    previousButton.addEventListener(
        "click",
        () => {
            let limit;


            try {
                limit =
                    getLimit();

            } catch (error) {
                historyStatus.textContent =
                    error.message;

                return;
            }


            const nextOffset =
                Math.max(
                    0,
                    currentOffset
                    - limit
                );


            void loadPage(
                nextOffset
            );
        }
    );


    nextButton.addEventListener(
        "click",
        () => {
            if (!currentHasMore) {
                return;
            }


            let limit;


            try {
                limit =
                    getLimit();

            } catch (error) {
                historyStatus.textContent =
                    error.message;

                return;
            }


            void loadPage(
                currentOffset
                + limit
            );
        }
    );


    limitInput.addEventListener(
        "change",
        () => {
            currentOffset =
                0;

            previousButton.disabled =
                true;


            if (
                historyLoaded
            ) {
                void loadPage(
                    0
                );
            }
        }
    );


    window.addEventListener(
        "lungxray:auth-user",
        (event) => {
            void activateUser(
                event.detail
                    && event.detail.user
            );
        }
    );


    window.addEventListener(
        "lungxray:auth-guest",
        resetForGuest
    );


    async function initializeSession() {
        const token =
            getToken();


        if (!token) {
            resetForGuest();

            return;
        }


        try {
            const user =
                await request(
                    "/api/v1/users/me"
                );


            await activateUser(
                user
            );

        } catch {
            resetForGuest();
        }
    }


    resetForGuest();


    queueMicrotask(
        () => {
            void initializeSession();
        }
    );
})();
