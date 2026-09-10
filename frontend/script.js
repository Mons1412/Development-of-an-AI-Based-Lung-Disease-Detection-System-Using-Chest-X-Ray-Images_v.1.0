"use strict";


const MAX_BATCH_FILES = 50;

const MAX_BATCH_TOTAL_BYTES =
    200 * 1024 * 1024;


const tokenInput =
    document.getElementById(
        "token-input"
    );

const modelIdInput =
    document.getElementById(
        "model-id"
    );

const filesInput =
    document.getElementById(
        "batch-files"
    );
const folderInput =
    document.getElementById(
        "batch-folder"
    );
const fileSummary =
    document.getElementById(
        "file-summary"
    );

const fileList =
    document.getElementById(
        "file-list"
    );

const validationMessage =
    document.getElementById(
        "validation-message"
    );

const analyzeButton =
    document.getElementById(
        "analyze-button"
    );

const clearButton =
    document.getElementById(
        "clear-button"
    );

const requestStatus =
    document.getElementById(
        "request-status"
    );

const resultSection =
    document.getElementById(
        "result-section"
    );

const batchSummary =
    document.getElementById(
        "batch-summary"
    );

const results =
    document.getElementById(
        "results"
    );
const filterButtons =
    Array.from(
        document.querySelectorAll(
            ".filter-button"
        )
    );

const historyPatientCodeInput =
    document.getElementById(
        "history-patient-code"
    );

const historyLimitInput =
    document.getElementById(
        "history-limit"
    );

const historyOffsetInput =
    document.getElementById(
        "history-offset"
    );

const loadHistoryButton =
    document.getElementById(
        "load-history-button"
    );

const historyPreviousButton =
    document.getElementById(
        "history-previous-button"
    );

const historyNextButton =
    document.getElementById(
        "history-next-button"
    );

const historyStatus =
    document.getElementById(
        "history-status"
    );

const historySummary =
    document.getElementById(
        "history-summary"
    );

const historyResults =
    document.getElementById(
        "history-results"
    );
const profileStatus =
    document.getElementById(
        "profile-status"
    );

const profilePatientCodeInput =
    document.getElementById(
        "profile-patient-code"
    );

const profileFullNameInput =
    document.getElementById(
        "profile-full-name"
    );

const profileBirthYearInput =
    document.getElementById(
        "profile-birth-year"
    );

const profileGenderInput =
    document.getElementById(
        "profile-gender"
    );

const profilePhoneInput =
    document.getElementById(
        "profile-phone"
    );

const profileAddressInput =
    document.getElementById(
        "profile-address"
    );

const loadProfileButton =
    document.getElementById(
        "load-profile-button"
    );

const saveProfileButton =
    document.getElementById(
        "save-profile-button"
    );
const medicalHistoryStatus =
    document.getElementById(
        "medical-history-status"
    );

const loadMedicalHistoriesButton =
    document.getElementById(
        "load-medical-histories-button"
    );

const newMedicalHistoryButton =
    document.getElementById(
        "new-medical-history-button"
    );

const medicalHistorySummary =
    document.getElementById(
        "medical-history-summary"
    );

const medicalHistoryResults =
    document.getElementById(
        "medical-history-results"
    );

const medicalHistoryEditorTitle =
    document.getElementById(
        "medical-history-editor-title"
    );

const medicalHistoryIdInput =
    document.getElementById(
        "medical-history-id"
    );

const medicalHistoryDiseasesInput =
    document.getElementById(
        "medical-history-diseases"
    );

const medicalHistoryMedicationsInput =
    document.getElementById(
        "medical-history-medications"
    );

const medicalHistoryAllergiesInput =
    document.getElementById(
        "medical-history-allergies"
    );

const medicalHistorySmokingStatusInput =
    document.getElementById(
        "medical-history-smoking-status"
    );

const medicalHistoryAlcoholStatusInput =
    document.getElementById(
        "medical-history-alcohol-status"
    );

const medicalHistoryOccupationalExposureInput =
    document.getElementById(
        "medical-history-occupational-exposure"
    );

const medicalHistoryNotesInput =
    document.getElementById(
        "medical-history-notes"
    );

const saveMedicalHistoryButton =
    document.getElementById(
        "save-medical-history-button"
    );

const clearMedicalHistoryButton =
    document.getElementById(
        "clear-medical-history-button"
    );

const adminPatientCodeInput =
    document.getElementById(
        "admin-patient-code"
    );

const adminHistoryLimitInput =
    document.getElementById(
        "admin-history-limit"
    );

const adminHistoryOffsetInput =
    document.getElementById(
        "admin-history-offset"
    );

const adminSearchButton =
    document.getElementById(
        "admin-search-button"
    );

const adminHistoryPreviousButton =
    document.getElementById(
        "admin-history-previous-button"
    );

const adminHistoryNextButton =
    document.getElementById(
        "admin-history-next-button"
    );

const adminSearchStatus =
    document.getElementById(
        "admin-search-status"
    );

const adminSearchSummary =
    document.getElementById(
        "admin-search-summary"
    );

const adminSearchResults =
    document.getElementById(
        "admin-search-results"
    );

let activeResultFilter = "ALL";

let selectedFiles = [];

let selectionSource = "";

let ignoredFileCount = 0;

let patientProfileExists = false;

let selectedMedicalHistoryId = null;

function applyResultFilter(
    filter
) {
    activeResultFilter =
        filter;


    for (
        const button
        of filterButtons
    ) {
        button.classList.toggle(
            "active",
            (
                button.dataset.filter
                === filter
            )
        );
    }


    const cards =
        results.querySelectorAll(
            ".result-item"
        );


    for (
        const card
        of cards
    ) {
        const visible =
            (
                filter === "ALL"
                ||
                card.dataset.status
                === filter
            );

        card.hidden =
            !visible;
    }
}

function formatBytes(bytes) {
    if (bytes === 0) {
        return "0 B";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB",
    ];

    const index = Math.floor(
        Math.log(bytes)
        / Math.log(1024)
    );

    const value =
        bytes
        / Math.pow(
            1024,
            index
        );

    return (
        `${value.toFixed(2)} `
        + units[index]
    );
}


function getTotalBytes(files) {
    return files.reduce(
        (total, file) => {
            return total + file.size;
        },
        0
    );
}


function normalizeToken(rawToken) {
    const token = rawToken.trim();

    if (
        token
        .toLowerCase()
        .startsWith("bearer ")
    ) {
        return token.slice(7).trim();
    }

    return token;
}

