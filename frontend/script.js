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

const profileFullNameInput =
    document.getElementById(
        "profile-full-name"
    );

const profileDateOfBirthInput =
    document.getElementById(
        "profile-date-of-birth"
    );

const profileSexInput =
    document.getElementById(
        "profile-sex"
    );

const profilePhoneInput =
    document.getElementById(
        "profile-phone"
    );

const profileEmailInput =
    document.getElementById(
        "profile-email"
    );

const profileHeightInput =
    document.getElementById(
        "profile-height"
    );

const profileWeightInput =
    document.getElementById(
        "profile-weight"
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

const medicalHistoryCurrentComplaintInput =
    document.getElementById(
        "medical-history-current-complaint"
    );

const medicalHistoryPastMedicalInput =
    document.getElementById(
        "medical-history-past-medical"
    );

const medicalHistoryPastMedicationInput =
    document.getElementById(
        "medical-history-past-medication"
    );

const medicalHistoryAllergyInput =
    document.getElementById(
        "medical-history-allergy"
    );

const medicalHistoryDietInput =
    document.getElementById(
        "medical-history-diet"
    );

const medicalHistoryAppetiteInput =
    document.getElementById(
        "medical-history-appetite"
    );

const medicalHistorySleepInput =
    document.getElementById(
        "medical-history-sleep"
    );

const medicalHistoryExerciseInput =
    document.getElementById(
        "medical-history-exercise"
    );

const medicalHistoryBowelBladderInput =
    document.getElementById(
        "medical-history-bowel-bladder"
    );

const medicalHistoryHabitsInput =
    document.getElementById(
        "medical-history-habits"
    );

const medicalHistoryFamilyInput =
    document.getElementById(
        "medical-history-family"
    );

const saveMedicalHistoryButton =
    document.getElementById(
        "save-medical-history-button"
    );

const clearMedicalHistoryButton =
    document.getElementById(
        "clear-medical-history-button"
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
function formatProbabilityClassName(
    className
) {
    const normalized =
        String(
            className ?? ""
        )
            .trim()
            .replace(
                /[_-]+/g,
                " "
            );

    if (!normalized) {
        return "Unknown";
    }

    return normalized.replace(
        /\b\w/g,
        (character) =>
            character.toUpperCase()
    );
}


function normalizeProbabilityEntries(
    probabilities
) {
    if (
        !probabilities
        || typeof probabilities !== "object"
        || Array.isArray(probabilities)
    ) {
        return [];
    }

    const entries = [];

    for (
        const [
            className,
            value,
        ]
        of Object.entries(
            probabilities
        )
    ) {
        const numericValue =
            Number(value);

        if (
            !Number.isFinite(
                numericValue
            )
        ) {
            continue;
        }

        const percent =
            probabilityToPercent(
                numericValue
            );

        entries.push(
            {
                className:
                    String(className),
                displayName:
                    formatProbabilityClassName(
                        className
                    ),
                value:
                    numericValue,
                percent,
                formattedPercent:
                    `${percent.toFixed(2)}%`,
            }
        );
    }

    entries.sort(
        (
            first,
            second
        ) => {
            const probabilityDifference =
                second.percent
                - first.percent;

            if (
                probabilityDifference !== 0
            ) {
                return probabilityDifference;
            }

            return (
                first.displayName
                    .localeCompare(
                        second.displayName
                    )
            );
        }
    );

    return entries;
}

function createProbabilityBarRow(
    entry
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
        entry.displayName;


    const valueElement =
        document.createElement(
            "span"
        );

    valueElement.className =
        "probability-value";

    valueElement.textContent =
        entry.formattedPercent;


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

    track.setAttribute(
        "role",
        "progressbar"
    );

    track.setAttribute(
        "aria-label",
        `${entry.displayName} probability`
    );

    track.setAttribute(
        "aria-valuemin",
        "0"
    );

    track.setAttribute(
        "aria-valuemax",
        "100"
    );

    track.setAttribute(
        "aria-valuenow",
        entry.percent.toFixed(2)
    );


    const fill =
        document.createElement(
            "div"
        );

    fill.className =
        "probability-fill";

    fill.style.width =
        `${entry.percent}%`;


    track.appendChild(
        fill
    );

    row.append(
        header,
        track
    );

    return row;
}


function createProbabilityBarChart(
    entries
) {
    const chart =
        document.createElement(
            "div"
        );

    chart.className =
        "probability-bar-chart";


    for (
        const entry
        of entries
    ) {
        chart.appendChild(
            createProbabilityBarRow(
                entry
            )
        );
    }


    return chart;
}

function createProbabilityColumnChart(
    entries
) {
    const chart =
        document.createElement(
            "div"
        );

    chart.className =
        "probability-column-chart";

    chart.setAttribute(
        "aria-label",
        "Class probability column chart"
    );


    for (
        const entry
        of entries
    ) {
        const item =
            document.createElement(
                "div"
            );

        item.className =
            "probability-column-item";


        const value =
            document.createElement(
                "div"
            );

        value.className =
            "probability-column-value";

        value.textContent =
            entry.formattedPercent;


        const plot =
            document.createElement(
                "div"
            );

        plot.className =
            "probability-column-plot";


        const column =
            document.createElement(
                "div"
            );

        column.className =
            "probability-column";

        column.style.height =
            `${entry.percent}%`;

        column.setAttribute(
            "role",
            "progressbar"
        );

        column.setAttribute(
            "aria-label",
            `${entry.displayName} probability`
        );

        column.setAttribute(
            "aria-valuemin",
            "0"
        );

        column.setAttribute(
            "aria-valuemax",
            "100"
        );

        column.setAttribute(
            "aria-valuenow",
            entry.percent.toFixed(2)
        );


        const label =
            document.createElement(
                "div"
            );

        label.className =
            "probability-column-label";

        label.textContent =
            entry.displayName;


        plot.appendChild(
            column
        );

        item.append(
            value,
            plot,
            label
        );

        chart.appendChild(
            item
        );
    }


    return chart;
}

function createProbabilityDonutChart(
    entries
) {
    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "probability-donut-chart";


    const visual =
        document.createElement(
            "div"
        );

    visual.className =
        "probability-donut-visual";


    const svgNamespace =
        "http://www.w3.org/2000/svg";

    const svg =
        document.createElementNS(
            svgNamespace,
            "svg"
        );

    svg.classList.add(
        "probability-donut-svg"
    );

    svg.setAttribute(
        "viewBox",
        "0 0 120 120"
    );

    svg.setAttribute(
        "role",
        "img"
    );

    svg.setAttribute(
        "aria-label",
        "Class probability donut chart"
    );


    const track =
        document.createElementNS(
            svgNamespace,
            "circle"
        );

    track.classList.add(
        "probability-donut-track"
    );

    track.setAttribute(
        "cx",
        "60"
    );

    track.setAttribute(
        "cy",
        "60"
    );

    track.setAttribute(
        "r",
        "44"
    );


    svg.appendChild(
        track
    );


    const totalPercent =
        entries.reduce(
            (
                total,
                entry
            ) =>
                total
                + entry.percent,
            0
        );


    let cumulativePercent =
        0;


    entries.forEach(
        (
            entry,
            index
        ) => {
            const slicePercent =
                totalPercent > 0
                    ? (
                        entry.percent
                        / totalPercent
                        * 100
                    )
                    : 0;


            const slice =
                document.createElementNS(
                    svgNamespace,
                    "circle"
                );

            slice.classList.add(
                "probability-donut-slice",
                `probability-donut-slice-${index + 1}`
            );

            slice.setAttribute(
                "cx",
                "60"
            );

            slice.setAttribute(
                "cy",
                "60"
            );

            slice.setAttribute(
                "r",
                "44"
            );

            slice.setAttribute(
                "pathLength",
                "100"
            );

            slice.setAttribute(
                "stroke-dasharray",
                `${slicePercent} ${100 - slicePercent}`
            );

            slice.setAttribute(
                "stroke-dashoffset",
                `${-cumulativePercent}`
            );

            slice.setAttribute(
                "transform",
                "rotate(-90 60 60)"
            );


            const title =
                document.createElementNS(
                    svgNamespace,
                    "title"
                );

            title.textContent =
                `${entry.displayName}: ${entry.formattedPercent}`;


            slice.appendChild(
                title
            );

            svg.appendChild(
                slice
            );


            cumulativePercent +=
                slicePercent;
        }
    );


    visual.appendChild(
        svg
    );


    const legend =
        document.createElement(
            "div"
        );

    legend.className =
        "probability-donut-legend";


    entries.forEach(
        (
            entry,
            index
        ) => {
            const legendItem =
                document.createElement(
                    "div"
                );

            legendItem.className =
                "probability-donut-legend-item";


            const marker =
                document.createElement(
                    "span"
                );

            marker.classList.add(
                "probability-donut-legend-marker",
                `probability-donut-marker-${index + 1}`
            );

            marker.setAttribute(
                "aria-hidden",
                "true"
            );


            const label =
                document.createElement(
                    "span"
                );

            label.className =
                "probability-donut-legend-label";

            label.textContent =
                entry.displayName;


            const value =
                document.createElement(
                    "span"
                );

            value.className =
                "probability-donut-legend-value";

            value.textContent =
                entry.formattedPercent;


            legendItem.append(
                marker,
                label,
                value
            );

            legend.appendChild(
                legendItem
            );
        }
    );


    wrapper.append(
        visual,
        legend
    );

    return wrapper;
}

function createProbabilityTable(
    entries,
    predictedClass
) {
    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "probability-table-wrapper";


    const table =
        document.createElement(
            "table"
        );

    table.className =
        "probability-table";

    table.setAttribute(
        "aria-label",
        "Class probability table"
    );


    const caption =
        document.createElement(
            "caption"
        );

    caption.textContent =
        "Probability table";


    const head =
        document.createElement(
            "thead"
        );

    const headRow =
        document.createElement(
            "tr"
        );

    for (
        const heading
        of [
            "Class",
            "Probability",
            "Result",
        ]
    ) {
        const cell =
            document.createElement(
                "th"
            );

        cell.scope =
            "col";

        cell.textContent =
            heading;

        headRow.appendChild(
            cell
        );
    }

    head.appendChild(
        headRow
    );


    const body =
        document.createElement(
            "tbody"
        );

    const normalizedPrediction =
        String(
            predictedClass ?? ""
        )
            .trim()
            .toLowerCase();


    for (
        const entry
        of entries
    ) {
        const row =
            document.createElement(
                "tr"
            );

        const normalizedClass =
            String(
                entry.className
            )
                .trim()
                .toLowerCase();

        const isPredicted =
            (
                normalizedPrediction
                && normalizedClass
                === normalizedPrediction
            );

        if (isPredicted) {
            row.classList.add(
                "probability-table-row-predicted"
            );
        }


        const classCell =
            document.createElement(
                "td"
            );

        classCell.textContent =
            entry.displayName;


        const probabilityCell =
            document.createElement(
                "td"
            );

        probabilityCell.className =
            "probability-table-number";

        probabilityCell.textContent =
            entry.formattedPercent;


        const resultCell =
            document.createElement(
                "td"
            );

        resultCell.className =
            "probability-table-result";

        resultCell.textContent =
            isPredicted
                ? "Predicted"
                : "—";


        row.append(
            classCell,
            probabilityCell,
            resultCell
        );

        body.appendChild(
            row
        );
    }


    table.append(
        caption,
        head,
        body
    );

    wrapper.appendChild(
        table
    );

    return wrapper;
}

function createProbabilityVisualizationSwitcher(
    entries,
    predictedClass
) {
    const viewer =
        document.createElement(
            "div"
        );

    viewer.className =
        "probability-viewer";


    const switcher =
        document.createElement(
            "div"
        );

    switcher.className =
        "probability-view-switcher";

    switcher.setAttribute(
        "role",
        "group"
    );

    switcher.setAttribute(
        "aria-label",
        "Probability visualization type"
    );


    const content =
        document.createElement(
            "div"
        );

    content.className =
        "probability-view-content";


    const views = [
        {
            key: "bar",
            label: "Bar",
            element:
                createProbabilityBarChart(
                    entries
                ),
        },
        {
            key: "column",
            label: "Column",
            element:
                createProbabilityColumnChart(
                    entries
                ),
        },
        {
            key: "donut",
            label: "Donut",
            element:
                createProbabilityDonutChart(
                    entries
                ),
        },
        {
            key: "table",
            label: "Table",
            element:
                createProbabilityTable(
                    entries,
                    predictedClass
                ),
        },
    ];


    const buttons = [];
    const panels = [];


    for (
        const [
            index,
            view,
        ]
        of views.entries()
    ) {
        const isActive =
            index === 0;


        const button =
            document.createElement(
                "button"
            );

        button.type =
            "button";

        button.className =
            "probability-view-button";

        button.textContent =
            view.label;

        button.dataset.view =
            view.key;

        button.setAttribute(
            "aria-pressed",
            isActive
                ? "true"
                : "false"
        );


        const panel =
            document.createElement(
                "div"
            );

        panel.className =
            "probability-view-panel";

        panel.dataset.view =
            view.key;

        panel.hidden =
            !isActive;

        panel.appendChild(
            view.element
        );


        buttons.push(
            button
        );

        panels.push(
            panel
        );

        switcher.appendChild(
            button
        );

        content.appendChild(
            panel
        );
    }


    buttons.forEach(
        (
            button,
            selectedIndex
        ) => {
            button.addEventListener(
                "click",
                () => {
                    buttons.forEach(
                        (
                            currentButton,
                            currentIndex
                        ) => {
                            const isActive =
                                currentIndex
                                === selectedIndex;

                            currentButton.setAttribute(
                                "aria-pressed",
                                isActive
                                    ? "true"
                                    : "false"
                            );

                            panels[
                                currentIndex
                            ].hidden =
                                !isActive;
                        }
                    );
                }
            );
        }
    );


    viewer.append(
        switcher,
        content
    );

    return viewer;
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
                normalizeProbabilityEntries(
                    analysis.probabilities
                );

            section.appendChild(
                createProbabilityVisualizationSwitcher(
                    entries,
                    analysis.predicted_class
                )
            );

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


    const reportControls =
        createReportControls(
            item
        );

    if (reportControls !== null) {
        card.appendChild(
            reportControls
        );
    }

    const drAIControls =
        createDrAIControls(
            item,
            {autoGenerate: true}
        );

    if (drAIControls !== null) {
        card.appendChild(
            drAIControls
        );
    }

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

    applyResultFilter(
        activeResultFilter
    );
}


function getReportAccessToken() {
    const input =
        document.getElementById(
            "token-input"
        );

    if (!input) {
        return "";
    }

    return input.value.trim();
}


function getReportAnalysisId(
    analysisLike
) {
    const candidates = [
        analysisLike?.id,
        analysisLike?.analysis_id,
        analysisLike?.analysis?.id,
        analysisLike?.result?.id,
    ];

    for (
        const candidate
        of candidates
    ) {
        const analysisId =
            Number(candidate);

        if (
            Number.isInteger(
                analysisId
            )
            && analysisId > 0
        ) {
            return analysisId;
        }
    }

    return null;
}


function getReportAnalysisStatus(
    analysisLike
) {
    const status =
        (
            analysisLike?.status
            ?? analysisLike?.analysis?.status
            ?? analysisLike?.result?.status
            ?? ""
        );

    return String(
        status
    ).trim().toUpperCase();
}


function getReportErrorMessage(
    payload,
    fallback
) {
    if (
        payload
        && typeof payload === "object"
        && payload.detail
    ) {
        return String(
            payload.detail
        );
    }

    if (
        typeof payload === "string"
        && payload.trim()
    ) {
        return payload.trim();
    }

    return fallback;
}


async function fetchReportPdf(
    reportId,
    action,
    token
) {
    const response =
        await fetch(
            (
                "/api/v1/reports/"
                + encodeURIComponent(
                    reportId
                )
                + "/"
                + action
            ),
            {
                method: "GET",

                headers: {
                    Authorization:
                        `Bearer ${token}`,
                },
            }
        );

    if (!response.ok) {
        const payload =
            await parseResponse(
                response
            );

        throw new Error(
            getReportErrorMessage(
                payload,
                (
                    "PDF request failed "
                    + `(${response.status}).`
                )
            )
        );
    }

    const blob =
        await response.blob();

    if (
        blob.size === 0
    ) {
        throw new Error(
            "The generated PDF is empty."
        );
    }

    return blob;
}


function createReportControls(
    analysisLike
) {
    const analysisId =
        getReportAnalysisId(
            analysisLike
        );

    const analysisStatus =
        getReportAnalysisStatus(
            analysisLike
        );


    if (
        analysisId === null
        || analysisStatus !== "COMPLETED"
    ) {
        return null;
    }


    const container =
        document.createElement(
            "div"
        );

    container.className =
        "report-actions";

    container.dataset.analysisId =
        String(
            analysisId
        );


    const title =
        document.createElement(
            "strong"
        );

    title.className =
        "report-actions-title";

    title.textContent =
        "PDF Report";


    const controls =
        document.createElement(
            "div"
        );

    controls.className =
        "report-actions-row";


    const languageSelect =
        document.createElement(
            "select"
        );

    languageSelect.className =
        "report-language-select";

    languageSelect.setAttribute(
        "aria-label",
        "Report language"
    );


    const viOption =
        document.createElement(
            "option"
        );

    viOption.value =
        "vi";

    viOption.textContent =
        "Vietnamese";


    const enOption =
        document.createElement(
            "option"
        );

    enOption.value =
        "en";

    enOption.textContent =
        "English";


    languageSelect.append(
        viOption,
        enOption
    );


    const previewButton =
        document.createElement(
            "button"
        );

    previewButton.type =
        "button";

    previewButton.className =
        "report-preview-button";

    previewButton.textContent =
        "Preview";


    const downloadButton =
        document.createElement(
            "button"
        );

    downloadButton.type =
        "button";

    downloadButton.className =
        "secondary report-download-button";

    downloadButton.textContent =
        "Download";


    const status =
        document.createElement(
            "div"
        );

    status.className =
        "report-action-status";

    status.textContent =
        "Ready to preview or download.";


    let currentReportId =
        null;

    let currentReportCode =
        null;


    async function ensureReport(
        token
    ) {
        if (
            currentReportId !== null
        ) {
            return;
        }


        status.textContent =
            "Generating PDF report...";


        const response =
            await fetch(
                "/api/v1/reports",
                {
                    method:
                        "POST",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,

                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify(
                            {
                                analysis_id:
                                    analysisId,

                                language:
                                    languageSelect.value,
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
                getReportErrorMessage(
                    payload
                )
            );
        }


        const reportId =
            Number(
                payload.id
            );


        if (
            !Number.isInteger(
                reportId
            )
            || reportId <= 0
        ) {
            throw new Error(
                "The report API returned "
                + "an invalid report ID."
            );
        }


        currentReportId =
            reportId;

        currentReportCode =
            (
                payload.report_code
                || (
                    "report-"
                    + reportId
                )
            );
    }


    function setControlsDisabled(
        disabled
    ) {
        languageSelect.disabled =
            disabled;

        previewButton.disabled =
            disabled;

        downloadButton.disabled =
            disabled;
    }


    languageSelect.addEventListener(
        "change",
        () => {
            currentReportId =
                null;

            currentReportCode =
                null;

            status.textContent =
                (
                    "Language changed. "
                    + "A new report will "
                    + "be generated."
                );
        }
    );


    previewButton.addEventListener(
        "click",
        async () => {
            const token =
                getReportAccessToken();

            if (!token) {
                status.textContent =
                    "Please sign in first.";

                return;
            }


            const previewWindow =
                window.open(
                    "",
                    "_blank"
                );


            if (!previewWindow) {
                status.textContent =
                    (
                        "Preview was blocked "
                        + "by the browser. "
                        + "Please allow pop-ups."
                    );

                return;
            }


            previewWindow.opener =
                null;

            previewWindow.document.title =
                "PDF Preview";

            previewWindow.document.body.textContent =
                "Preparing PDF preview...";


            setControlsDisabled(
                true
            );


            try {
                await ensureReport(
                    token
                );


                status.textContent =
                    "Loading PDF preview...";


                const blob =
                    await fetchReportPdf(
                        currentReportId,
                        "preview",
                        token
                    );


                const objectUrl =
                    URL.createObjectURL(
                        blob
                    );


                previewWindow.location.replace(
                    objectUrl
                );


                window.setTimeout(
                    () => {
                        URL.revokeObjectURL(
                            objectUrl
                        );
                    },
                    60000
                );


                status.textContent =
                    "PDF preview opened.";

            } catch (error) {
                previewWindow.close();

                status.textContent =
                    (
                        "Preview failed: "
                        + error.message
                    );

            } finally {
                setControlsDisabled(
                    false
                );
            }
        }
    );


    downloadButton.addEventListener(
        "click",
        async () => {
            const token =
                getReportAccessToken();

            if (!token) {
                status.textContent =
                    "Please sign in first.";

                return;
            }


            setControlsDisabled(
                true
            );


            try {
                await ensureReport(
                    token
                );


                status.textContent =
                    "Preparing PDF download...";


                const blob =
                    await fetchReportPdf(
                        currentReportId,
                        "download",
                        token
                    );


                const objectUrl =
                    URL.createObjectURL(
                        blob
                    );


                const link =
                    document.createElement(
                        "a"
                    );

                link.href =
                    objectUrl;

                link.download =
                    (
                        (
                            currentReportCode
                            || (
                                "report-"
                                + currentReportId
                            )
                        )
                        + ".pdf"
                    );


                document.body.appendChild(
                    link
                );

                link.click();

                link.remove();


                window.setTimeout(
                    () => {
                        URL.revokeObjectURL(
                            objectUrl
                        );
                    },
                    1000
                );


                status.textContent =
                    "PDF download started.";

            } catch (error) {
                status.textContent =
                    (
                        "Download failed: "
                        + error.message
                    );

            } finally {
                setControlsDisabled(
                    false
                );
            }
        }
    );


    controls.append(
        languageSelect,
        previewButton,
        downloadButton
    );


    container.append(
        title,
        controls,
        status
    );


    return container;
}


function getDrAIErrorMessage(
    response,
    data
) {
    const detail =
        getErrorMessage(data);

    const detailText =
        typeof detail === "string"
            ? detail.trim()
            : "";

    if (response.status === 401) {
        return (
            "Session expired or the access "
            + "token is invalid."
        );
    }

    if (response.status === 400) {
        return (
            detailText
            || "This analysis cannot be "
            + "used by Dr.AI."
        );
    }

    if (response.status === 404) {
        return (
            detailText
            || "Analysis or Dr.AI advice "
            + "was not found."
        );
    }

    if (response.status === 502) {
        return (
            detailText || "Dr.AI provider failed to "
            + "generate a response."
        );
    }

    if (response.status === 503) {
        return (
            detailText || "Dr.AI is not configured "
            + "on the server."
        );
    }

    return (
        detailText
        || (
            "Dr.AI request failed "
            + `(${response.status}).`
        )
    );
}


function createDrAIAdviceCard(
    advice
) {
    const card =
        document.createElement(
            "article"
        );

    card.className =
        "drai-advice-card";

    const meta =
        document.createElement(
            "div"
        );

    meta.className =
        "drai-advice-meta";

    const language =
        String(
            advice?.language
            || "unknown"
        ).toUpperCase();

    const provider =
        String(
            advice?.provider
            || "unknown provider"
        );

    const model =
        String(
            advice?.model_name
            || "unknown model"
        );

    const createdAt =
        formatHistoryDate(
            advice?.created_at
        );

    meta.textContent =
        (
            `${language} · ${provider}`
            + ` · ${model}`
            + ` · ${createdAt}`
        );

    const summary = advice?.summary;
    const riskLabels = {LOW: "🟢 Low Risk", MEDIUM: "🟡 Medium Risk", HIGH: "🔴 High Risk"};
    if (summary && riskLabels[summary.risk_level]) {
        const risk = document.createElement("div");
        risk.className = `drai-risk drai-risk-${summary.risk_level.toLowerCase()}`;
        risk.textContent = riskLabels[summary.risk_level];
        const conclusion = document.createElement("p");
        conclusion.textContent = summary.conclusion;
        const recommendation = document.createElement("p");
        recommendation.textContent = summary.recommendation;
        card.append(risk, conclusion, recommendation);
    } else {
        const legacy = document.createElement("p");
        legacy.textContent = advice?.language === "vi"
            ? "Tư vấn trước đây chưa có mức cảnh báo. Xem nội dung đầy đủ bên dưới."
            : "This previous advice has no warning level. View the full text below.";
        card.appendChild(legacy);
    }
    const details = document.createElement("details");
    const toggle = document.createElement("summary");
    const vietnamese = advice?.language === "vi";
    toggle.textContent = vietnamese ? "Hiển thị thêm" : "Show more";
    details.addEventListener("toggle", () => {
        toggle.textContent = vietnamese
            ? (details.open ? "Thu gọn" : "Hiển thị thêm")
            : (details.open ? "Show less" : "Show more");
    });
    const text = document.createElement("div");
    text.className = "drai-advice-text";
    text.textContent = String(advice?.advice_text || "No advice text returned.");
    details.append(toggle, meta, text);
    card.appendChild(details);

    return card;
}


function renderDrAIAdviceHistory(
    container,
    advices
) {
    container.replaceChildren();

    if (
        !Array.isArray(advices)
    ) {
        throw new Error(
            "Unexpected Dr.AI history "
            + "response."
        );
    }

    if (advices.length === 0) {
        const empty =
            document.createElement(
                "p"
            );

        empty.className =
            "drai-history-empty";

        empty.textContent =
            "No Dr.AI advice generated yet.";

        container.appendChild(
            empty
        );

        return;
    }

    const advice = advices[0];

    if (advice) {
        container.appendChild(
            createDrAIAdviceCard(
                advice
            )
        );
    }
}


async function fetchDrAIAdviceHistory(
    analysisId,
    token
) {
    const response =
        await fetch(
            (
                "/api/v1/analyses/"
                + encodeURIComponent(
                    analysisId
                )
                + "/medical-advices"
            ),
            {
                method: "GET",

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
            getDrAIErrorMessage(
                response,
                payload
            )
        );
    }

    if (!Array.isArray(payload)) {
        throw new Error(
            "Unexpected Dr.AI history "
            + "response."
        );
    }

    return payload;
}


// Serialize automatic batch advice requests to avoid a burst of provider calls.
let drAIInitialQueue = Promise.resolve();

function createDrAIControls(analysisLike, {autoGenerate = false} = {}) {
    const analysisId = getReportAnalysisId(analysisLike);
    if (analysisId === null || getReportAnalysisStatus(analysisLike) !== "COMPLETED") {
        return null;
    }
    const container = document.createElement("section");
    container.className = "report-actions drai-actions";
    container.dataset.analysisId = String(analysisId);
    const title = document.createElement("strong");
    title.className = "report-actions-title";
    title.textContent = "Dr.AI";
    const controls = document.createElement("div");
    controls.className = "report-actions-row drai-actions-row";
    const languageSelect = document.createElement("select");
    languageSelect.className = "report-language-select drai-language-select";
    languageSelect.setAttribute("aria-label", "Dr.AI language");
    for (const [value, label] of [["vi", "Vietnamese"], ["en", "English"]]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        languageSelect.appendChild(option);
    }
    languageSelect.value = "vi";
    const previewButton = document.createElement("button");
    previewButton.type = "button";
    previewButton.className = "secondary drai-preview-button";
    previewButton.textContent = "Preview PDF";
    previewButton.title = "Preview the latest Dr.AI advice as PDF";

    const downloadButton = document.createElement("button");
    downloadButton.type = "button";
    downloadButton.className = "secondary drai-download-button";
    downloadButton.textContent = "Download PDF";
    downloadButton.title = "Download the latest Dr.AI advice as PDF";
    const statusText = document.createElement("p");
    statusText.className = "report-action-status drai-status";
    statusText.setAttribute("aria-live", "polite");
    const disclaimer = document.createElement("p");
    disclaimer.className = "drai-disclaimer";
    disclaimer.textContent = "AI-generated explanation only. It is not a confirmed medical diagnosis.";
    const historyTitle = document.createElement("strong");
    historyTitle.className = "drai-history-title";
    historyTitle.textContent = "Previous Dr.AI advice";
    const historyContainer = document.createElement("div");
    historyContainer.className = "drai-history";
    historyContainer.setAttribute("aria-live", "polite");
    historyContainer.textContent = "Loading Dr.AI advice...";
    controls.append(
        languageSelect,
        previewButton,
        downloadButton
    );
    container.append(title, controls, statusText, disclaimer, historyTitle, historyContainer);

    const ownerToken = getReportAccessToken();
    let advices = [];
    let busy = true;
    function selectedAdvice() {
        return advices.find(advice => advice.language === languageSelect.value && advice.advice_text);
    }
    function setBusy(value) {
        busy = value;
        languageSelect.disabled = value;
        previewButton.disabled =
            value || !selectedAdvice();
        downloadButton.disabled =
            value || !selectedAdvice();
    }
    function checkSession() {
        if (!ownerToken || ownerToken !== getReportAccessToken()) {
            advices = [];
            historyContainer.textContent = "Please sign in and reload the analyses.";
            previewButton.disabled = true;
            downloadButton.disabled = true;
            throw new Error("Session changed. Please reload the analyses.");
        }
    }
    function showAdvices(records) {
        checkSession();
        advices = records.filter(advice => Number(advice.analysis_id) === Number(analysisId))
            .sort((a, b) => Number(b.id) - Number(a.id))
            .slice(0, 1);
        renderDrAIAdviceHistory(historyContainer, advices);
        setBusy(busy);
    }
    async function generate() {
        checkSession();
        statusText.textContent = "Generating Dr.AI advice...";
        const response = await fetch("/api/v1/medical-advices", {
            method: "POST",
            headers: {Authorization: `Bearer ${ownerToken}`, "Content-Type": "application/json"},
            body: JSON.stringify({analysis_id: analysisId, language: languageSelect.value}),
        });
        const payload = await parseResponse(response);
        checkSession();
        if (!response.ok) throw new Error(getDrAIErrorMessage(response, payload));
        if (!payload || !Number.isInteger(Number(payload.id)) ||
            Number(payload.analysis_id) !== Number(analysisId) || !payload.advice_text) {
            throw new Error("The Dr.AI API returned an invalid advice.");
        }
        showAdvices([payload, ...advices.filter(advice => advice.id !== payload.id)]);
        statusText.textContent = "Dr.AI advice generated. Download is ready.";
    }
    languageSelect.addEventListener("change", () => {
        setBusy(busy);
        statusText.textContent = selectedAdvice()
            ? "Download is ready for the selected language."
            : "No Dr.AI advice is available for this analysis.";
    });
    previewButton.addEventListener("click", async () => {
        if (busy) return;

        const advice = selectedAdvice();
        if (!advice) return;

        // Open immediately to avoid popup blocking
        // after the asynchronous PDF request.
        const previewWindow = window.open(
            "",
            "_blank"
        );

        if (!previewWindow) {
            statusText.textContent =
                "Dr.AI PDF preview failed: "
                + "the browser blocked the preview tab.";
            return;
        }

        previewWindow.document.title =
            "Dr.AI PDF Preview";

        previewWindow.document.body.textContent =
            "Loading Dr.AI PDF preview...";

        setBusy(true);

        try {
            checkSession();

            statusText.textContent =
                "Preparing Dr.AI PDF preview...";

            const response = await fetch(
                `/api/v1/medical-advices/${advice.id}/download`,
                {
                    method: "GET",
                    headers: {
                        Authorization:
                            `Bearer ${ownerToken}`,
                    },
                    cache: "no-store",
                }
            );

            checkSession();

            if (!response.ok) {
                const payload =
                    await parseResponse(response);

                throw new Error(
                    getDrAIErrorMessage(
                        response,
                        payload
                    )
                );
            }

            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";

            if (
                !contentType
                    .toLowerCase()
                    .startsWith(
                        "application/pdf"
                    )
            ) {
                throw new Error(
                    "Dr.AI preview returned an unexpected file type."
                );
            }

            const blob =
                await response.blob();

            const url =
                URL.createObjectURL(blob);

            previewWindow.location.href =
                url;

            setTimeout(
                () => URL.revokeObjectURL(url),
                60000
            );

            statusText.textContent =
                "Dr.AI PDF preview opened.";

        } catch (error) {
            if (
                previewWindow
                && !previewWindow.closed
            ) {
                previewWindow.close();
            }

            statusText.textContent =
                "Dr.AI PDF preview failed: "
                + error.message;

        } finally {
            setBusy(false);
        }
    });


    downloadButton.addEventListener("click", async () => {
        if (busy) return;

        const advice = selectedAdvice();
        if (!advice) return;

        setBusy(true);

        try {
            checkSession();

            statusText.textContent =
                "Downloading Dr.AI PDF...";

            const response = await fetch(
                `/api/v1/medical-advices/${advice.id}/download`,
                {
                    method: "GET",
                    headers: {
                        Authorization:
                            `Bearer ${ownerToken}`,
                    },
                    cache: "no-store",
                }
            );

            checkSession();

            if (!response.ok) {
                const payload =
                    await parseResponse(response);

                throw new Error(
                    getDrAIErrorMessage(
                        response,
                        payload
                    )
                );
            }

            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";

            if (
                !contentType
                    .toLowerCase()
                    .startsWith(
                        "application/pdf"
                    )
            ) {
                throw new Error(
                    "Dr.AI download returned an unexpected file type."
                );
            }

            const blob =
                await response.blob();

            const url =
                URL.createObjectURL(blob);

            const link =
                document.createElement("a");

            link.href = url;

            link.download =
                `DrAI-analysis-${analysisId}-advice-${advice.id}-${advice.language}.pdf`;

            document.body.appendChild(
                link
            );

            link.click();
            link.remove();

            setTimeout(
                () => URL.revokeObjectURL(url),
                1000
            );

            statusText.textContent =
                "Dr.AI report downloaded (.pdf).";

        } catch (error) {
            statusText.textContent =
                "Dr.AI PDF download failed: "
                + error.message;

        } finally {
            setBusy(false);
        }
    });
    setBusy(true);
    statusText.textContent = "Loading Dr.AI advice...";
    drAIInitialQueue = drAIInitialQueue.then(async () => {
        try {
            checkSession();
            showAdvices(await fetchDrAIAdviceHistory(analysisId, ownerToken));
            if (autoGenerate && !advices.length) {
                await generate();
            } else {
                statusText.textContent = advices.length
                    ? "Dr.AI advice loaded."
                    : "No Dr.AI advice is available.";
            }
        } catch (error) {
            statusText.textContent = "Dr.AI failed: " + error.message;
            if (!advices.length) {
                historyContainer.textContent = "No Dr.AI advice is available. " + error.message;
            }
        } finally {
            setBusy(false);
        }
    });
    return container;
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
    data
) {
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


    const probabilityEntries =
        normalizeProbabilityEntries(
            analysis.probabilities
        );

    if (
        probabilityEntries.length
        > 0
    ) {
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


        section.appendChild(
            createProbabilityVisualizationSwitcher(
                probabilityEntries,
                analysis.predicted_class
            )
        );


        card.appendChild(
            section
        );
    }

    const reportControls =
        createReportControls(
            analysis
        );

    if (reportControls !== null) {
        card.appendChild(
            reportControls
        );
    }

    const drAIControls =
        createDrAIControls(
            analysis
        );

    if (drAIControls !== null) {
        card.appendChild(
            drAIControls
        );
    }

    return card;
}


async function fetchHistoryImageBlob(
    analysisId,
    thumbnail
) {
    const token =
        getReportAccessToken();

    if (!token) {
        throw new Error(
            "Please sign in first."
        );
    }


    const suffix =
        (
            thumbnail
                ? "?thumbnail=true"
                : ""
        );


    const response =
        await fetch(
            (
                "/api/v1/analyses/"
                + encodeURIComponent(
                    analysisId
                )
                + "/image"
                + suffix
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


    const contentType =
        (
            response.headers.get(
                "content-type"
            )
            || ""
        );


    if (
        !contentType.startsWith(
            "image/"
        )
    ) {
        throw new Error(
            "The server did not return an image."
        );
    }


    return response.blob();
}


function createHistoryImagePreview(
    analysis
) {
    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "history-image-preview";


    const button =
        document.createElement(
            "button"
        );

    button.type =
        "button";

    button.className =
        "history-image-preview-button";

    button.setAttribute(
        "aria-label",
        (
            "Preview X-ray "
            + (
                analysis.original_filename
                || ""
            )
        ).trim()
    );


    const image =
        document.createElement(
            "img"
        );

    image.className =
        "history-thumbnail";

    image.alt =
        (
            "X-ray preview of "
            + (
                analysis.original_filename
                || "analysis image"
            )
        );

    image.hidden =
        true;


    const placeholder =
        document.createElement(
            "div"
        );

    placeholder.className =
        "history-image-placeholder";

    placeholder.textContent =
        "Loading X-ray...";


    const caption =
        document.createElement(
            "div"
        );

    caption.className =
        "history-image-caption";

    caption.textContent =
        "Click image to Preview";


    button.append(
        image,
        placeholder
    );

    wrapper.append(
        button,
        caption
    );


    async function loadThumbnail() {
        if (
            !Number.isInteger(
                Number(
                    analysis.id
                )
            )
        ) {
            placeholder.textContent =
                "Preview unavailable";

            button.disabled =
                true;

            return;
        }


        try {
            const blob =
                await fetchHistoryImageBlob(
                    analysis.id,
                    true
                );


            const objectUrl =
                URL.createObjectURL(
                    blob
                );


            image.onload =
                () => {
                    URL.revokeObjectURL(
                        objectUrl
                    );
                };


            image.src =
                objectUrl;

            image.hidden =
                false;

            placeholder.hidden =
                true;

        } catch (error) {
            placeholder.textContent =
                "Preview unavailable";

            caption.textContent =
                error.message;

            button.disabled =
                true;
        }
    }


    button.addEventListener(
        "click",
        async () => {
            const previewWindow =
                window.open(
                    "",
                    "_blank"
                );


            if (!previewWindow) {
                caption.textContent =
                    (
                        "Preview was blocked "
                        + "by the browser."
                    );

                return;
            }


            previewWindow.opener =
                null;

            previewWindow.document.title =
                (
                    analysis.original_filename
                    || "X-ray Preview"
                );

            previewWindow.document.body.textContent =
                "Loading X-ray preview...";


            button.disabled =
                true;

            caption.textContent =
                "Opening Preview...";


            try {
                const blob =
                    await fetchHistoryImageBlob(
                        analysis.id,
                        false
                    );


                const objectUrl =
                    URL.createObjectURL(
                        blob
                    );


                previewWindow.location.replace(
                    objectUrl
                );


                window.setTimeout(
                    () => {
                        URL.revokeObjectURL(
                            objectUrl
                        );
                    },
                    60000
                );


                caption.textContent =
                    "Click image to Preview";

            } catch (error) {
                previewWindow.close();

                caption.textContent =
                    (
                        "Preview failed: "
                        + error.message
                    );

            } finally {
                button.disabled =
                    false;
            }
        }
    );


    void loadThumbnail();


    return wrapper;
}


function decorateHistoryCardWithImage(
    card,
    analysis
) {
    if (
        card.querySelector(
            ".history-record-body"
        )
    ) {
        return;
    }


    const header =
        card.querySelector(
            ".history-item-header"
        );


    if (!header) {
        return;
    }


    const body =
        document.createElement(
            "div"
        );

    body.className =
        "history-record-body";


    const content =
        document.createElement(
            "div"
        );

    content.className =
        "history-record-content";


    const children =
        Array.from(
            card.children
        );


    for (
        const child
        of children
    ) {
        if (
            child !== header
        ) {
            content.appendChild(
                child
            );
        }
    }


    const preview =
        createHistoryImagePreview(
            analysis
        );


    body.append(
        preview,
        content
    );


    card.appendChild(
        body
    );
}


function renderAnalysisHistory(
    analyses,
    limit,
    offset
) {
    historyResults.replaceChildren();

    historySummary.hidden =
        true;

    historySummary.textContent =
        "";


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
            const historyCard =
                createHistoryItem(
                    analysis
                );


            const historyDetails =
                historyCard.querySelectorAll(
                    ".result-details li"
                );


            for (
                const detail
                of historyDetails
            ) {
                const label =
                    detail.querySelector(
                        "strong"
                    );

                if (
                    label
                    && label.textContent.trim()
                    === "Model:"
                ) {
                    detail.remove();
                }
            }


            decorateHistoryCardWithImage(
                historyCard,
                analysis
            );

            historyResults.appendChild(
                historyCard
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
            "Please sign in to continue.";

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
    profileFullNameInput.value =
        "";

    profileDateOfBirthInput.value =
        "";

    profileSexInput.value =
        "";

    profilePhoneInput.value =
        "";

    profileEmailInput.value =
        "";

    profileHeightInput.value =
        "";

    profileWeightInput.value =
        "";
}


function populatePatientProfile(
    profile
) {
    profileFullNameInput.value =
        profile.full_name ?? "";

    profileDateOfBirthInput.value =
        (
            profile.date_of_birth
                ? String(
                    profile.date_of_birth
                ).slice(
                    0,
                    10
                )
                : ""
        );

    profileSexInput.value =
        profile.sex ?? "";

    profilePhoneInput.value =
        profile.phone ?? "";

    profileEmailInput.value =
        profile.email ?? "";

    profileHeightInput.value =
        profile.height_cm ?? "";

    profileWeightInput.value =
        profile.weight_kg ?? "";
}


function buildPatientProfilePayload() {
    const fullName =
        profileFullNameInput
            .value
            .trim();

    const dateOfBirth =
        profileDateOfBirthInput
            .value
            .trim();

    const sex =
        profileSexInput.value;

    const phone =
        profilePhoneInput
            .value
            .trim();

    const email =
        profileEmailInput
            .value
            .trim();

    const height =
        Number.parseFloat(
            profileHeightInput.value
        );

    const weight =
        Number.parseFloat(
            profileWeightInput.value
        );


    if (!fullName) {
        throw new Error(
            "Full name is required."
        );
    }

    if (!dateOfBirth) {
        throw new Error(
            "Date of birth is required."
        );
    }

    if (!sex) {
        throw new Error(
            "Sex is required."
        );
    }

    if (!phone) {
        throw new Error(
            "Phone is required."
        );
    }

    if (!email) {
        throw new Error(
            "Email is required."
        );
    }

    if (
        !Number.isFinite(
            height
        )
    ) {
        throw new Error(
            "Height is required."
        );
    }

    if (
        !Number.isFinite(
            weight
        )
    ) {
        throw new Error(
            "Weight is required."
        );
    }


    return {
        full_name:
            fullName,

        date_of_birth:
            dateOfBirth,

        sex,

        phone,

        email,

        height_cm:
            height,

        weight_kg:
            weight,
    };
}


async function loadPatientProfile() {
    const token =
        normalizeToken(
            tokenInput.value
        );

    if (!token) {
        profileStatus.textContent =
            "Please sign in to continue.";

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
            "Please sign in to continue.";

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
function requiredMedicalHistoryText(
    input,
    maxLength,
    fieldName
) {
    const value =
        input.value.trim();

    if (!value) {
        throw new Error(
            fieldName
            + " is required."
        );
    }

    if (
        value.length
        > maxLength
    ) {
        throw new Error(
            fieldName
            + " can contain at most "
            + maxLength
            + " characters."
        );
    }

    return value;
}


function buildMedicalHistoryPayload() {
    return {
        current_complaint_hpi:
            requiredMedicalHistoryText(
                medicalHistoryCurrentComplaintInput,
                5000,
                "Current Complaint and HPI"
            ),

        past_medical_history:
            requiredMedicalHistoryText(
                medicalHistoryPastMedicalInput,
                5000,
                "Past Medical History"
            ),

        past_medication_history:
            requiredMedicalHistoryText(
                medicalHistoryPastMedicationInput,
                5000,
                "Past Medication History"
            ),

        allergy_history:
            requiredMedicalHistoryText(
                medicalHistoryAllergyInput,
                5000,
                "Allergy"
            ),

        diet:
            requiredMedicalHistoryText(
                medicalHistoryDietInput,
                2000,
                "Diet"
            ),

        appetite:
            requiredMedicalHistoryText(
                medicalHistoryAppetiteInput,
                2000,
                "Appetite"
            ),

        sleep:
            requiredMedicalHistoryText(
                medicalHistorySleepInput,
                2000,
                "Sleep"
            ),

        exercise:
            requiredMedicalHistoryText(
                medicalHistoryExerciseInput,
                2000,
                "Exercise"
            ),

        bowel_bladder:
            requiredMedicalHistoryText(
                medicalHistoryBowelBladderInput,
                2000,
                "Bowel and Bladder"
            ),

        habits:
            requiredMedicalHistoryText(
                medicalHistoryHabitsInput,
                3000,
                "Habits"
            ),

        family_history:
            requiredMedicalHistoryText(
                medicalHistoryFamilyInput,
                5000,
                "Family History"
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
        new Date(
            value
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


function clearMedicalHistoryEditor() {
    selectedMedicalHistoryId =
        null;

    medicalHistoryCurrentComplaintInput.value =
        "";

    medicalHistoryPastMedicalInput.value =
        "";

    medicalHistoryPastMedicationInput.value =
        "";

    medicalHistoryAllergyInput.value =
        "";

    medicalHistoryDietInput.value =
        "";

    medicalHistoryAppetiteInput.value =
        "";

    medicalHistorySleepInput.value =
        "";

    medicalHistoryExerciseInput.value =
        "";

    medicalHistoryBowelBladderInput.value =
        "";

    medicalHistoryHabitsInput.value =
        "";

    medicalHistoryFamilyInput.value =
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

    medicalHistoryCurrentComplaintInput.value =
        history.current_complaint_hpi
        ?? "";

    medicalHistoryPastMedicalInput.value =
        history.past_medical_history
        ?? "";

    medicalHistoryPastMedicationInput.value =
        history.past_medication_history
        ?? "";

    medicalHistoryAllergyInput.value =
        history.allergy_history
        ?? "";

    medicalHistoryDietInput.value =
        history.diet
        ?? "";

    medicalHistoryAppetiteInput.value =
        history.appetite
        ?? "";

    medicalHistorySleepInput.value =
        history.sleep
        ?? "";

    medicalHistoryExerciseInput.value =
        history.exercise
        ?? "";

    medicalHistoryBowelBladderInput.value =
        history.bowel_bladder
        ?? "";

    medicalHistoryHabitsInput.value =
        history.habits
        ?? "";

    medicalHistoryFamilyInput.value =
        history.family_history
        ?? "";

    medicalHistoryEditorTitle.textContent =
        (
            "Edit Medical History #"
            + history.id
        );

    saveMedicalHistoryButton.textContent =
        "Update History";
}


function createMedicalHistoryDetail(
    label,
    value
) {
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

    const text =
        document.createElement(
            "span"
        );

    text.textContent =
        (
            value
            || "N/A"
        );

    row.append(
        strong,
        text
    );

    return row;
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
            "h4"
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


    const rows = [
        [
            "Current Complaint and HPI",
            history.current_complaint_hpi,
        ],
        [
            "Past Medical History",
            history.past_medical_history,
        ],
        [
            "Past Medication History",
            history.past_medication_history,
        ],
        [
            "Allergy",
            history.allergy_history,
        ],
        [
            "Diet",
            history.diet,
        ],
        [
            "Appetite",
            history.appetite,
        ],
        [
            "Sleep",
            history.sleep,
        ],
        [
            "Exercise",
            history.exercise,
        ],
        [
            "Bowel and Bladder",
            history.bowel_bladder,
        ],
        [
            "Habits",
            history.habits,
        ],
        [
            "Family History",
            history.family_history,
        ],
    ];


    for (
        const [
            label,
            value,
        ]
        of rows
    ) {
        details.append(
            createMedicalHistoryDetail(
                label,
                value
            )
        );
    }


    const editButton =
        document.createElement(
            "button"
        );

    editButton.type =
        "button";

    editButton.className =
        "secondary";

    editButton.textContent =
        "Edit";

    editButton.addEventListener(
        "click",
        () => {
            loadMedicalHistoryById(
                history.id
            );
        }
    );


    card.append(
        header,
        details,
        editButton
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


    if (
        histories.length === 0
    ) {
        const empty =
            document.createElement(
                "p"
            );

        empty.textContent =
            "No medical history records.";

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

    if (
        !Array.isArray(
            data
        )
    ) {
        throw new Error(
            "Medical history response "
            + "must be an array."
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
            "Please sign in first.";

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
                + histories.length
                + " record(s) returned."
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
            "Please sign in first.";

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
            "Please sign in first.";

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
                        "Content-Type":
                            "application/json",

                        Authorization:
                            `Bearer ${token}`,
                    },

                    body: JSON.stringify(
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
                    ? "Medical history updated successfully."
                    : "Medical history created successfully."
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


const adminDashboardSection = document.getElementById("admin-dashboard-section");
const adminDashboardStatus = document.getElementById("admin-dashboard-status");
const adminDashboardOverview = document.getElementById("admin-dashboard-overview");
const adminDashboardPredictions = document.getElementById("admin-dashboard-predictions");
const adminDashboardModelUsage = document.getElementById("admin-dashboard-model-usage");
let adminDashboardRequest = null;

function resetAdminDashboardView() {
    for (const container of [adminDashboardOverview, adminDashboardPredictions,
        adminDashboardModelUsage]) {
        container.replaceChildren();
    }
    adminDashboardStatus.textContent = "ADMIN dashboard has not been loaded.";
}

function getAdminDashboardTokenRole() {
    try {
        const token = normalizeToken(tokenInput.value);
        const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        const payload = JSON.parse(atob(part.padEnd(Math.ceil(part.length / 4) * 4, "=")));
        if (payload.exp && payload.exp * 1000 <= Date.now()) return null;
        return payload.role;
    } catch {
        return null;
    }
}

function initializeAdminDashboard() {
    if (adminDashboardRequest) adminDashboardRequest.abort();
    adminDashboardRequest = null;
    resetAdminDashboardView();
    /* ADMIN ROLE GATE v1 */
    const tokenRole = getAdminDashboardTokenRole();
    const isAdmin = tokenRole === "ADMIN";

    adminDashboardSection.hidden = !isAdmin;

    if (isAdmin) {
        return loadAdminDashboard();
    }
}

function appendAdminDashboardText(parent, tag, value, className = "") {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = String(value ?? "—");
    parent.appendChild(element);
    return element;
}

function renderAdminDashboardBars(container, items, label, countKey) {
    if (!items.length) {
        appendAdminDashboardText(container, "p", "No data available.");
        return;
    }
    const maximum = Math.max(1, ...items.map(item => Number(item[countKey]) || 0));
    for (const item of items) {
        const row = appendAdminDashboardText(container, "div", "", "admin-dashboard-bar-item");
        const count = Number(item[countKey]) || 0;
        appendAdminDashboardText(row, "div", `${label(item)}: ${count}`, "admin-dashboard-bar-header");
        const track = appendAdminDashboardText(row, "div", "", "admin-dashboard-bar-track");
        const fill = appendAdminDashboardText(track, "div", "", "admin-dashboard-bar-fill");
        fill.style.width = `${Math.max(0, Math.min(100, count / maximum * 100))}%`;
    }
}

function renderAdminDashboard(data) {
    resetAdminDashboardView();
    const labels = {
        total_users: "Total users", active_users: "Active users",
        total_patients: "Total patients", total_analyses: "Total analyses",
    };
    for (const [key, label] of Object.entries(labels)) {
        const card = appendAdminDashboardText(adminDashboardOverview, "div", "", "admin-dashboard-metric");
        appendAdminDashboardText(card, "span", label);
        appendAdminDashboardText(card, "strong", data.overview[key]);
    }
    renderAdminDashboardBars(adminDashboardPredictions, data.prediction_distribution,
        item => item.class_name, "count");
    renderAdminDashboardBars(adminDashboardModelUsage, data.model_usage,
        item => `${item.display_name} (${item.version})`, "analysis_count");
}

async function loadAdminDashboard() {
    if (adminDashboardRequest) return;
    const token = normalizeToken(tokenInput.value);
    const tokenRole = getAdminDashboardTokenRole();
    if (
        !token
        || tokenRole !== "ADMIN"
    ) {
        resetAdminDashboardView();
        adminDashboardSection.hidden = true;
        return;
    }
    const request = new AbortController();
    adminDashboardRequest = request;
    adminDashboardStatus.textContent = "Loading ADMIN dashboard...";
    try {
        const options = {
            headers: { Authorization: `Bearer ${token}` }, signal: request.signal,
            cache: "no-store",
        };
        let response = await fetch("/api/v1/admin/dashboard/summary", options);
        // A running backend may predate the summary route. Only ADMIN may use
        // the original dashboard endpoint, which also includes patient records.
        if (response.status === 404 && tokenRole === "ADMIN"
            && request === adminDashboardRequest
            && normalizeToken(tokenInput.value) === token) {
            response = await fetch("/api/v1/admin/dashboard?recent_limit=1", options);
        }
        const data = await parseResponse(response);
        if (request !== adminDashboardRequest || normalizeToken(tokenInput.value) !== token) return;
        if (!response.ok) {
            throw new Error(response.status === 404 ? "Dashboard API is unavailable. Please restart the backend to load the update."
                : response.status === 401 ? "Session expired. Please sign in again."
                : response.status === 403 ? "Access denied. Please sign in again." : getErrorMessage(data));
        }
        if (!data || !data.overview || !Array.isArray(data.prediction_distribution)
            || !Array.isArray(data.model_usage)) {
            throw new Error("Invalid dashboard response.");
        }
        renderAdminDashboard(data);
        adminDashboardStatus.textContent = "ADMIN dashboard loaded successfully.";
    } catch (error) {
        if (request === adminDashboardRequest && error.name !== "AbortError") {
            resetAdminDashboardView();
            adminDashboardStatus.textContent = `Unable to load dashboard: ${error.message}`;
        }
    } finally {
        if (request === adminDashboardRequest) {
            adminDashboardRequest = null;
        }
    }
}

window.addEventListener("lungxray:auth-user", initializeAdminDashboard);
window.addEventListener("lungxray:auth-guest", initializeAdminDashboard);
tokenInput.addEventListener("input", initializeAdminDashboard);
tokenInput.addEventListener("change", initializeAdminDashboard);

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
            "Please sign in with a USER account.";

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
        console.error(
            "Batch analysis failed:",
            error
        );

        resultSection.hidden =
            false;

        batchSummary.replaceChildren();
        results.replaceChildren();


        const errorBox =
            document.createElement(
                "div"
            );

        errorBox.className =
            "request-status";

        errorBox.textContent =
            (
                "Batch analysis failed: "
                + error.message
            );

        results.appendChild(
            errorBox
        );

        requestStatus.textContent =
            (
                "Request failed: "
                + error.message
            );

    } finally {
        setLoading(false);
    }
}


// M15 Result Filter Controls

for (
    const button
    of filterButtons
) {
    button.addEventListener(
        "click",
        () => {
            const filter =
                button.dataset.filter;

            const allowedFilters = [
                "ALL",
                "COMPLETED",
                "REJECTED",
                "FAILED",
            ];

            if (
                !allowedFilters.includes(
                    filter
                )
            ) {
                return;
            }

            applyResultFilter(
                filter
            );
        }
    );
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

initializeAdminDashboard();

renderSelectedFiles();
