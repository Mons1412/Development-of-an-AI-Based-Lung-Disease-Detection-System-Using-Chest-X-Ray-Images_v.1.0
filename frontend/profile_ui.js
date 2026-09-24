(() => {
    "use strict";


    const STORAGE_KEY =
        "lungxray.auth.access_token";


    const fullNameInput =
        document.getElementById(
            "profile-full-name"
        );

    const dateOfBirthInput =
        document.getElementById(
            "profile-date-of-birth"
        );

    const sexInput =
        document.getElementById(
            "profile-sex"
        );

    const phoneInput =
        document.getElementById(
            "profile-phone"
        );

    const emailInput =
        document.getElementById(
            "profile-email"
        );

    const heightInput =
        document.getElementById(
            "profile-height"
        );

    const weightInput =
        document.getElementById(
            "profile-weight"
        );

    const editButton =
        document.getElementById(
            "profile-edit-button"
        );

    const saveButton =
        document.getElementById(
            "profile-save-measurements-button"
        );

    const historyButton =
        document.getElementById(
            "profile-history-button"
        );

    const profileStatus =
        document.getElementById(
            "profile-status"
        );

    const historyPanel =
        document.getElementById(
            "profile-history-panel"
        );

    const historyResults =
        document.getElementById(
            "profile-history-results"
        );


    const requiredElements = [
        fullNameInput,
        dateOfBirthInput,
        sexInput,
        phoneInput,
        emailInput,
        heightInput,
        weightInput,
        editButton,
        saveButton,
        historyButton,
        profileStatus,
        historyPanel,
        historyResults,
    ];


    if (
        requiredElements.some(
            (element) => {
                return element === null;
            }
        )
    ) {
        console.error(
            "Patient Profile UI initialization failed."
        );

        return;
    }


    let profileLoaded =
        false;

    let editing =
        false;


    function normalizeToken(
        rawToken
    ) {
        const token =
            String(
                rawToken
                || ""
            ).trim();


        if (
            token
                .toLowerCase()
                .startsWith(
                    "bearer "
                )
        ) {
            return token
                .slice(
                    7
                )
                .trim();
        }


        return token;
    }


    function getAccessToken() {
        const storedToken =
            normalizeToken(
                sessionStorage.getItem(
                    STORAGE_KEY
                )
            );


        if (storedToken) {
            return storedToken;
        }


        const tokenInput =
            document.getElementById(
                "token-input"
            );


        if (!tokenInput) {
            return "";
        }


        return normalizeToken(
            tokenInput.value
        );
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


    function getErrorMessage(
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


        if (
            payload
            && Array.isArray(
                payload.detail
            )
        ) {
            return payload.detail
                .map(
                    (item) => {
                        return (
                            item.msg
                            || "Validation error"
                        );
                    }
                )
                .join(
                    "; "
                );
        }


        return "Request failed.";
    }


    function clearProfileFields() {
        fullNameInput.value =
            "";

        dateOfBirthInput.value =
            "";

        sexInput.value =
            "";

        phoneInput.value =
            "";

        emailInput.value =
            "";

        heightInput.value =
            "";

        weightInput.value =
            "";
    }


    function setEditing(
        enabled
    ) {
        editing =
            Boolean(
                enabled
            );


        fullNameInput.readOnly =
            true;

        dateOfBirthInput.readOnly =
            true;

        sexInput.disabled =
            true;

        phoneInput.readOnly =
            true;

        emailInput.readOnly =
            true;


        heightInput.readOnly =
            !editing;

        weightInput.readOnly =
            !editing;


        editButton.disabled =
            (
                !profileLoaded
                || editing
            );

        saveButton.disabled =
            (
                !profileLoaded
                || !editing
            );


        heightInput.classList.toggle(
            "profile-editing",
            editing
        );

        weightInput.classList.toggle(
            "profile-editing",
            editing
        );
    }


    function resetProfileUI() {
        profileLoaded =
            false;


        clearProfileFields();


        setEditing(
            false
        );


        editButton.disabled =
            true;

        saveButton.disabled =
            true;

        historyButton.disabled =
            true;


        historyPanel.hidden =
            true;

        historyResults
            .replaceChildren();
    }


    function populateProfile(
        profile
    ) {
        fullNameInput.value =
            (
                profile.full_name
                ?? ""
            );

        dateOfBirthInput.value =
            (
                profile.date_of_birth
                ?? ""
            );

        sexInput.value =
            (
                profile.sex
                ?? ""
            );

        phoneInput.value =
            (
                profile.phone
                ?? ""
            );

        emailInput.value =
            (
                profile.email
                ?? ""
            );

        heightInput.value =
            (
                profile.height_cm
                ?? ""
            );

        weightInput.value =
            (
                profile.weight_kg
                ?? ""
            );


        profileLoaded =
            true;


        historyButton.disabled =
            false;


        setEditing(
            false
        );
    }


    async function loadProfile() {
        const token =
            getAccessToken();


        if (!token) {
            resetProfileUI();

            profileStatus.textContent =
                (
                    "Sign in to load "
                    + "your profile."
                );

            return;
        }


        profileStatus.textContent =
            "Loading patient profile...";


        try {
            const response =
                await fetch(
                    "/api/v1/patient-profile/me",
                    {
                        method:
                            "GET",

                        headers: {
                            Authorization:
                                `Bearer ${token}`,
                        },
                    }
                );


            const payload =
                await parseResponse(
                    response
                );


            if (!response.ok) {
                throw new Error(
                    getErrorMessage(
                        payload
                    )
                );
            }


            populateProfile(
                payload
            );


            profileStatus.textContent =
                (
                    "Patient profile "
                    + "loaded automatically."
                );

        } catch (error) {
            resetProfileUI();

            profileStatus.textContent =
                (
                    "Profile load failed: "
                    + error.message
                );
        }
    }


    function readMeasurement(
        input,
        label,
        maximum
    ) {
        const value =
            Number(
                input.value
            );


        if (
            !Number.isFinite(
                value
            )
            || value <= 0
            || value > maximum
        ) {
            throw new Error(
                label
                + " is invalid."
            );
        }


        return value;
    }


    async function saveProfile() {
        if (
            !profileLoaded
            || !editing
        ) {
            return;
        }


        const token =
            getAccessToken();


        if (!token) {
            profileStatus.textContent =
                "Please sign in first.";

            return;
        }


        let heightValue;
        let weightValue;


        try {
            heightValue =
                readMeasurement(
                    heightInput,
                    "Height",
                    300
                );

            weightValue =
                readMeasurement(
                    weightInput,
                    "Weight",
                    500
                );

        } catch (error) {
            profileStatus.textContent =
                error.message;

            return;
        }


        editButton.disabled =
            true;

        saveButton.disabled =
            true;

        historyButton.disabled =
            true;


        profileStatus.textContent =
            "Saving patient profile...";


        try {
            const response =
                await fetch(
                    (
                        "/api/v1/"
                        + "patient-profile/"
                        + "me/measurements"
                    ),
                    {
                        method:
                            "PATCH",

                        headers: {
                            Authorization:
                                `Bearer ${token}`,

                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    height_cm:
                                        heightValue,

                                    weight_kg:
                                        weightValue,
                                }
                            ),
                    }
                );


            const payload =
                await parseResponse(
                    response
                );


            if (!response.ok) {
                throw new Error(
                    getErrorMessage(
                        payload
                    )
                );
            }


            await loadProfile();


            profileStatus.textContent =
                (
                    payload.changed
                        ? (
                            "Profile saved successfully."
                        )
                        : (
                            "No Height or Weight "
                            + "changes were detected."
                        )
                );


            if (
                !historyPanel.hidden
            ) {
                await loadHistory();
            }

        } catch (error) {
            setEditing(
                true
            );

            historyButton.disabled =
                false;


            profileStatus.textContent =
                (
                    "Save failed: "
                    + error.message
                );
        }
    }


    function formatMeasurement(
        value
    ) {
        if (
            value === null
            || value === undefined
            || value === ""
        ) {
            return "?";
        }


        const numericValue =
            Number(
                value
            );


        if (
            !Number.isFinite(
                numericValue
            )
        ) {
            return String(
                value
            );
        }


        return numericValue
            .toFixed(
                2
            )
            .replace(
                /\.00$/,
                ""
            );
    }


    function normalizeServerDateTime(
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


        return (
            text
            + "Z"
        );
    }


    function formatHistoryDate(
        value
    ) {
        const normalized =
            normalizeServerDateTime(
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


    function renderHistory(
        records
    ) {
        historyResults
            .replaceChildren();


        if (
            !Array.isArray(
                records
            )
            || records.length === 0
        ) {
            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "profile-history-empty";

            empty.textContent =
                (
                    "No profile changes "
                    + "recorded yet."
                );


            historyResults.appendChild(
                empty
            );

            return;
        }


        for (
            const record
            of records
        ) {
            const card =
                document.createElement(
                    "article"
                );

            card.className =
                "profile-history-item";


            const date =
                document.createElement(
                    "div"
                );

            date.className =
                "profile-history-date";

            date.textContent =
                formatHistoryDate(
                    record.recorded_at
                );


            const heightRow =
                document.createElement(
                    "div"
                );

            const heightLabel =
                document.createElement(
                    "strong"
                );

            heightLabel.textContent =
                "Height (cm): ";


            heightRow.append(
                heightLabel,
                document.createTextNode(
                    formatMeasurement(
                        record.height_cm
                    )
                )
            );


            const weightRow =
                document.createElement(
                    "div"
                );

            const weightLabel =
                document.createElement(
                    "strong"
                );

            weightLabel.textContent =
                "Weight (kg): ";


            weightRow.append(
                weightLabel,
                document.createTextNode(
                    formatMeasurement(
                        record.weight_kg
                    )
                )
            );


            card.append(
                date,
                heightRow,
                weightRow
            );


            historyResults.appendChild(
                card
            );
        }
    }


    async function loadHistory() {
        const token =
            getAccessToken();


        if (!token) {
            return;
        }


        historyResults.textContent =
            "Loading Patient History...";


        try {
            const response =
                await fetch(
                    (
                        "/api/v1/"
                        + "patient-profile/"
                        + "me/history"
                    ),
                    {
                        method:
                            "GET",

                        headers: {
                            Authorization:
                                `Bearer ${token}`,
                        },
                    }
                );


            const payload =
                await parseResponse(
                    response
                );


            if (!response.ok) {
                throw new Error(
                    getErrorMessage(
                        payload
                    )
                );
            }


            renderHistory(
                payload
            );

        } catch (error) {
            historyResults.textContent =
                (
                    "Patient History failed: "
                    + error.message
                );
        }
    }


    editButton.addEventListener(
        "click",
        () => {
            if (!profileLoaded) {
                return;
            }


            setEditing(
                true
            );


            profileStatus.textContent =
                (
                    "Edit mode: "
                    + "Height and Weight only."
                );


            heightInput.focus();
            heightInput.select();
        }
    );


    saveButton.addEventListener(
        "click",
        saveProfile
    );


    historyButton.addEventListener(
        "click",
        async () => {
            if (!profileLoaded) {
                return;
            }


            if (
                !historyPanel.hidden
            ) {
                historyPanel.hidden =
                    true;

                return;
            }


            historyPanel.hidden =
                false;


            await loadHistory();
        }
    );


    window.addEventListener(
        "lungxray:auth-user",
        (event) => {
            const user =
                (
                    event.detail
                    && event.detail.user
                );


            if (
                !user
                || user.role !== "USER"
            ) {
                resetProfileUI();

                profileStatus.textContent =
                    (
                        "Patient Profile is available "
                        + "to USER accounts."
                    );

                return;
            }


            void loadProfile();
        }
    );


    window.addEventListener(
        "lungxray:auth-guest",
        () => {
            resetProfileUI();

            profileStatus.textContent =
                (
                    "Sign in to load "
                    + "your profile."
                );
        }
    );


    resetProfileUI();


    queueMicrotask(
        () => {
            if (
                getAccessToken()
            ) {
                void loadProfile();
            }
        }
    );
})();