function isImageFile(file) {
    if (
        file.type
        && file.type.startsWith("image/")
    ) {
        return true;
    }

    const name =
        file.name.toLowerCase();

    const extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".tif",
        ".tiff",
    ];

    return extensions.some(
        (extension) => {
            return name.endsWith(
                extension
            );
        }
    );
}
function applySelection(
    files,
    source
) {
    const allFiles =
        Array.from(files);

    const imageFiles =
        allFiles.filter(
            isImageFile
        );

    ignoredFileCount =
        allFiles.length
        - imageFiles.length;

    selectedFiles =
        imageFiles;

    selectionSource =
        source;

    renderSelectedFiles();
}
function validateFiles(files) {
    if (files.length === 0) {
        return {
            valid: false,
            message: (
                "Select at least one image."
            ),
        };
    }

    if (
        files.length
        > MAX_BATCH_FILES
    ) {
        return {
            valid: false,
            message: (
                "Too many files. "
                + `Maximum is `
                + `${MAX_BATCH_FILES}.`
            ),
        };
    }

    const totalBytes =
        getTotalBytes(files);

    if (
        totalBytes
        > MAX_BATCH_TOTAL_BYTES
    ) {
        return {
            valid: false,
            message: (
                "Batch is too large. "
                + "Maximum total size "
                + "is 200 MB."
            ),
        };
    }

    return {
        valid: true,
        message: "",
    };
}


function showValidation(message) {
    if (!message) {
        validationMessage.hidden = true;
        validationMessage.textContent = "";
        return;
    }

    validationMessage.hidden = false;
    validationMessage.textContent =
        message;
}


function renderSelectedFiles() {
    fileList.replaceChildren();

    const totalBytes =
        getTotalBytes(
            selectedFiles
        );

    if (
        selectedFiles.length === 0
    ) {
        fileSummary.textContent =
            "No images selected.";

        analyzeButton.disabled = true;

        showValidation("");

        return;
    }

    let summary =
        `${selectedFiles.length} image(s) — `
        + `${formatBytes(totalBytes)} total`;

    if (selectionSource) {
        summary +=
            ` — ${selectionSource}`;
    }

    if (ignoredFileCount > 0) {
        summary +=
            ` — ${ignoredFileCount} non-image file(s) ignored`;
    }

    fileSummary.textContent =
        summary;

    for (
        const file
        of selectedFiles
    ) {
        const item =
            document.createElement("li");

        const displayName =
            file.webkitRelativePath
            || file.name;

        item.textContent =
            `${displayName} — `
            + formatBytes(file.size);

        fileList.appendChild(item);
    }

    const validation =
        validateFiles(
            selectedFiles
        );

    showValidation(
        validation.message
    );

    analyzeButton.disabled =
        !validation.valid;
}


function setLoading(loading) {
    filesInput.disabled = loading;
    folderInput.disabled = loading;
    modelIdInput.disabled = loading;
    tokenInput.disabled = loading;
    clearButton.disabled = loading;

    if (loading) {
        analyzeButton.disabled = true;
        analyzeButton.textContent =
            "Analyzing...";

        requestStatus.textContent =
            "Uploading images and running AI analysis...";
    } else {
        const validation =
            validateFiles(
                selectedFiles
            );

        analyzeButton.disabled =
            !validation.valid;

        analyzeButton.textContent =
            "Analyze Batch";
    }
}


function createSummaryCard(
    label,
    value
) {
    const card =
        document.createElement("div");

    card.className =
        "summary-card";

    const labelElement =
        document.createElement("span");

    labelElement.textContent =
        label;

    const valueElement =
        document.createElement("strong");

    valueElement.textContent =
        String(value);

    card.append(
        labelElement,
        valueElement
    );

    return card;
}


function formatConfidence(value) {
    if (
        value === null
        || value === undefined
    ) {
        return "N/A";
    }

    const number =
        Number(value);

    if (
        Number.isNaN(number)
    ) {
        return String(value);
    }

    if (number <= 1) {
        return (
            `${(number * 100)
                .toFixed(2)}%`
        );
    }

    return `${number.toFixed(2)}%`;
}


function addDetail(
    list,
    label,
    value
) {
    const item =
        document.createElement("li");

    item.textContent =
        `${label}: ${value}`;

    list.appendChild(item);
}

function probabilityToPercent(value) {
    const number = Number(value);

    if (Number.isNaN(number)) {
        return 0;
    }

    const percent =
        number <= 1
            ? number * 100
            : number;

    return Math.min(
        100,
        Math.max(
            0,
            percent
        )
    );
}

function createImagePreview(file) {
    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "image-preview-wrapper";


    if (!file) {
        const fallback =
            document.createElement(
                "div"
            );

        fallback.className =
            "no-preview";

        fallback.textContent =
            "Preview unavailable";

        wrapper.appendChild(
            fallback
        );

        return wrapper;
    }


    const image =
        document.createElement(
            "img"
        );

    image.className =
        "image-preview";

    image.alt =
        `Preview of ${file.name}`;


    const objectUrl =
        URL.createObjectURL(file);

    image.src =
        objectUrl;


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


    wrapper.appendChild(
        image
    );

    return wrapper;
}

function createProbabilityRow(
    className,
    probability
) {
    const row =
        document.createElement(
            "div"
        );

    row.className =
        "probability-row";


    const header =
        document.createElement(
            "div"
        );

    header.className =
        "probability-header";


    const classElement =
        document.createElement(
            "span"
        );

    classElement.className =
        "probability-class";

    classElement.textContent =
        className;


    const valueElement =
        document.createElement(
            "span"
        );

    valueElement.className =
        "probability-value";

    valueElement.textContent =
        formatConfidence(
            probability
        );


    header.append(
        classElement,
        valueElement
    );


    const track =
        document.createElement(
            "div"
        );

    track.className =
        "probability-track";


    const fill =
        document.createElement(
            "div"
        );

    fill.className =
        "probability-fill";

    fill.style.width =
        `${
            probabilityToPercent(
                probability
            )
        }%`;


    track.appendChild(
        fill
    );


    row.append(
        header,
        track
    );

    return row;
}

