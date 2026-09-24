(() => {
    "use strict";
    const el = id => document.getElementById(id);
    const searchForm = el("admin-patient-search-form");
    const query = el("admin-patient-query");
    const limitInput = el("admin-patient-limit");
    const status = el("admin-search-status");
    const results = el("admin-search-results");
    const searchButton = el("admin-search-button");
    const previous = el("admin-patient-previous");
    const next = el("admin-patient-next");
    const pageLabel = el("admin-patient-page");
    const editor = el("admin-patient-editor");
    const editForm = el("admin-patient-edit-form");
    const editStatus = el("admin-patient-edit-status");

    const viewer = el("admin-patient-viewer");
    const viewIdentity = el("admin-patient-view-identity");
    const viewStatus = el("admin-patient-view-status");
    const viewProfile = el("admin-patient-view-profile");
    const viewMedical = el("admin-patient-view-medical");
    const viewAnalyses = el("admin-patient-view-analyses");
    const viewClose = el("admin-patient-view-close");
    const editMedicalFieldset = el(
        "admin-patient-edit-medical-fields"
    );

    const editMedicalMeta = el(
        "admin-edit-medical-meta"
    );

    const editMedicalEmpty = el(
        "admin-edit-medical-empty"
    );

    const medicalFields = {
        current_complaint_hpi:
            el("admin-edit-current-complaint"),

        past_medical_history:
            el("admin-edit-past-medical"),

        past_medication_history:
            el("admin-edit-past-medication"),

        allergy_history:
            el("admin-edit-allergy-history"),

        diseases:
            el("admin-edit-diseases"),

        medications:
            el("admin-edit-medications"),

        smoking_status:
            el("admin-edit-smoking"),

        alcohol_status:
            el("admin-edit-alcohol"),

        occupational_exposure:
            el("admin-edit-exposure"),

        diet:
            el("admin-edit-diet"),

        appetite:
            el("admin-edit-appetite"),

        sleep:
            el("admin-edit-sleep"),

        exercise:
            el("admin-edit-exercise"),

        bowel_bladder:
            el("admin-edit-bowel"),

        habits:
            el("admin-edit-habits"),

        family_history:
            el("admin-edit-family-history"),

        notes:
            el("admin-edit-medical-notes"),
    };

    const fields = {
        full_name: el("admin-edit-name"), phone: el("admin-edit-phone"),
        email: el("admin-edit-email"), address: el("admin-edit-address"),
        date_of_birth: el("admin-edit-birth"), sex: el("admin-edit-sex"),
        is_active: el("admin-edit-active"),
    };
    let page = 1, total = 0, loadedLimit = 20, activeQuery = "", selected = null;
    let generation = 0, request = null, mutating = false;
    let detailRequest = null;
    let editDetailRequest = null;
    let selectedLatestMedicalHistory = null;
    const token = () => normalizeToken(el("token-input").value);

    function node(parent, tag, text, className = "") {
        const child = document.createElement(tag);
        child.textContent = text == null || text === "" ? "—" : String(text);
        child.className = className;
        parent.appendChild(child);
        return child;
    }
    function controls() {
        searchButton.disabled = Boolean(request) || mutating;
        previous.disabled = Boolean(request) || mutating || page <= 1;
        next.disabled = Boolean(request) || mutating || page * loadedLimit >= total;
    }
    function reset() {
        generation++;
        if (request) request.abort();
        request = null;
        results.replaceChildren();
        page = 1; total = 0; selected = null; mutating = false;
        query.value = "";
        pageLabel.textContent = "";
        status.textContent = "Enter a name, phone number, or address to search.";
        if (editor.open) editor.close();

        if (detailRequest) {
            detailRequest.abort();
            detailRequest = null;
        }

        if (editDetailRequest) {
            editDetailRequest.abort();
            editDetailRequest = null;
        }

        selectedLatestMedicalHistory = null;

        if (viewer.open) viewer.close();

        controls();
    }
    async function api(url, options = {}) {
        const response = await fetch(url, { ...options, headers: {
            Authorization: `Bearer ${token()}`, ...options.headers,
        }, cache: "no-store" });
        if (response.status === 204) return null;
        const data = await parseResponse(response);
        if (!response.ok) {
            if (response.status === 404 && url.split("?")[0] === "/api/v1/admin/patients") {
                throw new Error("Patient Search API is unavailable. Restart the backend to load the update.");
            }
            throw new Error(getErrorMessage(data));
        }
        return data;
    }

    function formatDetailDate(value) {
        if (!value) return "?";

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString();
    }


    function formatDetailConfidence(value) {
        if (
            value === null
            || value === undefined
            || value === ""
        ) {
            return "?";
        }

        let number = Number(value);

        if (!Number.isFinite(number)) {
            return String(value);
        }

        if (number <= 1) {
            number *= 100;
        }

        return `${number.toFixed(2)}%`;
    }


    function renderPatientProfile(profile) {
        viewProfile.replaceChildren();

        const table = node(
            viewProfile,
            "table",
            "",
            "admin-patient-table admin-patient-detail-table"
        );

        table.textContent = "";

        const rows = [
            ["Patient code", profile.patient_code],
            ["Username", profile.username],
            ["Full name", profile.full_name],
            ["Phone", profile.phone],
            ["Email", profile.email],
            ["Address", profile.address],
            ["Date of birth", profile.date_of_birth],
            ["Birth year", profile.birth_year],
            ["Sex", profile.sex],
            [
                "Height",
                profile.height_cm == null
                    ? null
                    : `${profile.height_cm} cm`
            ],
            [
                "Weight",
                profile.weight_kg == null
                    ? null
                    : `${profile.weight_kg} kg`
            ],
            [
                "Account status",
                profile.is_active
                    ? "Active"
                    : "Inactive"
            ],
        ];

        const body = table.createTBody();

        for (const [label, value] of rows) {
            const row = body.insertRow();

            node(
                row,
                "th",
                label
            );

            node(
                row,
                "td",
                value
            );
        }
    }



    function formatMedicalList(value) {
        if (!Array.isArray(value) || !value.length) {
            return null;
        }

        return value.join(", ");
    }


    function renderMedicalHistory(items) {
        viewMedical.replaceChildren();

        if (!items.length) {
            node(
                viewMedical,
                "p",
                "No medical history found."
            );

            return;
        }

        items.forEach(
            (history, index) => {

                const card = node(
                    viewMedical,
                    "section",
                    "",
                    "admin-medical-history-card"
                );

                card.textContent = "";

                const title = node(
                    card,
                    "h5",
                    (
                        `Record ${index + 1} ? `
                        + formatDetailDate(
                            history.recorded_at
                        )
                    )
                );

                title.className = (
                    "admin-medical-history-title"
                );

                const table = node(
                    card,
                    "table",
                    "",
                    (
                        "admin-patient-table "
                        + "admin-patient-detail-table"
                    )
                );

                table.textContent = "";

                const rows = [
                    [
                        "Current complaint / HPI",
                        history.current_complaint_hpi
                    ],
                    [
                        "Past medical history",
                        history.past_medical_history
                    ],
                    [
                        "Past medication history",
                        history.past_medication_history
                    ],
                    [
                        "Allergy history",
                        history.allergy_history
                    ],
                    [
                        "Diseases",
                        formatMedicalList(
                            history.diseases
                        )
                    ],
                    [
                        "Medications",
                        formatMedicalList(
                            history.medications
                        )
                    ],
                    [
                        "Allergies",
                        formatMedicalList(
                            history.allergies
                        )
                    ],
                    [
                        "Smoking",
                        history.smoking_status
                    ],
                    [
                        "Alcohol",
                        history.alcohol_status
                    ],
                    [
                        "Occupational exposure",
                        history.occupational_exposure
                    ],
                    [
                        "Diet",
                        history.diet
                    ],
                    [
                        "Appetite",
                        history.appetite
                    ],
                    [
                        "Sleep",
                        history.sleep
                    ],
                    [
                        "Exercise",
                        history.exercise
                    ],
                    [
                        "Bowel / bladder",
                        history.bowel_bladder
                    ],
                    [
                        "Habits",
                        history.habits
                    ],
                    [
                        "Family history",
                        history.family_history
                    ],
                    [
                        "Notes",
                        history.notes
                    ],
                ];

                const body = table.createTBody();

                for (
                    const [label, value]
                    of rows
                ) {
                    const row = body.insertRow();

                    node(
                        row,
                        "th",
                        label
                    );

                    node(
                        row,
                        "td",
                        value
                    );
                }
            }
        );
    }



    async function fetchAdminAssetBlob(url) {
        const accessToken = token();

        if (!accessToken) {
            throw new Error(
                "Please sign in with an ADMIN account."
            );
        }

        const response = await fetch(
            url,
            {
                method: "GET",
                headers: {
                    Authorization:
                        `Bearer ${accessToken}`,
                },
                cache: "no-store",
            }
        );

        if (!response.ok) {
            const payload =
                await parseResponse(
                    response
                );

            throw new Error(
                getErrorMessage(
                    payload
                )
            );
        }

        return await response.blob();
    }


    async function fetchLatestAdminDrAIAdvice(
        analysisId
    ) {
        const payload = await api(
            "/api/v1/analyses/"
            + encodeURIComponent(
                analysisId
            )
            + "/medical-advices"
        );

        if (!Array.isArray(payload)) {
            throw new Error(
                "Unexpected Dr.AI response."
            );
        }

        return (
            payload.length
                ? payload[0]
                : null
        );
    }


    function createAnalysisAction(
        parent,
        label,
        handler,
        disabled = false
    ) {
        const button = node(
            parent,
            "button",
            label,
            "secondary"
        );

        button.type = "button";
        button.disabled = disabled;

        if (!disabled) {
            button.addEventListener(
                "click",
                handler
            );
        }

        return button;
    }


    async function previewAdminPdf(
        url,
        title
    ) {
        const previewWindow =
            window.open(
                "",
                "_blank"
            );

        if (!previewWindow) {
            throw new Error(
                "The browser blocked the PDF preview tab."
            );
        }

        previewWindow.document.title =
            title;

        previewWindow.document.body.textContent =
            "Loading PDF preview...";

        try {
            const blob =
                await fetchAdminAssetBlob(
                    url
                );

            if (
                !String(
                    blob.type || ""
                )
                .toLowerCase()
                .startsWith(
                    "application/pdf"
                )
            ) {
                throw new Error(
                    "The server did not return a PDF file."
                );
            }

            const objectUrl =
                URL.createObjectURL(
                    blob
                );

            previewWindow.location.href =
                objectUrl;

            window.setTimeout(
                () => {
                    URL.revokeObjectURL(
                        objectUrl
                    );
                },
                60000
            );

        } catch (error) {
            if (
                previewWindow
                && !previewWindow.closed
            ) {
                previewWindow.close();
            }

            throw error;
        }
    }


    async function downloadAdminPdf(
        url,
        filename
    ) {
        const blob =
            await fetchAdminAssetBlob(
                url
            );

        if (
            !String(
                blob.type || ""
            )
            .toLowerCase()
            .startsWith(
                "application/pdf"
            )
        ) {
            throw new Error(
                "The server did not return a PDF file."
            );
        }

        const objectUrl =
            URL.createObjectURL(
                blob
            );

        const link =
            document.createElement(
                "a"
            );

        link.href = objectUrl;
        link.download = filename;
        link.click();

        window.setTimeout(
            () => {
                URL.revokeObjectURL(
                    objectUrl
                );
            },
            1000
        );
    }


    function renderAdminAdvice(
        container,
        advice
    ) {
        container.replaceChildren();

        if (!advice) {
            node(
                container,
                "p",
                "No Dr.AI advice is available for this analysis."
            );

            return;
        }

        const meta = node(
            container,
            "p",
            "",
            "admin-analysis-advice-meta"
        );

        meta.textContent = [
            advice.language
                ? `Language: ${advice.language}`
                : null,
            advice.provider
                ? `Provider: ${advice.provider}`
                : null,
            advice.model_name
                ? `Model: ${advice.model_name}`
                : null,
        ]
        .filter(Boolean)
        .join(" | ");

        const text = node(
            container,
            "pre",
            advice.advice_text
                || "No advice text is available.",
            "admin-analysis-advice-text"
        );

        text.setAttribute?.(
            "tabindex",
            "0"
        );
    }


    async function showAdminAnalysisImage(
        userId,
        analysis,
        container,
        statusNode
    ) {
        container.replaceChildren();

        statusNode.textContent =
            "Loading X-ray image...";

        const blob =
            await fetchAdminAssetBlob(
                "/api/v1/admin/patients/"
                + encodeURIComponent(
                    userId
                )
                + "/analyses/"
                + encodeURIComponent(
                    analysis.analysis_id
                )
                + "/image"
            );

        if (
            !String(
                blob.type || ""
            )
            .toLowerCase()
            .startsWith(
                "image/"
            )
        ) {
            throw new Error(
                "The server did not return an image."
            );
        }

        const objectUrl =
            URL.createObjectURL(
                blob
            );

        const image = node(
            container,
            "img",
            "",
            "admin-analysis-xray-image"
        );

        image.alt = (
            "Chest X-ray for analysis "
            + analysis.analysis_code
        );

        image.src = objectUrl;

        image.addEventListener(
            "load",
            () => {
                URL.revokeObjectURL(
                    objectUrl
                );
            },
            {
                once: true,
            }
        );

        image.addEventListener(
            "error",
            () => {
                URL.revokeObjectURL(
                    objectUrl
                );
            },
            {
                once: true,
            }
        );

        statusNode.textContent =
            "X-ray image loaded.";
    }


    function renderAnalysisHistory(
        items,
        userId
    ) {
        viewAnalyses.replaceChildren();

        if (!items.length) {
            node(
                viewAnalyses,
                "p",
                "No analysis history found."
            );

            return;
        }

        for (const analysis of items) {

            const card = node(
                viewAnalyses,
                "section",
                "",
                "admin-analysis-history-card"
            );

            card.textContent = "";

            const heading = node(
                card,
                "h5",
                (
                    "Analysis "
                    + analysis.analysis_code
                ),
                "admin-analysis-history-title"
            );

            heading.textContent = (
                "Analysis "
                + analysis.analysis_code
            );

            const metaTable = node(
                card,
                "table",
                "",
                (
                    "admin-patient-table "
                    + "admin-patient-detail-table "
                    + "admin-analysis-meta-table"
                )
            );

            metaTable.textContent = "";

            const model = [
                (
                    analysis.model_name
                    || analysis.model_key
                ),
                (
                    analysis.model_version
                        ? `v${analysis.model_version}`
                        : null
                ),
            ]
            .filter(Boolean)
            .join(" ");

            const metaRows = [
                [
                    "Analysis code",
                    analysis.analysis_code
                ],
                [
                    "Date",
                    formatDetailDate(
                        analysis.created_at
                    )
                ],
                [
                    "Completed",
                    formatDetailDate(
                        analysis.completed_at
                    )
                ],
                [
                    "Original file",
                    analysis.original_filename
                ],
                [
                    "Input source",
                    analysis.input_source
                ],
                [
                    "Model",
                    model || null
                ],
                [
                    "Prediction",
                    analysis.predicted_class
                ],
                [
                    "Confidence",
                    formatDetailConfidence(
                        analysis.confidence
                    )
                ],
                [
                    "Status",
                    analysis.status
                ],
                [
                    "Technical PDF",
                    (
                        analysis.report_code
                            ? (
                                analysis.report_code
                                + (
                                    analysis.report_language
                                        ? ` (${analysis.report_language})`
                                        : ""
                                )
                            )
                            : "Not generated"
                    )
                ],
            ];

            const body =
                metaTable.createTBody();

            for (
                const [label, value]
                of metaRows
            ) {
                const row =
                    body.insertRow();

                node(
                    row,
                    "th",
                    label
                );

                node(
                    row,
                    "td",
                    value
                );
            }


            const actions = node(
                card,
                "div",
                "",
                "admin-analysis-action-row"
            );

            actions.textContent = "";


            const imagePanel = node(
                card,
                "div",
                "",
                "admin-analysis-image-panel"
            );

            imagePanel.textContent = "";


            const advicePanel = node(
                card,
                "div",
                "",
                "admin-analysis-advice-panel"
            );

            advicePanel.textContent = "";


            const actionStatus = node(
                card,
                "p",
                "Ready.",
                "admin-analysis-action-status"
            );


            const imageButton =
                createAnalysisAction(
                    actions,
                    (
                        analysis.has_image
                            ? "View X-ray Image"
                            : "X-ray Image Unavailable"
                    ),
                    async () => {
                        if (
                            imageButton.disabled
                        ) {
                            return;
                        }

                        imageButton.disabled =
                            true;

                        try {
                            await showAdminAnalysisImage(
                                userId,
                                analysis,
                                imagePanel,
                                actionStatus
                            );

                        } catch (error) {
                            actionStatus.textContent =
                                (
                                    "Image failed: "
                                    + error.message
                                );

                        } finally {
                            imageButton.disabled =
                                false;
                        }
                    },
                    !analysis.has_image
                );


            const adviceButton =
                createAnalysisAction(
                    actions,
                    "View Dr.AI Advice",
                    async () => {
                        if (
                            adviceButton.disabled
                        ) {
                            return;
                        }

                        adviceButton.disabled =
                            true;

                        actionStatus.textContent =
                            "Loading Dr.AI advice...";

                        try {
                            const advice =
                                await fetchLatestAdminDrAIAdvice(
                                    analysis.analysis_id
                                );

                            renderAdminAdvice(
                                advicePanel,
                                advice
                            );

                            actionStatus.textContent =
                                (
                                    advice
                                        ? "Dr.AI advice loaded."
                                        : "No Dr.AI advice is available."
                                );

                        } catch (error) {
                            actionStatus.textContent =
                                (
                                    "Dr.AI advice failed: "
                                    + error.message
                                );

                        } finally {
                            adviceButton.disabled =
                                false;
                        }
                    }
                );


            const reportPreview =
                createAnalysisAction(
                    actions,
                    "Preview Report PDF",
                    async () => {
                        if (
                            reportPreview.disabled
                        ) {
                            return;
                        }

                        reportPreview.disabled =
                            true;

                        actionStatus.textContent =
                            "Opening report PDF...";

                        try {
                            await previewAdminPdf(
                                "/api/v1/reports/"
                                + encodeURIComponent(
                                    analysis.report_id
                                )
                                + "/preview",
                                (
                                    analysis.report_code
                                    || "Technical Report"
                                )
                            );

                            actionStatus.textContent =
                                "Report PDF preview opened.";

                        } catch (error) {
                            actionStatus.textContent =
                                (
                                    "Report PDF preview failed: "
                                    + error.message
                                );

                        } finally {
                            reportPreview.disabled =
                                false;
                        }
                    },
                    analysis.report_id == null
                );


            const reportDownload =
                createAnalysisAction(
                    actions,
                    "Download Report PDF",
                    async () => {
                        if (
                            reportDownload.disabled
                        ) {
                            return;
                        }

                        reportDownload.disabled =
                            true;

                        actionStatus.textContent =
                            "Downloading report PDF...";

                        try {
                            await downloadAdminPdf(
                                "/api/v1/reports/"
                                + encodeURIComponent(
                                    analysis.report_id
                                )
                                + "/download",
                                (
                                    (
                                        analysis.report_code
                                        || (
                                            "report-"
                                            + analysis.analysis_id
                                        )
                                    )
                                    + ".pdf"
                                )
                            );

                            actionStatus.textContent =
                                "Report PDF downloaded.";

                        } catch (error) {
                            actionStatus.textContent =
                                (
                                    "Report PDF download failed: "
                                    + error.message
                                );

                        } finally {
                            reportDownload.disabled =
                                false;
                        }
                    },
                    analysis.report_id == null
                );


            const drAIPreview =
                createAnalysisAction(
                    actions,
                    "Preview Dr.AI PDF",
                    async () => {
                        if (
                            drAIPreview.disabled
                        ) {
                            return;
                        }

                        drAIPreview.disabled =
                            true;

                        actionStatus.textContent =
                            "Loading Dr.AI PDF...";

                        try {
                            const advice =
                                await fetchLatestAdminDrAIAdvice(
                                    analysis.analysis_id
                                );

                            if (!advice) {
                                throw new Error(
                                    "No Dr.AI advice is available."
                                );
                            }

                            await previewAdminPdf(
                                "/api/v1/medical-advices/"
                                + encodeURIComponent(
                                    advice.id
                                )
                                + "/download",
                                "Dr.AI PDF"
                            );

                            actionStatus.textContent =
                                "Dr.AI PDF preview opened.";

                        } catch (error) {
                            actionStatus.textContent =
                                (
                                    "Dr.AI PDF preview failed: "
                                    + error.message
                                );

                        } finally {
                            drAIPreview.disabled =
                                false;
                        }
                    }
                );


            const drAIDownload =
                createAnalysisAction(
                    actions,
                    "Download Dr.AI PDF",
                    async () => {
                        if (
                            drAIDownload.disabled
                        ) {
                            return;
                        }

                        drAIDownload.disabled =
                            true;

                        actionStatus.textContent =
                            "Downloading Dr.AI PDF...";

                        try {
                            const advice =
                                await fetchLatestAdminDrAIAdvice(
                                    analysis.analysis_id
                                );

                            if (!advice) {
                                throw new Error(
                                    "No Dr.AI advice is available."
                                );
                            }

                            await downloadAdminPdf(
                                "/api/v1/medical-advices/"
                                + encodeURIComponent(
                                    advice.id
                                )
                                + "/download",
                                (
                                    "DrAI-analysis-"
                                    + analysis.analysis_id
                                    + "-advice-"
                                    + advice.id
                                    + "-"
                                    + (
                                        advice.language
                                        || "unknown"
                                    )
                                    + ".pdf"
                                )
                            );

                            actionStatus.textContent =
                                "Dr.AI PDF downloaded.";

                        } catch (error) {
                            actionStatus.textContent =
                                (
                                    "Dr.AI PDF download failed: "
                                    + error.message
                                );

                        } finally {
                            drAIDownload.disabled =
                                false;
                        }
                    }
                );
        }
    }


    async function openDetails(patient) {
        if (mutating) return;

        if (detailRequest) {
            detailRequest.abort();
        }

        const current = (
            new AbortController()
        );

        detailRequest = current;

        const epoch = generation;

        viewIdentity.textContent = (
            `${patient.patient_code} ? `
            + patient.full_name
        );

        viewStatus.textContent = (
            "Loading patient details..."
        );

        viewProfile.replaceChildren();
        viewMedical.replaceChildren();
        viewAnalyses.replaceChildren();

        viewer.showModal();

        try {
            const data = await api(
                `/api/v1/admin/patients/`
                + `${patient.user_id}/details`,
                {
                    signal: current.signal,
                }
            );

            if (
                epoch !== generation
                || detailRequest !== current
            ) {
                return;
            }

            if (
                !data
                || !data.patient_profile
                || !Array.isArray(
                    data.medical_history
                )
                || !Array.isArray(
                    data.analysis_history
                )
            ) {
                throw new Error(
                    "Invalid patient detail response."
                );
            }

            renderPatientProfile(
                data.patient_profile
            );

            renderMedicalHistory(
                data.medical_history
            );

            renderAnalysisHistory(
                data.analysis_history,
                data.patient_profile.user_id
            );

            const medicalCount = (
                data.medical_history.length
            );

            const analysisCount = (
                data.analysis_history.length
            );

            viewStatus.textContent = (
                `${medicalCount} medical history record(s) ? `
                + `${analysisCount} analysis record(s).`
            );

        } catch (error) {
            if (
                epoch === generation
                && detailRequest === current
                && error.name !== "AbortError"
            ) {
                viewProfile.replaceChildren();
                viewMedical.replaceChildren();
                viewAnalyses.replaceChildren();

                viewStatus.textContent = (
                    `Patient details failed: `
                    + error.message
                );
            }

        } finally {
            if (detailRequest === current) {
                detailRequest = null;
            }
        }
    }


    function render(items) {
        results.replaceChildren();
        if (!items.length) { node(results, "p", "No patient accounts found."); return; }
        const table = node(results, "table", "", "admin-patient-table");
        table.textContent = "";
        const header = table.createTHead().insertRow();
        for (const label of ["Patient", "Full name", "Phone", "Email", "Address", "Status", "Actions"]) {
            const th = node(header, "th", label); th.scope = "col";
        }
        const body = table.createTBody();
        for (const patient of items) {
            const row = body.insertRow();
            for (const value of [patient.patient_code, patient.full_name, patient.phone,
                patient.email, patient.address, patient.is_active ? "Active" : "Inactive"]) {
                node(row, "td", value);
            }
            const actions = node(row, "td", "", "admin-patient-actions");
            actions.textContent = "";

            const view = node(
                actions,
                "button",
                "View",
                "secondary"
            );

            view.type = "button";

            view.addEventListener(
                "click",
                () => {
                    if (!mutating) {
                        void openDetails(
                            patient
                        );
                    }
                }
            );

            const edit = node(actions, "button", "Edit", "secondary");
            edit.type = "button";
            edit.addEventListener("click", () => { if (!mutating) openEditor(patient); });
            const remove = node(actions, "button", "Delete", "danger");
            remove.type = "button";
            remove.addEventListener("click", () => deletePatient(patient, remove));
        }
    }
    async function load(targetPage = 1, newQuery = false) {
        if (mutating) return;
        if (getAdminDashboardTokenRole() !== "ADMIN") {
            status.textContent = "Sign in with an ADMIN account to search patients.";
            return;
        }
        const limit = newQuery ? Number(limitInput.value) : loadedLimit;
        if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
            status.textContent = "Limit must be an integer from 1 to 100."; return;
        }
        if (request) request.abort();
        const current = new AbortController();
        request = current;
        const epoch = generation;
        const requestedQuery = newQuery ? query.value.trim() : activeQuery;
        controls();
        status.textContent = "Searching patient accounts...";
        try {
            const params = new URLSearchParams({q: requestedQuery, page: targetPage, limit});
            const data = await api(`/api/v1/admin/patients?${params}`, {signal: current.signal});
            if (epoch !== generation || request !== current) return;
            if (!data || !Array.isArray(data.items)) throw new Error("Invalid patient search response.");
            page = data.page; total = data.total; loadedLimit = limit; activeQuery = requestedQuery;
            render(data.items);
            pageLabel.textContent = `Page ${page} of ${Math.max(1, Math.ceil(total / limit))}`;
            status.textContent = `${total} patient account(s) found.`;
        } catch (error) {
            if (epoch === generation && request === current && error.name !== "AbortError") {
                results.replaceChildren(); total = 0; page = 1; pageLabel.textContent = "";
                status.textContent = `Patient search failed: ${error.message}`;
            }
        } finally {
            if (request === current) { request = null; controls(); }
        }
    }
    function parseMedicalListInput(value) {
        const items = String(
            value || ""
        )
        .split(",")
        .map(
            item => item.trim()
        )
        .filter(Boolean);

        return (
            items.length
                ? items
                : null
        );
    }


    function medicalListToInput(value) {
        if (
            !Array.isArray(value)
            || !value.length
        ) {
            return "";
        }

        return value.join(", ");
    }


    function clearMedicalEditor() {
        selectedLatestMedicalHistory = null;

        el(
            "admin-edit-medical-id"
        ).value = "";

        for (
            const input
            of Object.values(
                medicalFields
            )
        ) {
            input.value = "";
        }

        editMedicalFieldset.disabled = true;

        editMedicalMeta.textContent =
            "Loading latest medical history...";

        editMedicalEmpty.hidden = true;
    }


    function populateMedicalEditor(
        history
    ) {
        selectedLatestMedicalHistory =
            history;

        el(
            "admin-edit-medical-id"
        ).value = String(
            history.id
        );

        medicalFields.current_complaint_hpi.value =
            history.current_complaint_hpi
            ?? "";

        medicalFields.past_medical_history.value =
            history.past_medical_history
            ?? "";

        medicalFields.past_medication_history.value =
            history.past_medication_history
            ?? "";

        medicalFields.allergy_history.value =
            history.allergy_history
            ?? "";

        medicalFields.diseases.value =
            medicalListToInput(
                history.diseases
            );

        medicalFields.medications.value =
            medicalListToInput(
                history.medications
            );

        medicalFields.smoking_status.value =
            history.smoking_status
            ?? "";

        medicalFields.alcohol_status.value =
            history.alcohol_status
            ?? "";

        medicalFields.occupational_exposure.value =
            history.occupational_exposure
            ?? "";

        medicalFields.diet.value =
            history.diet
            ?? "";

        medicalFields.appetite.value =
            history.appetite
            ?? "";

        medicalFields.sleep.value =
            history.sleep
            ?? "";

        medicalFields.exercise.value =
            history.exercise
            ?? "";

        medicalFields.bowel_bladder.value =
            history.bowel_bladder
            ?? "";

        medicalFields.habits.value =
            history.habits
            ?? "";

        medicalFields.family_history.value =
            history.family_history
            ?? "";

        medicalFields.notes.value =
            history.notes
            ?? "";

        editMedicalMeta.textContent =
            (
                "Editing latest record #"
                + history.id
                + " | "
                + formatDetailDate(
                    history.recorded_at
                )
            );

        editMedicalEmpty.hidden = true;

        editMedicalFieldset.disabled =
            false;
    }


    function buildLatestMedicalPayload() {
        if (
            !selectedLatestMedicalHistory
        ) {
            return null;
        }

        return {
            id:
                selectedLatestMedicalHistory.id,

            current_complaint_hpi:
                medicalFields
                .current_complaint_hpi
                .value.trim()
                || null,

            past_medical_history:
                medicalFields
                .past_medical_history
                .value.trim()
                || null,

            past_medication_history:
                medicalFields
                .past_medication_history
                .value.trim()
                || null,

            allergy_history:
                medicalFields
                .allergy_history
                .value.trim()
                || null,

            diseases:
                parseMedicalListInput(
                    medicalFields
                    .diseases
                    .value
                ),

            medications:
                parseMedicalListInput(
                    medicalFields
                    .medications
                    .value
                ),

            smoking_status:
                medicalFields
                .smoking_status
                .value.trim()
                || null,

            alcohol_status:
                medicalFields
                .alcohol_status
                .value.trim()
                || null,

            occupational_exposure:
                medicalFields
                .occupational_exposure
                .value.trim()
                || null,

            diet:
                medicalFields
                .diet
                .value.trim()
                || null,

            appetite:
                medicalFields
                .appetite
                .value.trim()
                || null,

            sleep:
                medicalFields
                .sleep
                .value.trim()
                || null,

            exercise:
                medicalFields
                .exercise
                .value.trim()
                || null,

            bowel_bladder:
                medicalFields
                .bowel_bladder
                .value.trim()
                || null,

            habits:
                medicalFields
                .habits
                .value.trim()
                || null,

            family_history:
                medicalFields
                .family_history
                .value.trim()
                || null,

            notes:
                medicalFields
                .notes
                .value.trim()
                || null,
        };
    }


    async function openEditor(patient) {
        selected = patient;

        el(
            "admin-patient-edit-identity"
        ).textContent =
            (
                patient.patient_code
                + " | "
                + patient.username
            );

        for (
            const [key, input]
            of Object.entries(fields)
        ) {
            if (
                key === "is_active"
            ) {
                input.checked =
                    patient[key];
            }
            else {
                input.value =
                    patient[key]
                    ?? "";
            }
        }

        clearMedicalEditor();

        editStatus.textContent = "";

        el(
            "admin-patient-edit-fields"
        ).disabled = false;

        el(
            "admin-patient-save"
        ).disabled = false;

        editor.showModal();

        if (editDetailRequest) {
            editDetailRequest.abort();
        }

        const current =
            new AbortController();

        editDetailRequest = current;

        try {
            const data = await api(
                (
                    "/api/v1/admin/patients/"
                    + encodeURIComponent(
                        patient.user_id
                    )
                    + "/details"
                ),
                {
                    signal:
                        current.signal,
                }
            );

            if (
                editDetailRequest
                !== current
            ) {
                return;
            }

            const histories =
                Array.isArray(
                    data.medical_history
                )
                    ? data.medical_history
                    : [];

            if (!histories.length) {
                selectedLatestMedicalHistory =
                    null;

                editMedicalFieldset.disabled =
                    true;

                editMedicalMeta.textContent =
                    "No medical history available.";

                editMedicalEmpty.hidden =
                    false;

                return;
            }

            populateMedicalEditor(
                histories[0]
            );

        } catch (error) {
            if (
                error.name
                === "AbortError"
            ) {
                return;
            }

            editMedicalFieldset.disabled =
                true;

            editMedicalMeta.textContent =
                (
                    "Medical history load failed: "
                    + error.message
                );

        } finally {
            if (
                editDetailRequest
                === current
            ) {
                editDetailRequest = null;
            }
        }
    }


    editForm.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            if (
                mutating
                || !selected
                || !editForm.reportValidity()
            ) {
                return;
            }

            const epoch =
                generation;

            const payload =
                Object.fromEntries(
                    Object.entries(fields).map(
                        ([key, input]) => [
                            key,
                            (
                                key === "is_active"
                                    ? input.checked
                                    : (
                                        input.value.trim()
                                        || null
                                    )
                            ),
                        ]
                    )
                );

            const latestMedicalHistory =
                buildLatestMedicalPayload();

            if (latestMedicalHistory) {
                payload.latest_medical_history =
                    latestMedicalHistory;
            }

            mutating = true;
            controls();

            el(
                "admin-patient-edit-fields"
            ).disabled = true;

            editMedicalFieldset.disabled =
                true;

            el(
                "admin-patient-save"
            ).disabled = true;

            editStatus.textContent =
                "Saving...";

            let saved = false;

            try {
                await api(
                    (
                        "/api/v1/admin/patients/"
                        + selected.user_id
                    ),
                    {
                        method: "PUT",
                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                        body:
                            JSON.stringify(
                                payload
                            ),
                    }
                );

                if (
                    epoch
                    !== generation
                ) {
                    return;
                }

                saved = true;
                editor.close();

            } catch (error) {
                if (
                    epoch
                    === generation
                ) {
                    editStatus.textContent =
                        error.message;
                }

            } finally {
                if (
                    epoch
                    === generation
                ) {
                    mutating = false;
                    controls();

                    el(
                        "admin-patient-edit-fields"
                    ).disabled = false;

                    editMedicalFieldset.disabled =
                        !selectedLatestMedicalHistory;

                    el(
                        "admin-patient-save"
                    ).disabled = false;
                }
            }

            if (
                saved
                && epoch
                === generation
            ) {
                await load(1);

                void initializeAdminDashboard();
            }
        }
    );


    async function deletePatient(patient, button) {
        if (mutating || request) return;
        if (!window.confirm(`Delete ${patient.full_name} (${patient.patient_code})? This permanently deletes the USER account and linked patient profile, medical histories, and analysis records. This cannot be undone.`)) return;
        const epoch = generation;
        mutating = true; button.disabled = true; controls();
        let deleted = false;
        try {
            await api(`/api/v1/admin/patients/${patient.user_id}`, {method: "DELETE"});
            deleted = epoch === generation;
        } catch (error) {
            if (epoch === generation) status.textContent = `Delete failed: ${error.message}`;
        } finally {
            if (epoch === generation) { mutating = false; button.disabled = false; controls(); }
        }
        if (deleted) {
            const lastPage = Math.max(1, Math.ceil((total - 1) / loadedLimit));
            await load(Math.min(page, lastPage));
            void initializeAdminDashboard();
        }
    }
    searchForm.addEventListener("submit", event => { event.preventDefault(); void load(1, true); });
    previous.addEventListener("click", () => { if (!previous.disabled) void load(page - 1); });
    next.addEventListener("click", () => { if (!next.disabled) void load(page + 1); });
    el("admin-patient-cancel").addEventListener(
        "click",
        () => {
            if (mutating) {
                return;
            }

            if (editDetailRequest) {
                editDetailRequest.abort();
                editDetailRequest = null;
            }

            editor.close();
        }
    );
    editor.addEventListener("cancel", event => { if (mutating) event.preventDefault(); });

    viewClose.addEventListener(
        "click",
        () => {
            if (detailRequest) {
                detailRequest.abort();
                detailRequest = null;
            }

            viewer.close();
        }
    );

    viewer.addEventListener(
        "cancel",
        () => {
            if (detailRequest) {
                detailRequest.abort();
                detailRequest = null;
            }
        }
    );
    window.addEventListener("lungxray:auth-user", reset);
    window.addEventListener("lungxray:auth-guest", reset);
})();
