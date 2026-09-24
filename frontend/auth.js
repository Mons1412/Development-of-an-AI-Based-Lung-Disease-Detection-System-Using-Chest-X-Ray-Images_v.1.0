(() => {
    "use strict";


    const STORAGE_KEY =
        "lungxray.auth.access_token";


    function requireElement(id) {
        const element =
            document.getElementById(
                id
            );

        if (!element) {
            throw new Error(
                `Missing required element: #${id}`
            );
        }

        return element;
    }


    const modal =
        requireElement(
            "auth-section"
        );

    const modalDialog =
        modal.querySelector(
            ".auth-modal"
        );

    if (!modalDialog) {
        throw new Error(
            "Missing required element: .auth-modal"
        );
    }


    const openLoginButton =
        requireElement(
            "open-login-button"
        );

    const openRegisterButton =
        requireElement(
            "open-register-button"
        );

    const closeAuthButton =
        requireElement(
            "close-auth-button"
        );

    const switchLoginButton =
        requireElement(
            "switch-login-button"
        );

    const switchRegisterButton =
        requireElement(
            "switch-register-button"
        );

    const dialogTitle =
        requireElement(
            "auth-dialog-title"
        );

    const loginForm =
        requireElement(
            "login-form"
        );

    const registerForm =
        requireElement(
            "register-form"
        );

    const loginPhone =
        requireElement(
            "login-phone"
        );

    const loginPassword =
        requireElement(
            "login-password"
        );

    const registerFullName =
        requireElement(
            "register-full-name"
        );

    const registerPassword =
        requireElement(
            "register-password"
        );

    const registerConfirmPassword =
        requireElement(
            "register-confirm-password"
        );

    const loginSubmitButton =
        requireElement(
            "login-submit-button"
        );

    const registerSubmitButton =
        requireElement(
            "register-submit-button"
        );

    const authStatus =
        requireElement(
            "auth-status"
        );

    const tokenInput =
        requireElement(
            "token-input"
        );

    const guestHeader =
        requireElement(
            "auth-header-guest"
        );

    const userHeader =
        requireElement(
            "auth-header-user"
        );

    const headerUserName =
        requireElement(
            "header-user-name"
        );

    const headerUserRole =
        requireElement(
            "header-user-role"
        );

    const logoutButton =
        requireElement(
            "logout-button"
        );

    const adminSection =
        document.getElementById(
            "admin-search-section"
        );


    function normalizeToken(
        rawToken
    ) {
        const token =
            String(
                rawToken || ""
            ).trim();

        if (
            token
                .toLowerCase()
                .startsWith(
                    "bearer "
                )
        ) {
            return token
                .slice(7)
                .trim();
        }

        return token;
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
                detail: text,
            };
        }
    }


    function getErrorMessage(
        payload
    ) {
        if (
            payload
            && typeof payload.detail
                === "string"
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
                        const location =
                            Array.isArray(
                                item.loc
                            )
                                ? item.loc
                                    .slice(1)
                                    .join(".")
                                : "";

                        const message =
                            item.msg
                            || "Validation error";

                        return location
                            ? `${location}: ${message}`
                            : message;
                    }
                )
                .join("; ");
        }

        return "Request failed.";
    }


    function setStatus(
        message
    ) {
        authStatus.textContent =
            message;
    }


    function getToken() {
        return normalizeToken(
            tokenInput.value
            || sessionStorage.getItem(
                STORAGE_KEY
            )
            || ""
        );
    }


    function saveToken(
        token
    ) {
        const normalized =
            normalizeToken(
                token
            );

        if (!normalized) {
            throw new Error(
                "The server did not return "
                + "a valid login session."
            );
        }

        tokenInput.value =
            normalized;

        sessionStorage.setItem(
            STORAGE_KEY,
            normalized
        );
    }


    function clearToken() {
        tokenInput.value = "";

        sessionStorage.removeItem(
            STORAGE_KEY
        );
    }


    function renderGuest() {
        guestHeader.hidden =
            false;

        userHeader.hidden =
            true;

        headerUserName.textContent =
            "User";

        headerUserRole.textContent =
            "";

        if (adminSection) {
            adminSection.hidden =
                true;
        }


        window.dispatchEvent(
            new CustomEvent(
                "lungxray:auth-guest"
            )
        );
}


    async function loadPatientHeaderName(
        user
    ) {
        if (
            !user
            || user.role !== "USER"
        ) {
            return;
        }

        const token =
            getToken();

        if (!token) {
            return;
        }

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

            if (!response.ok) {
                return;
            }

            const profile =
                await parseResponse(
                    response
                );

            const fullName =
                String(
                    profile.full_name
                    || ""
                ).trim();

            if (fullName) {
                headerUserName.textContent =
                    fullName;
            }

        } catch {
            // Keep the fallback account label.
        }
    }


    function renderUser(
        user
    ) {
        guestHeader.hidden =
            true;

        userHeader.hidden =
            false;

        if (
            user.role === "USER"
        ) {
            headerUserName.textContent =
                "Patient";

            void loadPatientHeaderName(
                user
            );
        }
        else {
            headerUserName.textContent =
                (
                    user.username
                    || "User"
                );
        }


        headerUserRole.textContent =
            user.role;

        if (adminSection) {
            adminSection.hidden =
                user.role !== "ADMIN";
        }


        window.dispatchEvent(
            new CustomEvent(
                "lungxray:auth-user",
                {
                    detail: {
                        user,
                    },
                }
            )
        );
}


    function showLogin() {
        loginForm.hidden =
            false;

        registerForm.hidden =
            true;

        modalDialog.classList.remove(
            "auth-modal-wide"
        );

        dialogTitle.textContent =
            "Sign In";

        switchLoginButton.disabled =
            true;

        switchRegisterButton.disabled =
            false;

        setStatus(
            "Enter your phone number "
            + "and password."
        );

        queueMicrotask(
            () => {
                loginPhone.focus();
            }
        );
    }


    function showRegister() {
        loginForm.hidden =
            true;

        registerForm.hidden =
            false;

        modalDialog.classList.add(
            "auth-modal-wide"
        );

        dialogTitle.textContent =
            "Create Account";

        switchLoginButton.disabled =
            false;

        switchRegisterButton.disabled =
            true;

        setStatus(
            "Complete all required "
            + "registration information."
        );

        queueMicrotask(
            () => {
                registerFullName.focus();
            }
        );
    }


    function openModal(
        mode
    ) {
        modal.hidden =
            false;

        if (
            mode === "register"
        ) {
            showRegister();
        }
        else {
            showLogin();
        }
    }


    function closeModal() {
        modal.hidden =
            true;

        loginPassword.value =
            "";

        registerPassword.value =
            "";

        registerConfirmPassword.value =
            "";
    }


    async function loadCurrentUser() {
        const token =
            getToken();

        if (!token) {
            renderGuest();
            return null;
        }

        const response =
            await fetch(
                "/api/v1/users/me",
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
            clearToken();
            renderGuest();

            throw new Error(
                getErrorMessage(
                    payload
                )
            );
        }

        renderUser(
            payload
        );

        return payload;
    }


    async function login(
        identifier,
        password
    ) {
        const formData =
            new URLSearchParams();

        formData.set(
            "username",
            identifier
        );

        formData.set(
            "password",
            password
        );

        const response =
            await fetch(
                "/api/v1/auth/login",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            (
                                "application/"
                                + "x-www-form-urlencoded"
                            ),
                    },

                    body: formData,
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

        saveToken(
            payload.access_token
        );

        return loadCurrentUser();
    }


    async function register(
        payload
    ) {
        const response =
            await fetch(
                "/api/v1/auth/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify(
                        payload
                    ),
                }
            );

        const responsePayload =
            await parseResponse(
                response
            );

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    responsePayload
                )
            );
        }

        return responsePayload;
    }


    openLoginButton.addEventListener(
        "click",
        () => {
            openModal(
                "login"
            );
        }
    );


    openRegisterButton.addEventListener(
        "click",
        () => {
            openModal(
                "register"
            );
        }
    );


    closeAuthButton.addEventListener(
        "click",
        closeModal
    );


    switchLoginButton.addEventListener(
        "click",
        showLogin
    );


    switchRegisterButton.addEventListener(
        "click",
        showRegister
    );


    modal.addEventListener(
        "click",
        (event) => {
            if (
                event.target === modal
            ) {
                closeModal();
            }
        }
    );


    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape"
                && !modal.hidden
            ) {
                closeModal();
            }
        }
    );


    loginForm.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const phone =
                loginPhone
                    .value
                    .trim();

            const password =
                loginPassword.value;

            if (
                !phone
                || !password
            ) {
                setStatus(
                    "Enter your phone number "
                    + "and password."
                );

                return;
            }

            loginSubmitButton.disabled =
                true;

            setStatus(
                "Signing in..."
            );

            try {
                await login(
                    phone,
                    password
                );

                loginPassword.value =
                    "";

                setStatus(
                    "Signed in successfully."
                );

                modal.hidden =
                    true;

            } catch (error) {
                setStatus(
                    error.message
                );

            } finally {
                loginSubmitButton.disabled =
                    false;
            }
        }
    );


    registerForm.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const formData =
                new FormData(
                    registerForm
                );

            const payload =
                Object.fromEntries(
                    formData.entries()
                );

            for (
                const [
                    key,
                    value,
                ]
                of Object.entries(
                    payload
                )
            ) {
                if (
                    typeof value
                        === "string"
                    && key !== "password"
                    && key
                        !== "confirm_password"
                ) {
                    payload[key] =
                        value.trim();
                }
            }

            const diseaseText =
                payload.diseases
                || "";

            payload.diseases =
                diseaseText
                    ? diseaseText
                        .split(/[,;\n]+/)
                        .map(
                            item =>
                                item.trim()
                        )
                        .filter(Boolean)
                    : null;

            for (
                const key
                of [
                    "smoking_status",
                    "alcohol_status",
                    "occupational_exposure",
                ]
            ) {
                payload[key] =
                    payload[key]
                        ? payload[key]
                        : null;
            }

            if (
                payload.password
                !== payload.confirm_password
            ) {
                setStatus(
                    "Passwords do not match."
                );

                registerConfirmPassword.focus();

                return;
            }

            registerSubmitButton.disabled =
                true;

            setStatus(
                "Creating account..."
            );

            try {
                await register(
                    payload
                );

                await login(
                    payload.phone,
                    payload.password
                );

                registerForm.reset();

                setStatus(
                    "Account created "
                    + "and signed in successfully."
                );

                modal.hidden =
                    true;

            } catch (error) {
                setStatus(
                    error.message
                );

            } finally {
                registerSubmitButton.disabled =
                    false;
            }
        }
    );


    logoutButton.addEventListener(
        "click",
        () => {
            clearToken();

            renderGuest();

            setStatus(
                "Signed out successfully."
            );
        }
    );


    async function restoreSession() {
        const storedToken =
            normalizeToken(
                sessionStorage.getItem(
                    STORAGE_KEY
                )
                || ""
            );

        if (!storedToken) {
            renderGuest();
            return;
        }

        tokenInput.value =
            storedToken;

        try {
            await loadCurrentUser();

        } catch {
            clearToken();

            renderGuest();
        }
    }


    window.lungXrayAuth = {
        getToken,

        openLogin() {
            openModal(
                "login"
            );
        },

        openRegister() {
            openModal(
                "register"
            );
        },

        focusLogin() {
            openModal(
                "login"
            );
        },

        logout() {
            clearToken();
            renderGuest();
        },
    };


    renderGuest();

    void restoreSession();
})();