function renderResultItem(
    item,
    sourceFile
) {
    const card =
        document.createElement(
            "article"
        );

    card.classList.add(
        "result-item"
    );

    card.classList.add(
        item.status
            .toLowerCase()
    );

    card.dataset.status =
        item.status;


    const header =
        document.createElement(
            "div"
        );

    header.className =
        "result-header";


    const filename =
        document.createElement(
            "div"
        );

    filename.className =
        "result-filename";

    filename.textContent =
        item.filename;


    const status =
        document.createElement(
            "div"
        );

    status.className =
        "status-badge";

    status.textContent =
        item.status;


    header.append(
        filename,
        status
    );

    card.appendChild(
        header
    );


    const content =
        document.createElement(
            "div"
        );

    content.className =
        "result-content";


    const preview =
        createImagePreview(
            sourceFile
        );


    const information =
        document.createElement(
            "div"
        );

    information.className =
        "result-information";


    if (
        item.status === "COMPLETED"
        && item.analysis
    ) {
        const analysis =
            item.analysis;


        const prediction =
            document.createElement(
                "p"
            );

        prediction.className =
            "prediction-title";


        const predictionLabel =
            document.createElement(
                "span"
            );

        predictionLabel.textContent =
            "Prediction: ";


        const predictionValue =
            document.createElement(
                "span"
            );

        predictionValue.className =
            "prediction-value";

        predictionValue.textContent =
            analysis.predicted_class
            || "N/A";


        prediction.append(
            predictionLabel,
            predictionValue
        );

        information.appendChild(
            prediction
        );


        const details =
            document.createElement(
                "ul"
            );

        details.className =
            "result-details";


        addDetail(
            details,
            "Analysis code",
            analysis.analysis_code
        );

        addDetail(
            details,
            "Patient code",
            analysis.patient_code
        );

        addDetail(
            details,
            "Model",
            (
                `${analysis.model_key} `
                + `${analysis.model_version}`
            )
        );

        addDetail(
            details,
            "Confidence",
            formatConfidence(
                analysis.confidence
            )
        );


        information.appendChild(
            details
        );


        if (
            analysis.probabilities
        ) {
            const section =
                document.createElement(
                    "div"
                );

            section.className =
                "probability-section";


            const title =
                document.createElement(
                    "p"
                );

            title.className =
                "probability-title";

            title.textContent =
                "Class probabilities";


            section.appendChild(
                title
            );


            const entries =
                Object.entries(
                    analysis.probabilities
                )
                .sort(
                    (
                        first,
                        second
                    ) => {
                        return (
                            Number(
                                second[1]
                            )
                            -
                            Number(
                                first[1]
                            )
                        );
                    }
                );


            for (
                const [
                    className,
                    probability,
                ]
                of entries
            ) {
                section.appendChild(
                    createProbabilityRow(
                        className,
                        probability
                    )
                );
            }


            information.appendChild(
                section
            );
        }

    } else {
        const error =
            document.createElement(
                "p"
            );

        error.className =
            "error-text";

        error.textContent =
            item.error
            || (
                "Analysis did not "
                + "complete."
            );

        information.appendChild(
            error
        );
    }


    content.append(
        preview,
        information
    );


    card.appendChild(
        content
    );


    return card;
}


function renderBatchResult(data) {
    batchSummary.replaceChildren();
    results.replaceChildren();

    batchSummary.append(
        createSummaryCard(
            "Total",
            data.total
        ),

        createSummaryCard(
            "Completed",
            data.completed
        ),

        createSummaryCard(
            "Rejected",
            data.rejected
        ),

        createSummaryCard(
            "Failed",
            data.failed
        )
    );

    data.items.forEach(
    (
        item,
        index
    ) => {
        const sourceFile =
            selectedFiles[
                index
            ];

        results.appendChild(
            renderResultItem(
                item,
                sourceFile
            )
        );
    }
);

    resultSection.hidden = false;
}


async function parseResponse(response) {
    const text =
        await response.text();

    if (!text) {
        return {};
    }

    try {
        return JSON.parse(text);
    } catch {
        return {
            detail: text,
        };
    }
}


function getErrorMessage(data) {
    if (
        typeof data.detail
        === "string"
    ) {
        return data.detail;
    }

    if (
        Array.isArray(
            data.detail
        )
    ) {
        return data.detail
            .map((item) => {
                return (
                    item.msg
                    || "Validation error"
                );
            })
            .join("; ");
    }

    return "Request failed.";
}
function formatHistoryDate(value) {
    if (!value) {
        return "—";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return String(value);
    }

    return date.toLocaleString();
}


function formatHistoryConfidence(value) {
    const numberValue =
        Number(value);

    if (
        !Number.isFinite(
            numberValue
        )
    ) {
        return "—";
    }

    const percentage =
        (
            numberValue <= 1
                ? numberValue * 100
                : numberValue
        );

    return (
        percentage.toFixed(2)
        + "%"
    );
}


function createHistoryDetail(
    label,
    value
) {
    const item =
        document.createElement(
            "li"
        );

    const strong =
        document.createElement(
            "strong"
        );

    strong.textContent =
        `${label}: `;

    item.appendChild(
        strong
    );

    item.appendChild(
        document.createTextNode(
            value ?? "—"
        )
    );

    return item;
}


function createHistoryProbabilityRow(
    className,
    probability
) {
    const row =
        document.createElement(
            "div"
        );

    row.className =
        "probability-row";


    const header =
        document.createElement(
            "div"
        );

    header.className =
        "probability-header";


    const label =
        document.createElement(
            "span"
        );

    label.className =
        "probability-class";

    label.textContent =
        className;


    const value =
        document.createElement(
            "span"
        );

    value.className =
        "probability-value";

    value.textContent =
        formatHistoryConfidence(
            probability
        );


    header.append(
        label,
        value
    );


    const track =
        document.createElement(
            "div"
        );

    track.className =
        "probability-track";


    const fill =
        document.createElement(
            "div"
        );

    fill.className =
        "probability-fill";


    const numericProbability =
        Number(probability);

    let percentage = 0;

    if (
        Number.isFinite(
            numericProbability
        )
    ) {
        percentage =
            (
                numericProbability <= 1
                    ? numericProbability * 100
                    : numericProbability
            );

        percentage =
            Math.max(
                0,
                Math.min(
                    100,
                    percentage
                )
            );
    }

    fill.style.width =
        `${percentage}%`;

    track.appendChild(
        fill
    );


    row.append(
        header,
        track
    );

    return row;
}


