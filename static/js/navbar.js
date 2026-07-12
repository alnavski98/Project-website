document.addEventListener("DOMContentLoaded", () => {
    const toggleButton = document.querySelector(".navbar__toggle");
    const menu = document.querySelector(".navbar__menu");

    if (!toggleButton || !menu) {
        return;
    }

    function setMenuState(isOpen) {
        menu.classList.toggle("is-open", isOpen);
        toggleButton.classList.toggle("is-open", isOpen);

        toggleButton.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

        toggleButton.setAttribute(
            "aria-label",
            isOpen
                ? "Close navigation menu"
                : "Open navigation menu"
        );
    }

    toggleButton.addEventListener("click", () => {
        const isOpen =
            toggleButton.getAttribute("aria-expanded") === "true";

        setMenuState(!isOpen);
    });

    menu.addEventListener("click", (event) => {
        if (event.target.closest("a")) {
            setMenuState(false);
        }
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 700) {
            setMenuState(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setMenuState(false);
        }
    });
});