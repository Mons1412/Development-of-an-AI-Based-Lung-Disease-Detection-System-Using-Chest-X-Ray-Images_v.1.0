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


let activeResultFilter = "ALL";

let selectedFiles = [];

let selectionSource = "";

let ignoredFileCount = 0;

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


renderSelectedFiles();