function createHistoryItem(
    analysis
) {
    const card =
        document.createElement(
            "article"
        );

    card.className =
        "history-item";


    const header =
        document.createElement(
            "div"
        );

    header.className =
        "history-item-header";


    const analysisCode =
        document.createElement(
            "div"
        );

    analysisCode.className =
        "history-analysis-code";

    analysisCode.textContent =
        (
            analysis.analysis_code
            || "Unknown analysis"
        );


    const date =
        document.createElement(
            "div"
        );

    date.className =
        "history-date";

    date.textContent =
        formatHistoryDate(
            analysis.created_at
        );


    header.append(
        analysisCode,
        date
    );

    card.appendChild(
        header
    );


    const prediction =
        document.createElement(
            "div"
        );

    prediction.className =
        "history-prediction";

    prediction.textContent =
        (
            analysis.predicted_class
                ? (
                    "Prediction: "
                    + analysis.predicted_class
                )
                : "Prediction: —"
        );

    card.appendChild(
        prediction
    );


    const details =
        document.createElement(
            "ul"
        );

    details.className =
        "result-details";

    details.append(
        createHistoryDetail(
            "Patient code",
            analysis.patient_code
        ),

        createHistoryDetail(
            "Filename",
            analysis.original_filename
        ),

        createHistoryDetail(
            "Status",
            analysis.status
        ),

        createHistoryDetail(
            "Model",
            (
                analysis.model_key
                && analysis.model_version
                    ? (
                        `${analysis.model_key} `
                        + `${analysis.model_version}`
                    )
                    : (
                        analysis.model_key
                        || "—"
                    )
            )
        ),

        createHistoryDetail(
            "Confidence",
            formatHistoryConfidence(
                analysis.confidence
            )
        )
    );

    card.appendChild(
        details
    );


    const probabilities =
        analysis.probabilities;

    if (
        probabilities
        && typeof probabilities === "object"
    ) {
        const entries =
            Object.entries(
                probabilities
            );

        if (entries.length > 0) {
            const section =
                document.createElement(
                    "div"
                );

            section.className =
                "probability-section";


            const title =
                document.createElement(
                    "div"
                );

            title.className =
                "probability-title";

            title.textContent =
                "Probabilities";


            section.appendChild(
                title
            );


            for (
                const [
                    className,
                    probability
                ]
                of entries
            ) {
                section.appendChild(
                    createHistoryProbabilityRow(
                        className,
                        probability
                    )
                );
            }

            card.appendChild(
                section
            );
        }
    }

    return card;
}


function renderAnalysisHistory(
    analyses,
    limit,
    offset
) {
    historyResults.replaceChildren();

    historySummary.hidden =
        false;

    historySummary.textContent =
        (
            `Showing ${analyses.length} record(s). `
            + `Offset: ${offset}. `
            + `Limit: ${limit}.`
        );


    if (analyses.length === 0) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "history-empty";

        empty.textContent =
            "No analysis history found.";

        historyResults.appendChild(
            empty
        );

    } else {
        for (
            const analysis
            of analyses
        ) {
            historyResults.appendChild(
                createHistoryItem(
                    analysis
                )
            );
        }
    }


    historyPreviousButton.disabled =
        offset <= 0;

    historyNextButton.disabled =
        analyses.length < limit;
}


function getHistoryRequestValues() {
    const limit =
        Number.parseInt(
            historyLimitInput.value,
            10
        );

    const offset =
        Number.parseInt(
            historyOffsetInput.value,
            10
        );


    if (
        !Number.isInteger(limit)
        || limit < 1
        || limit > 100
    ) {
        throw new Error(
            "Limit must be between 1 and 100."
        );
    }


    if (
        !Number.isInteger(offset)
        || offset < 0
    ) {
        throw new Error(
            "Offset must be 0 or greater."
        );
    }


    const patientCode =
        historyPatientCodeInput
            .value
            .trim()
            .toUpperCase();


    return {
        limit,
        offset,
        patientCode,
    };
}

function resetHistoryPaginationForQueryChange() {
    historyOffsetInput.value =
        "0";

    historyPreviousButton.disabled =
        true;

    historyNextButton.disabled =
        true;

    historySummary.hidden =
        true;

    historyResults.replaceChildren();
}


function resetAdminPaginationForQueryChange() {
    adminHistoryOffsetInput.value =
        "0";

    adminHistoryPreviousButton.disabled =
        true;

    adminHistoryNextButton.disabled =
        true;

    adminSearchSummary.hidden =
        true;

    adminSearchResults.replaceChildren();
}

async function loadAnalysisHistory(
    options = {}
) {
    const recoverEmptyNextPage =
        (
            options.recoverEmptyNextPage
            === true
        );

    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        historyStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    let requestValues;

    try {
        requestValues =
            getHistoryRequestValues();

    } catch (error) {
        historyStatus.textContent =
            error.message;

        return;
    }


    const {
        limit,
        offset,
        patientCode,
    } = requestValues;


    historyPatientCodeInput.value =
        patientCode;

    historyLimitInput.value =
        String(limit);

    historyOffsetInput.value =
        String(offset);


    const parameters =
        new URLSearchParams();

    parameters.set(
        "limit",
        String(limit)
    );

    parameters.set(
        "offset",
        String(offset)
    );

    if (patientCode) {
        parameters.set(
            "patient_code",
            patientCode
        );
    }


    loadHistoryButton.disabled =
        true;

    historyPreviousButton.disabled =
        true;

    historyNextButton.disabled =
        true;

    historyStatus.textContent =
        "Loading analysis history...";


    try {
        const response =
            await fetch(
                (
                    "/api/v1/analyses?"
                    + parameters.toString()
                ),
                {
                    method: "GET",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data
                )
            );
        }


        if (
            !Array.isArray(
                data
            )
        ) {
            throw new Error(
                "Unexpected history response."
            );
        }

            if (
            recoverEmptyNextPage
            && data.length === 0
            && offset > 0
        ) {
            const previousOffset =
                Math.max(
                    0,
                    offset - limit
                );

            historyOffsetInput.value =
                String(
                    previousOffset
                );

            historyStatus.textContent =
                (
                    "No records on the next page. "
                    + "Returning to the last "
                    + "available page..."
                );


            await loadAnalysisHistory();


            historyNextButton.disabled =
                true;

            historyStatus.textContent =
                (
                    "No more analysis records. "
                    + "Returned to the last "
                    + "available page."
                );

            return;
        }

        renderAnalysisHistory(
            data,
            limit,
            offset
        );

        historyStatus.textContent =
            (
                "Analysis history loaded successfully. "
                + `${data.length} record(s) returned.`
            );

    } catch (error) {
        historyResults.replaceChildren();

        historySummary.hidden =
            true;

        historyPreviousButton.disabled =
            true;

        historyNextButton.disabled =
            true;

        historyStatus.textContent =
            (
                "History request failed: "
                + error.message
            );

    } finally {
        loadHistoryButton.disabled =
            false;
    }
}
function clearPatientProfileForm() {
    profilePatientCodeInput.value = "";
    profileFullNameInput.value = "";
    profileBirthYearInput.value = "";
    profileGenderInput.value = "";
    profilePhoneInput.value = "";
    profileAddressInput.value = "";
}


