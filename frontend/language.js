"use strict";

(() => {

    const STORAGE_KEY =
        "lungxray.ui.language";

    const PAIRS =
[
        [
        "Development of an AI-Based Lung Disease Detection System Using Chest X-Ray Images",
        "H\u1ec6 TH\u1ed0NG X\u00c1C \u0110\u1ecaNH B\u1ec6NH PH\u1ed4I TH\u00d4NG QUA \u1ea2NH X-RAY"
    ],
[
        "Batch Chest X-ray Analysis",
        "Ph\u00e2n t\u00edch h\u00e0ng lo\u1ea1t X-quang ng\u1ef1c"
    ],
    [
        "Sign In",
        "\u0110\u0103ng nh\u1eadp"
    ],
    [
        "Create Account",
        "T\u1ea1o t\u00e0i kho\u1ea3n"
    ],
    [
        "Sign Out",
        "\u0110\u0103ng xu\u1ea5t"
    ],
    [
        "Personal Information",
        "Th\u00f4ng tin c\u00e1 nh\u00e2n"
    ],
    [
        "Please sign in or create an account.",
        "Vui l\u00f2ng \u0111\u0103ng nh\u1eadp ho\u1eb7c t\u1ea1o t\u00e0i kho\u1ea3n."
    ],
    [
        "Enter your phone number and password.",
        "Nh\u1eadp s\u1ed1 \u0111i\u1ec7n tho\u1ea1i v\u00e0 m\u1eadt kh\u1ea9u."
    ],
    [
        "Complete all required registration information.",
        "Vui l\u00f2ng \u0111i\u1ec1n \u0111\u1ea7y \u0111\u1ee7 th\u00f4ng tin \u0111\u0103ng k\u00fd."
    ],
    [
        "Signing in...",
        "\u0110ang \u0111\u0103ng nh\u1eadp..."
    ],
    [
        "Signed in successfully.",
        "\u0110\u0103ng nh\u1eadp th\u00e0nh c\u00f4ng."
    ],
    [
        "Signed out successfully.",
        "\u0110\u0103ng xu\u1ea5t th\u00e0nh c\u00f4ng."
    ],
    [
        "Creating account...",
        "\u0110ang t\u1ea1o t\u00e0i kho\u1ea3n..."
    ],
    [
        "Account created and signed in successfully.",
        "T\u1ea1o t\u00e0i kho\u1ea3n v\u00e0 \u0111\u0103ng nh\u1eadp th\u00e0nh c\u00f4ng."
    ],
    [
        "Passwords do not match.",
        "M\u1eadt kh\u1ea9u x\u00e1c nh\u1eadn kh\u00f4ng kh\u1edbp."
    ],
    [
        "Full Name",
        "H\u1ecd v\u00e0 t\u00ean"
    ],
    [
        "Full name",
        "H\u1ecd v\u00e0 t\u00ean"
    ],
    [
        "Phone",
        "S\u1ed1 \u0111i\u1ec7n tho\u1ea1i"
    ],
    [
        "Phone Number",
        "S\u1ed1 \u0111i\u1ec7n tho\u1ea1i"
    ],
    [
        "Address",
        "\u0110\u1ecba ch\u1ec9"
    ],
    [
        "Date of Birth",
        "Ng\u00e0y sinh"
    ],
    [
        "Date of birth",
        "Ng\u00e0y sinh"
    ],
    [
        "Birth year",
        "N\u0103m sinh"
    ],
    [
        "Sex",
        "Gi\u1edbi t\u00ednh"
    ],
    [
        "Male",
        "Nam"
    ],
    [
        "Female",
        "N\u1eef"
    ],
    [
        "Other",
        "Kh\u00e1c"
    ],
    [
        "Password",
        "M\u1eadt kh\u1ea9u"
    ],
    [
        "Confirm Password",
        "X\u00e1c nh\u1eadn m\u1eadt kh\u1ea9u"
    ],
    [
        "Height",
        "Chi\u1ec1u cao"
    ],
    [
        "Weight",
        "C\u00e2n n\u1eb7ng"
    ],
    [
        "PROJECT OVERVIEW",
        "T\u1ed4NG QUAN D\u1ef0 \u00c1N"
    ],
    [
        "1. Project Title and Field",
        "1. T\u00ean \u0111\u1ec1 t\u00e0i v\u00e0 l\u0129nh v\u1ef1c"
    ],
    [
        "2. Problem Statement and Motivation",
        "2. B\u00e0i to\u00e1n v\u00e0 \u0111\u1ed9ng l\u1ef1c"
    ],
    [
        "3. Project Objectives",
        "3. M\u1ee5c ti\u00eau d\u1ef1 \u00e1n"
    ],
    [
        "4. Scope and Limitations",
        "4. Ph\u1ea1m vi v\u00e0 gi\u1edbi h\u1ea1n"
    ],
    [
        "5. Technologies and Implementation Methods",
        "5. C\u00f4ng ngh\u1ec7 v\u00e0 ph\u01b0\u01a1ng ph\u00e1p tri\u1ec3n khai"
    ],
    [
        "3. Select Images",
        "3. Ch\u1ecdn \u1ea3nh"
    ],
    [
        "4. Batch Results",
        "4. K\u1ebft qu\u1ea3 ph\u00e2n t\u00edch"
    ],
    [
        "5. Analysis History",
        "5. L\u1ecbch s\u1eed ph\u00e2n t\u00edch"
    ],
    [
        "6. Patient Profile",
        "6. H\u1ed3 s\u01a1 b\u1ec7nh nh\u00e2n"
    ],
    [
        "7. New Medical History",
        "7. B\u1ec7nh s\u1eed m\u1edbi"
    ],
    [
        "9. ADMIN Dashboard",
        "9. B\u1ea3ng \u0111i\u1ec1u khi\u1ec3n ADMIN"
    ],
    [
        "10. ADMIN Patient Search",
        "10. ADMIN T\u00ecm ki\u1ebfm b\u1ec7nh nh\u00e2n"
    ],
    [
        "Select Images",
        "Ch\u1ecdn \u1ea3nh"
    ],
    [
        "Analyze Batch",
        "Ph\u00e2n t\u00edch h\u00e0ng lo\u1ea1t"
    ],
    [
        "Clear",
        "X\u00f3a"
    ],
    [
        "Load History",
        "T\u1ea3i l\u1ecbch s\u1eed"
    ],
    [
        "Previous",
        "Tr\u01b0\u1edbc"
    ],
    [
        "Next",
        "Ti\u1ebfp"
    ],
    [
        "Edit",
        "Ch\u1ec9nh s\u1eeda"
    ],
    [
        "Save",
        "L\u01b0u"
    ],
    [
        "Cancel",
        "H\u1ee7y"
    ],
    [
        "Delete",
        "X\u00f3a"
    ],
    [
        "View",
        "Xem"
    ],
    [
        "Close",
        "\u0110\u00f3ng"
    ],
    [
        "Limit",
        "Gi\u1edbi h\u1ea1n"
    ],
    [
        "Patient Search",
        "T\u00ecm ki\u1ebfm b\u1ec7nh nh\u00e2n"
    ],
    [
        "Search Patient",
        "T\u00ecm b\u1ec7nh nh\u00e2n"
    ],
    [
        "Full name, phone number, or address",
        "H\u1ecd t\u00ean, s\u1ed1 \u0111i\u1ec7n tho\u1ea1i ho\u1eb7c \u0111\u1ecba ch\u1ec9"
    ],
    [
        "Enter a name, phone number, or address to search.",
        "Nh\u1eadp h\u1ecd t\u00ean, s\u1ed1 \u0111i\u1ec7n tho\u1ea1i ho\u1eb7c \u0111\u1ecba ch\u1ec9 \u0111\u1ec3 t\u00ecm ki\u1ebfm."
    ],
    [
        "Patient code",
        "M\u00e3 b\u1ec7nh nh\u00e2n"
    ],
    [
        "Username",
        "T\u00ean \u0111\u0103ng nh\u1eadp"
    ],
    [
        "Account status",
        "Tr\u1ea1ng th\u00e1i t\u00e0i kho\u1ea3n"
    ],
    [
        "Active",
        "\u0110ang ho\u1ea1t \u0111\u1ed9ng"
    ],
    [
        "Inactive",
        "Ng\u1eebng ho\u1ea1t \u0111\u1ed9ng"
    ],
    [
        "Patient",
        "B\u1ec7nh nh\u00e2n"
    ],
    [
        "Actions",
        "Thao t\u00e1c"
    ],
    [
        "Current Complaint / HPI",
        "L\u00fd do kh\u00e1m / B\u1ec7nh s\u1eed hi\u1ec7n t\u1ea1i"
    ],
    [
        "Current complaint / HPI",
        "L\u00fd do kh\u00e1m / B\u1ec7nh s\u1eed hi\u1ec7n t\u1ea1i"
    ],
    [
        "Past Medical History",
        "Ti\u1ec1n s\u1eed b\u1ec7nh"
    ],
    [
        "Past medical history",
        "Ti\u1ec1n s\u1eed b\u1ec7nh"
    ],
    [
        "Past Medication History",
        "Ti\u1ec1n s\u1eed d\u00f9ng thu\u1ed1c"
    ],
    [
        "Past medication history",
        "Ti\u1ec1n s\u1eed d\u00f9ng thu\u1ed1c"
    ],
    [
        "Allergy History",
        "Ti\u1ec1n s\u1eed d\u1ecb \u1ee9ng"
    ],
    [
        "Allergy history",
        "Ti\u1ec1n s\u1eed d\u1ecb \u1ee9ng"
    ],
    [
        "Diseases",
        "B\u1ec7nh l\u00fd"
    ],
    [
        "Medications",
        "Thu\u1ed1c"
    ],
    [
        "Allergies",
        "D\u1ecb \u1ee9ng"
    ],
    [
        "Smoking",
        "H\u00fat thu\u1ed1c"
    ],
    [
        "Alcohol",
        "R\u01b0\u1ee3u bia"
    ],
    [
        "Occupational Exposure",
        "Ph\u01a1i nhi\u1ec5m ngh\u1ec1 nghi\u1ec7p"
    ],
    [
        "Occupational exposure",
        "Ph\u01a1i nhi\u1ec5m ngh\u1ec1 nghi\u1ec7p"
    ],
    [
        "Diet",
        "T\u00ecnh tr\u1ea1ng \u0103n u\u1ed1ng"
    ],
    [
        "Appetite",
        "Kh\u1ea9u v\u1ecb"
    ],
    [
        "Sleep",
        "Gi\u1ea5c ng\u1ee7"
    ],
    [
        "Exercise",
        "V\u1eadn \u0111\u1ed9ng"
    ],
    [
        "Bowel / Bladder",
        "Ti\u1ec3u ti\u1ec7n v\u00e0 \u0111\u1ea1i ti\u1ec7n"
    ],
    [
        "Bowel / bladder",
        "Ti\u1ec3u ti\u1ec7n v\u00e0 \u0111\u1ea1i ti\u1ec7n"
    ],
    [
        "Habits",
        "Th\u00f3i quen"
    ],
    [
        "Family History",
        "Ti\u1ec1n s\u1eed gia \u0111\u00ecnh"
    ],
    [
        "Family history",
        "Ti\u1ec1n s\u1eed gia \u0111\u00ecnh"
    ],
    [
        "Notes",
        "Ghi ch\u00fa"
    ],
    [
        "Medical History",
        "B\u1ec7nh s\u1eed"
    ],
    [
        "New Medical History",
        "B\u1ec7nh s\u1eed m\u1edbi"
    ],
    [
        "Latest Medical History",
        "B\u1ec7nh s\u1eed g\u1ea7n nh\u1ea5t"
    ],
    [
        "Create History",
        "T\u1ea1o b\u1ec7nh s\u1eed"
    ],
    [
        "Update History",
        "C\u1eadp nh\u1eadt b\u1ec7nh s\u1eed"
    ],
    [
        "Patient Profile",
        "H\u1ed3 s\u01a1 b\u1ec7nh nh\u00e2n"
    ],
    [
        "Patient History",
        "L\u1ecbch s\u1eed b\u1ec7nh nh\u00e2n"
    ],
    [
        "Please sign in first.",
        "Vui l\u00f2ng \u0111\u0103ng nh\u1eadp tr\u01b0\u1edbc."
    ],
    [
        "Please sign in to continue.",
        "Vui l\u00f2ng \u0111\u0103ng nh\u1eadp \u0111\u1ec3 ti\u1ebfp t\u1ee5c."
    ],
    [
        "Please sign in with a USER account.",
        "Vui l\u00f2ng \u0111\u0103ng nh\u1eadp b\u1eb1ng t\u00e0i kho\u1ea3n USER."
    ],
    [
        "Please sign in with an ADMIN account.",
        "Vui l\u00f2ng \u0111\u0103ng nh\u1eadp b\u1eb1ng t\u00e0i kho\u1ea3n ADMIN."
    ],
    [
        "Select at least one image.",
        "Vui l\u00f2ng ch\u1ecdn \u00edt nh\u1ea5t m\u1ed9t \u1ea3nh."
    ],
    [
        "No images selected.",
        "Ch\u01b0a ch\u1ecdn \u1ea3nh."
    ],
    [
        "Waiting for images.",
        "\u0110ang ch\u1edd ch\u1ecdn \u1ea3nh."
    ],
    [
        "Analyzing...",
        "\u0110ang ph\u00e2n t\u00edch..."
    ],
    [
        "Uploading images and running AI analysis...",
        "\u0110ang t\u1ea3i \u1ea3nh v\u00e0 ph\u00e2n t\u00edch AI..."
    ],
    [
        "Prediction:",
        "D\u1ef1 \u0111o\u00e1n:"
    ],
    [
        "Prediction",
        "D\u1ef1 \u0111o\u00e1n"
    ],
    [
        "Confidence",
        "\u0110\u1ed9 tin c\u1eady"
    ],
    [
        "Class probabilities",
        "X\u00e1c su\u1ea5t theo l\u1edbp"
    ],
    [
        "Class",
        "L\u1edbp"
    ],
    [
        "Probability",
        "X\u00e1c su\u1ea5t"
    ],
    [
        "Result",
        "K\u1ebft qu\u1ea3"
    ],
    [
        "Predicted",
        "\u0110\u01b0\u1ee3c d\u1ef1 \u0111o\u00e1n"
    ],
    [
        "Total",
        "T\u1ed5ng"
    ],
    [
        "Completed",
        "Ho\u00e0n t\u1ea5t"
    ],
    [
        "Rejected",
        "B\u1ecb t\u1eeb ch\u1ed1i"
    ],
    [
        "Failed",
        "Th\u1ea5t b\u1ea1i"
    ],
    [
        "Status",
        "Tr\u1ea1ng th\u00e1i"
    ],
    [
        "Date",
        "Ng\u00e0y"
    ],
    [
        "Filename",
        "T\u00ean t\u1ec7p"
    ],
    [
        "Original file",
        "T\u1ec7p g\u1ed1c"
    ],
    [
        "Input source",
        "Ngu\u1ed3n \u0111\u1ea7u v\u00e0o"
    ],
    [
        "PDF Report",
        "B\u00e1o c\u00e1o PDF"
    ],
    [
        "Report language",
        "Ng\u00f4n ng\u1eef b\u00e1o c\u00e1o"
    ],
    [
        "Vietnamese",
        "Ti\u1ebfng Vi\u1ec7t"
    ],
    [
        "English",
        "Ti\u1ebfng Anh"
    ],
    [
        "Preview",
        "Xem tr\u01b0\u1edbc"
    ],
    [
        "Download",
        "T\u1ea3i xu\u1ed1ng"
    ],
    [
        "Preview PDF",
        "Xem tr\u01b0\u1edbc PDF"
    ],
    [
        "Download PDF",
        "T\u1ea3i PDF"
    ],
    [
        "Previous Dr.AI advice",
        "T\u01b0 v\u1ea5n Dr.AI tr\u01b0\u1edbc \u0111\u00f3"
    ],
    [
        "Dr.AI language",
        "Ng\u00f4n ng\u1eef Dr.AI"
    ],
    [
        "Show more",
        "Hi\u1ec3n th\u1ecb th\u00eam"
    ],
    [
        "Show less",
        "Thu g\u1ecdn"
    ],
    [
        "AI-generated explanation only. It is not a confirmed medical diagnosis.",
        "N\u1ed9i dung do AI t\u1ea1o ch\u1ec9 mang t\u00ednh tham kh\u1ea3o, kh\u00f4ng ph\u1ea3i ch\u1ea9n \u0111o\u00e1n y khoa \u0111\u00e3 \u0111\u01b0\u1ee3c x\u00e1c nh\u1eadn."
    ],
    [
        "ADMIN dashboard has not been loaded.",
        "B\u1ea3ng \u0111i\u1ec1u khi\u1ec3n ADMIN ch\u01b0a \u0111\u01b0\u1ee3c t\u1ea3i."
    ],
    [
        "Overview",
        "T\u1ed5ng quan"
    ],
    [
        "Total users",
        "T\u1ed5ng ng\u01b0\u1eddi d\u00f9ng"
    ],
    [
        "Active users",
        "Ng\u01b0\u1eddi d\u00f9ng \u0111ang ho\u1ea1t \u0111\u1ed9ng"
    ],
    [
        "Total patients",
        "T\u1ed5ng b\u1ec7nh nh\u00e2n"
    ],
    [
        "Total analyses",
        "T\u1ed5ng l\u1ea7n ph\u00e2n t\u00edch"
    ],
    [
        "No data available.",
        "Kh\u00f4ng c\u00f3 d\u1eef li\u1ec7u."
    ],
    [
        "Request failed.",
        "Y\u00eau c\u1ea7u th\u1ea5t b\u1ea1i."
    ],
    [
        "Ready.",
        "S\u1eb5n s\u00e0ng."
    ]
];

    const enToVi =
        new Map(PAIRS);

    const viToEn =
        new Map(
            PAIRS.map(
                ([en, vi]) => [
                    vi,
                    en,
                ]
            )
        );

    let currentLanguage = "en";

    try {
        const saved =
            localStorage.getItem(
                STORAGE_KEY
            );

        if (
            saved === "en"
            || saved === "vi"
        ) {
            currentLanguage =
                saved;
        }
    }
    catch {
    }


    function normalize(value) {
        return String(value || "")
            .replace(/\s+/g, " ")
            .trim();
    }


    function translateCore(
        value,
        language
    ) {
        const normalized =
            normalize(value);

        if (!normalized) {
            return value;
        }

        const dictionary =
            language === "vi"
                ? enToVi
                : viToEn;

        if (
            dictionary.has(normalized)
        ) {
            return dictionary.get(
                normalized
            );
        }

        if (language === "vi") {

            let match =
                normalized.match(
                    /^Page (\d+) of (\d+)$/
                );

            if (match) {
                return (
                    "Trang "
                    + match[1]
                    + " / "
                    + match[2]
                );
            }

            match =
                normalized.match(
                    /^(\d+) patient account\(s\) found\.$/
                );

            if (match) {
                return (
                    "T\u00ecm th\u1ea5y "
                    + match[1]
                    + " t\u00e0i kho\u1ea3n b\u1ec7nh nh\u00e2n."
                );
            }

            match =
                normalized.match(
                    /^Medical History #(\d+)$/
                );

            if (match) {
                return (
                    "B\u1ec7nh s\u1eed #"
                    + match[1]
                );
            }
        }

        if (language === "en") {

            let match =
                normalized.match(
                    /^Trang (\d+) \/ (\d+)$/
                );

            if (match) {
                return (
                    "Page "
                    + match[1]
                    + " of "
                    + match[2]
                );
            }

            match =
                normalized.match(
                    /^T\u00ecm th\u1ea5y (\d+) t\u00e0i kho\u1ea3n b\u1ec7nh nh\u00e2n\.$/
                );

            if (match) {
                return (
                    match[1]
                    + " patient account(s) found."
                );
            }

            match =
                normalized.match(
                    /^B\u1ec7nh s\u1eed #(\d+)$/
                );

            if (match) {
                return (
                    "Medical History #"
                    + match[1]
                );
            }
        }

        return value;
    }


    function translateText(
        value,
        language
    ) {
        if (
            typeof value !== "string"
        ) {
            return value;
        }

        const match =
            value.match(
                /^(\s*)([\s\S]*?)(\s*)$/
            );

        if (!match) {
            return value;
        }

        const translated =
            translateCore(
                match[2],
                language
            );

        return (
            match[1]
            + translated
            + match[3]
        );
    }


    function shouldSkip(
        element
    ) {
        if (!element) {
            return true;
        }

        return Boolean(
            element.closest(
                "script,"
                + "style,"
                + "code,"
                + "pre,"
                + ".drai-advice-text,"
                + ".admin-analysis-advice-text,"
                + "[data-overview-language]"
            )
        );
    }


    function translateElement(
        element,
        language
    ) {
        if (
            !element
            || element.nodeType !== 1
            || shouldSkip(element)
        ) {
            return;
        }

        for (
            const attribute
            of [
                "placeholder",
                "title",
                "aria-label",
            ]
        ) {
            if (
                !element.hasAttribute(
                    attribute
                )
            ) {
                continue;
            }

            const oldValue =
                element.getAttribute(
                    attribute
                );

            const newValue =
                translateCore(
                    oldValue,
                    language
                );

            if (
                oldValue !== newValue
            ) {
                element.setAttribute(
                    attribute,
                    newValue
                );
            }
        }
    }


    function translateNode(
        node,
        language
    ) {
        if (!node) {
            return;
        }

        if (
            node.nodeType === 3
        ) {
            const parent =
                node.parentElement;

            if (
                !parent
                || shouldSkip(parent)
            ) {
                return;
            }

            const oldValue =
                node.nodeValue;

            const newValue =
                translateText(
                    oldValue,
                    language
                );

            if (
                oldValue !== newValue
            ) {
                node.nodeValue =
                    newValue;
            }

            return;
        }

        if (
            node.nodeType !== 1
            && node.nodeType !== 9
        ) {
            return;
        }

        if (
            node.nodeType === 1
        ) {
            translateElement(
                node,
                language
            );
        }

        const walker =
            document.createTreeWalker(
                node,
                NodeFilter.SHOW_ELEMENT
                | NodeFilter.SHOW_TEXT
            );

        let current =
            walker.nextNode();

        while (current) {

            if (
                current.nodeType === 3
            ) {
                const parent =
                    current.parentElement;

                if (
                    parent
                    && !shouldSkip(parent)
                ) {
                    const oldValue =
                        current.nodeValue;

                    const newValue =
                        translateText(
                            oldValue,
                            language
                        );

                    if (
                        oldValue !== newValue
                    ) {
                        current.nodeValue =
                            newValue;
                    }
                }
            }
            else {
                translateElement(
                    current,
                    language
                );
            }

            current =
                walker.nextNode();
        }
    }


    function updateSwitcher() {

        document
            .querySelectorAll(
                "[data-ui-language]"
            )
            .forEach(
                (button) => {

                    const selected =
                        button.dataset
                            .uiLanguage
                        === currentLanguage;

                    button.classList.toggle(
                        "is-active",
                        selected
                    );

                    button.setAttribute(
                        "aria-pressed",
                        selected
                            ? "true"
                            : "false"
                    );
                }
            );
    }



    function updateOverviewLanguage() {

        document
            .querySelectorAll(
                "[data-overview-language]"
            )
            .forEach(
                (section) => {

                    section.hidden =
                        section.dataset
                            .overviewLanguage
                        !== currentLanguage;
                }
            );
    }


    function setLanguage(
        language,
        persist = true
    ) {

        if (
            language !== "en"
            && language !== "vi"
        ) {
            language = "en";
        }

        currentLanguage =
            language;

        document.documentElement.lang =
            language;

        updateOverviewLanguage();

        translateNode(
            document.body,
            language
        );

        updateSwitcher();

        if (persist) {
            try {
                localStorage.setItem(
                    STORAGE_KEY,
                    language
                );
            }
            catch {
            }
        }

        window.dispatchEvent(
            new CustomEvent(
                "lungxray:language-changed",
                {
                    detail: {
                        language,
                    },
                }
            )
        );
    }


    document
        .querySelectorAll(
            "[data-ui-language]"
        )
        .forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    () => {
                        setLanguage(
                            button.dataset
                                .uiLanguage
                        );
                    }
                );
            }
        );


    setLanguage(
        currentLanguage,
        false
    );


    const observer =
        new MutationObserver(
            (mutations) => {

                for (
                    const mutation
                    of mutations
                ) {

                    if (
                        mutation.type
                        === "characterData"
                    ) {
                        translateNode(
                            mutation.target,
                            currentLanguage
                        );

                        continue;
                    }

                    for (
                        const node
                        of mutation.addedNodes
                    ) {
                        translateNode(
                            node,
                            currentLanguage
                        );
                    }
                }
            }
        );


    observer.observe(
        document.body,
        {
            childList: true,
            characterData: true,
            subtree: true,
        }
    );


    window.LungXrayLanguage = {
        getLanguage() {
            return currentLanguage;
        },

        setLanguage,

        translate(value) {
            return translateCore(
                value,
                currentLanguage
            );
        },
    };

})();
