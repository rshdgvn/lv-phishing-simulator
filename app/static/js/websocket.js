(function () {
    "use strict";

    const WS_URL =
        (location.protocol === "https:" ? "wss://" : "ws://") +
        location.host +
        "/ws/dashboard";
    const RECONNECT_BASE_MS = 1500;
    const RECONNECT_MAX_MS = 30000;

    let socket = null;
    let retryDelay = RECONNECT_BASE_MS;
    let retryTimer = null;

    function emit(name, detail) {
        window.dispatchEvent(new CustomEvent(name, { detail }));
    }

    function connect() {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            retryDelay = RECONNECT_BASE_MS;
            clearTimeout(retryTimer);
            emit("lvcc:ws-status", { online: true });
            socket.send(JSON.stringify({ action: "sync_stats" }));
        };

        socket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                emit("lvcc:ws-message", message);
            } catch (_err) {
                console.warn("Ignoring non-JSON websocket message");
            }
        };

        socket.onerror = () => {
            emit("lvcc:ws-status", { online: false });
        };

        socket.onclose = () => {
            emit("lvcc:ws-status", { online: false });
            retryTimer = setTimeout(() => {
                retryDelay = Math.min(retryDelay * 2, RECONNECT_MAX_MS);
                connect();
            }, retryDelay);
        };
    }

    connect();
})();