function populatePatientProfile(
    profile
) {
    profilePatientCodeInput.value =
        profile.patient_code ?? "";

    profileFullNameInput.value =
        profile.full_name ?? "";

    profileBirthYearInput.value =
        profile.birth_year ?? "";

    profileGenderInput.value =
        profile.gender ?? "";

    profilePhoneInput.value =
        profile.phone ?? "";

    profileAddressInput.value =
        profile.address ?? "";
}


function optionalTextValue(input) {
    const value =
        input.value.trim();

    if (!value) {
        return null;
    }

    return value;
}


function buildPatientProfilePayload() {
    const fullName =
        profileFullNameInput
            .value
            .trim();

    if (!fullName) {
        throw new Error(
            "Full name is required."
        );
    }


    const birthYearText =
        profileBirthYearInput
            .value
            .trim();

    let birthYear = null;

    if (birthYearText) {
        birthYear =
            Number.parseInt(
                birthYearText,
                10
            );

        if (
            !Number.isInteger(
                birthYear
            )
        ) {
            throw new Error(
                "Birth year must be an integer."
            );
        }
    }


    return {
        full_name: fullName,
        birth_year: birthYear,
        gender:
            optionalTextValue(
                profileGenderInput
            ),
        phone:
            optionalTextValue(
                profilePhoneInput
            ),
        address:
            optionalTextValue(
                profileAddressInput
            ),
    };
}


async function loadPatientProfile() {
    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        profileStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    loadProfileButton.disabled =
        true;

    saveProfileButton.disabled =
        true;

    profileStatus.textContent =
        "Loading patient profile...";


    try {
        const response =
            await fetch(
                "/api/v1/patient-profile/me",
                {
                    method: "GET",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (response.status === 404) {
            patientProfileExists =
                false;

            clearPatientProfileForm();

            profileStatus.textContent =
                (
                    "Patient profile does not exist yet. "
                    + "Enter the information and "
                    + "click Save Profile."
                );

            return;
        }


        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data
                )
            );
        }


        patientProfileExists =
            true;

        populatePatientProfile(
            data
        );

        profileStatus.textContent =
            "Patient profile loaded successfully.";

    } catch (error) {
        profileStatus.textContent =
            (
                "Profile request failed: "
                + error.message
            );

    } finally {
        loadProfileButton.disabled =
            false;

        saveProfileButton.disabled =
            false;
    }
}


async function savePatientProfile() {
    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        profileStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    let payload;

    try {
        payload =
            buildPatientProfilePayload();

    } catch (error) {
        profileStatus.textContent =
            error.message;

        return;
    }


    const method =
        (
            patientProfileExists
                ? "PATCH"
                : "POST"
        );

    const endpoint =
        (
            patientProfileExists
                ? "/api/v1/patient-profile/me"
                : "/api/v1/patient-profile"
        );


    loadProfileButton.disabled =
        true;

    saveProfileButton.disabled =
        true;

    profileStatus.textContent =
        (
            patientProfileExists
                ? "Updating patient profile..."
                : "Creating patient profile..."
        );


    try {
        const response =
            await fetch(
                endpoint,
                {
                    method,

                    headers: {
                        Authorization:
                            `Bearer ${token}`,

                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify(
                            payload
                        ),
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data
                )
            );
        }


        patientProfileExists =
            true;

        populatePatientProfile(
            data
        );

        profileStatus.textContent =
            (
                method === "POST"
                    ? "Patient profile created successfully."
                    : "Patient profile updated successfully."
            );

    } catch (error) {
        profileStatus.textContent =
            (
                "Profile save failed: "
                + error.message
            );

    } finally {
        loadProfileButton.disabled =
            false;

        saveProfileButton.disabled =
            false;
    }
}
function parseMedicalHistoryList(
    value,
    fieldName
) {
    const trimmed =
        value.trim();

    if (!trimmed) {
        return null;
    }

    const items =
        trimmed
            .split(",")
            .map(
                (item) =>
                    item.trim()
            )
            .filter(
                (item) =>
                    item.length > 0
            );

    if (items.length > 50) {
        throw new Error(
            (
                `${fieldName} can contain `
                + "at most 50 items."
            )
        );
    }

    return items;
}


function medicalHistoryListToText(
    value
) {
    if (!Array.isArray(value)) {
        return "";
    }

    return value.join(", ");
}


function optionalMedicalHistoryText(
    input,
    maxLength,
    fieldName
) {
    const value =
        input.value.trim();

    if (!value) {
        return null;
    }

    if (value.length > maxLength) {
        throw new Error(
            (
                `${fieldName} can contain `
                + `at most ${maxLength} characters.`
            )
        );
    }

    return value;
}


function buildMedicalHistoryPayload() {
    return {
        diseases:
            parseMedicalHistoryList(
                medicalHistoryDiseasesInput.value,
                "Diseases"
            ),

        medications:
            parseMedicalHistoryList(
                medicalHistoryMedicationsInput.value,
                "Medications"
            ),

        allergies:
            parseMedicalHistoryList(
                medicalHistoryAllergiesInput.value,
                "Allergies"
            ),

        smoking_status:
            optionalMedicalHistoryText(
                medicalHistorySmokingStatusInput,
                30,
                "Smoking status"
            ),

        alcohol_status:
            optionalMedicalHistoryText(
                medicalHistoryAlcoholStatusInput,
                30,
                "Alcohol status"
            ),

        occupational_exposure:
            optionalMedicalHistoryText(
                medicalHistoryOccupationalExposureInput,
                2000,
                "Occupational exposure"
            ),

        notes:
            optionalMedicalHistoryText(
                medicalHistoryNotesInput,
                5000,
                "Notes"
            ),
    };
}


function formatMedicalHistoryDate(
    value
) {
    if (!value) {
        return "N/A";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return String(value);
    }

    return date.toLocaleString();
}


function clearMedicalHistoryEditor() {
    selectedMedicalHistoryId =
        null;

    medicalHistoryIdInput.value =
        "";

    medicalHistoryDiseasesInput.value =
        "";

    medicalHistoryMedicationsInput.value =
        "";

    medicalHistoryAllergiesInput.value =
        "";

    medicalHistorySmokingStatusInput.value =
        "";

    medicalHistoryAlcoholStatusInput.value =
        "";

    medicalHistoryOccupationalExposureInput.value =
        "";

    medicalHistoryNotesInput.value =
        "";

    medicalHistoryEditorTitle.textContent =
        "New Medical History";

    saveMedicalHistoryButton.textContent =
        "Create History";
}


function populateMedicalHistoryEditor(
    history
) {
    selectedMedicalHistoryId =
        history.id;

    medicalHistoryIdInput.value =
        String(
            history.id
        );

    medicalHistoryDiseasesInput.value =
        medicalHistoryListToText(
            history.diseases
        );

    medicalHistoryMedicationsInput.value =
        medicalHistoryListToText(
            history.medications
        );

    medicalHistoryAllergiesInput.value =
        medicalHistoryListToText(
            history.allergies
        );

    medicalHistorySmokingStatusInput.value =
        history.smoking_status ?? "";

    medicalHistoryAlcoholStatusInput.value =
        history.alcohol_status ?? "";

    medicalHistoryOccupationalExposureInput.value =
        history.occupational_exposure ?? "";

    medicalHistoryNotesInput.value =
        history.notes ?? "";

    medicalHistoryEditorTitle.textContent =
        (
            "Edit Medical History #"
            + history.id
        );

    saveMedicalHistoryButton.textContent =
        "Save Changes";
}


function createMedicalHistoryDetail(
    label,
    value
) {
    const item =
        document.createElement(
            "div"
        );

    item.className =
        "medical-history-detail";


    const strong =
        document.createElement(
            "strong"
        );

    strong.textContent =
        label;


    const content =
        document.createElement(
            "span"
        );

    content.textContent =
        value || "N/A";


    item.append(
        strong,
        content
    );

    return item;
}


function createMedicalHistoryCard(
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
            "h3"
        );

    title.textContent =
        (
            "Medical History #"
            + history.id
        );


    const recordedAt =
        document.createElement(
            "span"
        );

    recordedAt.textContent =
        formatMedicalHistoryDate(
            history.recorded_at
        );


    header.append(
        title,
        recordedAt
    );


    const details =
        document.createElement(
            "div"
        );

    details.className =
        "medical-history-details";


    details.append(
        createMedicalHistoryDetail(
            "Diseases",
            medicalHistoryListToText(
                history.diseases
            )
        ),

        createMedicalHistoryDetail(
            "Medications",
            medicalHistoryListToText(
                history.medications
            )
        ),

        createMedicalHistoryDetail(
            "Allergies",
            medicalHistoryListToText(
                history.allergies
            )
        ),

        createMedicalHistoryDetail(
            "Smoking status",
            history.smoking_status
        ),

        createMedicalHistoryDetail(
            "Alcohol status",
            history.alcohol_status
        ),

        createMedicalHistoryDetail(
            "Occupational exposure",
            history.occupational_exposure
        ),

        createMedicalHistoryDetail(
            "Notes",
            history.notes
        ),

        createMedicalHistoryDetail(
            "Updated",
            formatMedicalHistoryDate(
                history.updated_at
            )
        )
    );


    const actions =
        document.createElement(
            "div"
        );

    actions.className =
        "actions";


    const editButton =
        document.createElement(
            "button"
        );

    editButton.type =
        "button";

    editButton.className =
        "secondary";

    editButton.textContent =
        "Edit Record";

    editButton.addEventListener(
        "click",
        () => {
            loadMedicalHistoryById(
                history.id
            );
        }
    );


    actions.append(
        editButton
    );


    card.append(
        header,
        details,
        actions
    );

    return card;
}


function renderMedicalHistories(
    histories
) {
    medicalHistoryResults
        .replaceChildren();


    medicalHistorySummary.hidden =
        false;

    medicalHistorySummary.textContent =
        (
            "Medical history records: "
            + histories.length
        );


    if (histories.length === 0) {
        const empty =
            document.createElement(
                "p"
            );

        empty.className =
            "help-text";

        empty.textContent =
            (
                "No medical history "
                + "records were found."
            );

        medicalHistoryResults.append(
            empty
        );

        return;
    }


    for (
        const history
        of histories
    ) {
        medicalHistoryResults.append(
            createMedicalHistoryCard(
                history
            )
        );
    }
}


async function refreshMedicalHistories(
    token
) {
    const response =
        await fetch(
            "/api/v1/medical-histories",
            {
                method: "GET",

                headers: {
                    Authorization:
                        `Bearer ${token}`,
                },
            }
        );


    const data =
        await parseResponse(
            response
        );


    if (!response.ok) {
        throw new Error(
            getErrorMessage(
                data
            )
        );
    }


    if (!Array.isArray(data)) {
        throw new Error(
            (
                "Medical history response "
                + "must be an array."
            )
        );
    }


    renderMedicalHistories(
        data
    );

    return data;
}


async function loadMedicalHistories() {
    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        medicalHistoryStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    loadMedicalHistoriesButton.disabled =
        true;

    newMedicalHistoryButton.disabled =
        true;

    medicalHistoryStatus.textContent =
        "Loading medical histories...";


    try {
        const histories =
            await refreshMedicalHistories(
                token
            );

        medicalHistoryStatus.textContent =
            (
                "Medical histories loaded successfully. "
                + `${histories.length} record(s) returned.`
            );

    } catch (error) {
        medicalHistoryStatus.textContent =
            (
                "Medical history request failed: "
                + error.message
            );

    } finally {
        loadMedicalHistoriesButton.disabled =
            false;

        newMedicalHistoryButton.disabled =
            false;
    }
}


async function loadMedicalHistoryById(
    historyId
) {
    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        medicalHistoryStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    loadMedicalHistoriesButton.disabled =
        true;

    newMedicalHistoryButton.disabled =
        true;

    saveMedicalHistoryButton.disabled =
        true;

    medicalHistoryStatus.textContent =
        (
            "Loading medical history #"
            + historyId
            + "..."
        );


    try {
        const response =
            await fetch(
                (
                    "/api/v1/medical-histories/"
                    + encodeURIComponent(
                        historyId
                    )
                ),
                {
                    method: "GET",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data
                )
            );
        }


        populateMedicalHistoryEditor(
            data
        );

        medicalHistoryStatus.textContent =
            (
                "Medical history #"
                + historyId
                + " loaded for editing."
            );

    } catch (error) {
        medicalHistoryStatus.textContent =
            (
                "Medical history request failed: "
                + error.message
            );

    } finally {
        loadMedicalHistoriesButton.disabled =
            false;

        newMedicalHistoryButton.disabled =
            false;

        saveMedicalHistoryButton.disabled =
            false;
    }
}


async function saveMedicalHistory() {
    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        medicalHistoryStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    let payload;

    try {
        payload =
            buildMedicalHistoryPayload();

    } catch (error) {
        medicalHistoryStatus.textContent =
            error.message;

        return;
    }


    const isUpdate =
        (
            selectedMedicalHistoryId
            !== null
        );


    const method =
        (
            isUpdate
                ? "PATCH"
                : "POST"
        );


    const endpoint =
        (
            isUpdate
                ? (
                    "/api/v1/medical-histories/"
                    + encodeURIComponent(
                        selectedMedicalHistoryId
                    )
                )
                : "/api/v1/medical-histories"
        );


    loadMedicalHistoriesButton.disabled =
        true;

    newMedicalHistoryButton.disabled =
        true;

    saveMedicalHistoryButton.disabled =
        true;

    clearMedicalHistoryButton.disabled =
        true;


    medicalHistoryStatus.textContent =
        (
            isUpdate
                ? "Updating medical history..."
                : "Creating medical history..."
        );


    try {
        const response =
            await fetch(
                endpoint,
                {
                    method,

                    headers: {
                        Authorization:
                            `Bearer ${token}`,

                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify(
                            payload
                        ),
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data
                )
            );
        }


        populateMedicalHistoryEditor(
            data
        );


        await refreshMedicalHistories(
            token
        );


        medicalHistoryStatus.textContent =
            (
                isUpdate
                    ? (
                        "Medical history updated "
                        + "successfully."
                    )
                    : (
                        "Medical history created "
                        + "successfully."
                    )
            );

    } catch (error) {
        medicalHistoryStatus.textContent =
            (
                "Medical history save failed: "
                + error.message
            );

    } finally {
        loadMedicalHistoriesButton.disabled =
            false;

        newMedicalHistoryButton.disabled =
            false;

        saveMedicalHistoryButton.disabled =
            false;

        clearMedicalHistoryButton.disabled =
            false;
    }
}
function getAdminSearchRequestValues() {
    const patientCode =
        adminPatientCodeInput
            .value
            .trim()
            .toUpperCase();


    if (!patientCode) {
        throw new Error(
            "Patient code is required."
        );
    }


    const limit =
        Number.parseInt(
            adminHistoryLimitInput.value,
            10
        );


    if (
        !Number.isInteger(limit)
        || limit < 1
        || limit > 100
    ) {
        throw new Error(
            "Limit must be between 1 and 100."
        );
    }


    const offset =
        Number.parseInt(
            adminHistoryOffsetInput.value,
            10
        );


    if (
        !Number.isInteger(offset)
        || offset < 0
    ) {
        throw new Error(
            (
                "Offset must be greater than "
                + "or equal to 0."
            )
        );
    }


    return {
        patientCode,
        limit,
        offset,
    };
}
function renderAdminAnalysisHistory(
    analyses,
    patientCode,
    limit,
    offset
) {
    adminSearchResults
        .replaceChildren();


    adminSearchSummary.hidden =
        false;

    adminSearchSummary.textContent =
        (
            `Patient ${patientCode} | `
            + `${analyses.length} record(s) | `
            + `Offset ${offset} | `
            + `Limit ${limit}`
        );


    if (analyses.length === 0) {
        const emptyMessage =
            document.createElement(
                "p"
            );

        emptyMessage.className =
            "help-text";

        emptyMessage.textContent =
            (
                "No analysis records "
                + "were found on this page."
            );

        adminSearchResults.append(
            emptyMessage
        );

    } else {

        for (
            const analysis
            of analyses
        ) {
            adminSearchResults.append(
                createHistoryItem(
                    analysis
                )
            );
        }
    }


    adminHistoryPreviousButton.disabled =
        offset <= 0;


    adminHistoryNextButton.disabled =
        analyses.length < limit;
}
async function loadAdminAnalysisHistory(
    options = {}
) {
    const recoverEmptyNextPage =
        (
            options.recoverEmptyNextPage
            === true
        );

    const token =
        normalizeToken(
            tokenInput.value
        );


    if (!token) {
        adminSearchStatus.textContent =
            "An access token is required.";

        tokenInput.focus();

        return;
    }


    let requestValues;

    try {
        requestValues =
            getAdminSearchRequestValues();

    } catch (error) {
        adminSearchStatus.textContent =
            error.message;

        return;
    }


    const {
        patientCode,
        limit,
        offset,
    } = requestValues;


    adminPatientCodeInput.value =
        patientCode;

    adminHistoryLimitInput.value =
        String(limit);

    adminHistoryOffsetInput.value =
        String(offset);


    const params =
        new URLSearchParams();


    params.set(
        "patient_code",
        patientCode
    );

    params.set(
        "limit",
        String(limit)
    );

    params.set(
        "offset",
        String(offset)
    );


    adminSearchButton.disabled =
        true;

    adminHistoryPreviousButton.disabled =
        true;

    adminHistoryNextButton.disabled =
        true;


    adminSearchStatus.textContent =
        (
            "Searching analysis history "
            + `for ${patientCode}...`
        );


    try {
        const response =
            await fetch(
                (
                    "/api/v1/admin/analyses?"
                    + params.toString()
                ),
                {
                    method: "GET",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data
                )
            );
        }


        if (!Array.isArray(data)) {
            throw new Error(
                (
                    "ADMIN analysis response "
                    + "must be an array."
                )
            );
        }

        if (
            recoverEmptyNextPage
            && data.length === 0
            && offset > 0
        ) {
            const previousOffset =
                Math.max(
                    0,
                    offset - limit
                );

            adminHistoryOffsetInput.value =
                String(
                    previousOffset
                );

            adminSearchStatus.textContent =
                (
                    "No records on the next page. "
                    + "Returning to the last "
                    + "available page..."
                );


            await loadAdminAnalysisHistory();


            adminHistoryNextButton.disabled =
                true;

            adminSearchStatus.textContent =
                (
                    "No more analysis records. "
                    + "Returned to the last "
                    + "available page."
                );

            return;
        }

        renderAdminAnalysisHistory(
            data,
            patientCode,
            limit,
            offset
        );


        adminSearchStatus.textContent =
            (
                "ADMIN patient search "
                + "completed successfully. "
                + `${data.length} record(s) returned.`
            );

    } catch (error) {
        adminSearchResults.replaceChildren();

        adminSearchSummary.hidden =
            true;

        adminHistoryPreviousButton.disabled =
            true;

        adminHistoryNextButton.disabled =
            true;

        adminSearchStatus.textContent =
            (
                "ADMIN search failed: "
                + error.message
            );

    } finally {
        adminSearchButton.disabled =
            false;
    }
}
async function analyzeBatch() {
    const validation =
        validateFiles(
            selectedFiles
        );

    if (!validation.valid) {
        showValidation(
            validation.message
        );

        return;
    }


    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        requestStatus.textContent =
            "A USER access token is required.";

        tokenInput.focus();

        return;
    }


    const formData =
        new FormData();


    for (
        const file
        of selectedFiles
    ) {
        formData.append(
            "files",
            file,
            file.name
        );
    }


    const modelId =
        modelIdInput.value.trim();

    if (modelId) {
        formData.append(
            "model_id",
            modelId
        );
    }


    setLoading(true);

    resultSection.hidden = true;


    try {
        const response =
            await fetch(
                "/api/v1/analyses/batch",
                {
                    method: "POST",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },

                    body: formData,
                }
            );


        const data =
            await parseResponse(
                response
            );


        if (!response.ok) {
            throw new Error(
                getErrorMessage(data)
            );
        }


        renderBatchResult(data);

        requestStatus.textContent =
            (
                "Batch analysis completed. "
                + `${data.completed} completed, `
                + `${data.rejected} rejected, `
                + `${data.failed} failed.`
            );

    } catch (error) {
        requestStatus.textContent =
            (
                "Request failed: "
                + error.message
            );

    } finally {
        setLoading(false);
    }
}


filesInput.addEventListener(
    "change",
    () => {
        folderInput.value = "";

        applySelection(
            filesInput.files,
            "Individual files"
        );
    }
);


folderInput.addEventListener(
    "change",
    () => {
        filesInput.value = "";

        applySelection(
            folderInput.files,
            "Folder"
        );
    }
);


clearButton.addEventListener(
    "click",
    () => {
        selectedFiles = [];

        selectionSource = "";

        ignoredFileCount = 0;

        filesInput.value = "";

        folderInput.value = "";

        resultSection.hidden = true;

        results.replaceChildren();
        batchSummary.replaceChildren();

        requestStatus.textContent =
            "Waiting for images.";

        renderSelectedFiles();
    }
);


analyzeButton.addEventListener(
    "click",
    analyzeBatch
);


loadHistoryButton.addEventListener(
    "click",
    loadAnalysisHistory
);


historyPreviousButton.addEventListener(
    "click",
    () => {
        const limit =
            Number.parseInt(
                historyLimitInput.value,
                10
            );

        const offset =
            Number.parseInt(
                historyOffsetInput.value,
                10
            );

        if (
            !Number.isInteger(limit)
            || limit < 1
        || limit > 100
            || !Number.isInteger(offset)
            || offset < 0
        ) {
            historyStatus.textContent =
            "Invalid pagination values.";

        return;
        }

        historyOffsetInput.value =
            String(
                Math.max(
                    0,
                    offset - limit
                )
            );

        loadAnalysisHistory();
    }
);


historyNextButton.addEventListener(
    "click",
    () => {
        const limit =
            Number.parseInt(
                historyLimitInput.value,
                10
            );

        const offset =
            Number.parseInt(
                historyOffsetInput.value,
                10
            );
    if (
            !Number.isInteger(limit)
            || limit < 1
            || limit > 100
            || !Number.isInteger(offset)
            || offset < 0
    ) {
            historyStatus.textContent =
            "Invalid pagination values.";

            return;
    }

        historyOffsetInput.value =
            String(
                offset + limit
            );

        loadAnalysisHistory(
            {
                recoverEmptyNextPage:
                    true,
            }
        );
    }
);
historyLimitInput.addEventListener(
    "change",
    () => {
        resetHistoryPaginationForQueryChange();

        historyStatus.textContent =
            (
                "Pagination settings changed. "
                + "Click Load History to reload."
            );
    }
);


historyPatientCodeInput.addEventListener(
    "input",
    () => {
        resetHistoryPaginationForQueryChange();

        historyStatus.textContent =
            (
                "Patient filter changed. "
                + "Click Load History to reload."
            );
    }
);

loadProfileButton.addEventListener(
    "click",
    loadPatientProfile
);


saveProfileButton.addEventListener(
    "click",
    savePatientProfile
);
loadMedicalHistoriesButton.addEventListener(
    "click",
    loadMedicalHistories
);


newMedicalHistoryButton.addEventListener(
    "click",
    () => {
        clearMedicalHistoryEditor();

        medicalHistoryStatus.textContent =
            (
                "Ready to create a new "
                + "medical history record."
            );
    }
);


saveMedicalHistoryButton.addEventListener(
    "click",
    saveMedicalHistory
);


clearMedicalHistoryButton.addEventListener(
    "click",
    () => {
        clearMedicalHistoryEditor();

        medicalHistoryStatus.textContent =
            "Medical history editor cleared.";
    }
);

adminSearchButton.addEventListener(
    "click",
    loadAdminAnalysisHistory
);


adminHistoryPreviousButton.addEventListener(
    "click",
    () => {
        const limit =
            Number.parseInt(
                adminHistoryLimitInput.value,
                10
            );

        const offset =
            Number.parseInt(
                adminHistoryOffsetInput.value,
                10
            );


        if (
            !Number.isInteger(limit)
            || limit < 1
            || limit > 100
            || !Number.isInteger(offset)
            || offset < 0
        ) {
            return;
        }


        adminHistoryOffsetInput.value =
            String(
                Math.max(
                    0,
                    offset - limit
                )
            );


        loadAdminAnalysisHistory();
    }
);


adminHistoryNextButton.addEventListener(
    "click",
    () => {
        const limit =
            Number.parseInt(
                adminHistoryLimitInput.value,
                10
            );

        const offset =
            Number.parseInt(
                adminHistoryOffsetInput.value,
                10
            );


        if (
            !Number.isInteger(limit)
            || limit < 1
            || limit > 100
            || !Number.isInteger(offset)
            || offset < 0
        ) {
            return;
        }


        adminHistoryOffsetInput.value =
            String(
                offset + limit
            );


                loadAdminAnalysisHistory(
            {
                recoverEmptyNextPage:
                    true,
            }
        );
    }
);

adminHistoryLimitInput.addEventListener(
    "change",
    () => {
        resetAdminPaginationForQueryChange();

        adminSearchStatus.textContent =
            (
                "Pagination settings changed. "
                + "Click Search Patient to reload."
            );
    }
);


adminPatientCodeInput.addEventListener(
    "input",
    () => {
        resetAdminPaginationForQueryChange();

        adminSearchStatus.textContent =
            (
                "Patient code changed. "
                + "Click Search Patient to reload."
            );
    }
);

renderSelectedFiles();