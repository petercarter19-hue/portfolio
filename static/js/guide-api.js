/* Same-origin, owner-derived reads. No owner selector or write is accepted here. */
(function (global) {
    'use strict';
    function unavailable() {
        var error = new Error('The Guide is unavailable right now.');
        error.code = 'guide_unavailable'; return error;
    }
    function create(options) {
        var fetcher = (options && options.fetch) || global.fetch.bind(global);
        var generation = 0;
        async function readWorkingSet(signal) {
            try {
                var request = {method: 'GET', credentials: 'same-origin', cache: 'no-store', redirect: 'error',
                    headers: {'Accept': 'application/json'}};
                if (signal) request.signal = signal;
                var response = await fetcher('/api/resume-intake/me/guide/working-set', request);
                if (!response.ok) throw unavailable();
                var payload = await response.json(), state = global.PeerSlateGuideState.create();
                if (!state.accept(payload)) throw unavailable();
                return state.data();
            } catch (_) { throw unavailable(); }
        }
        return Object.freeze({
            readWorkingSet: readWorkingSet,
            refresh: async function (state, signal) {
                var own = ++generation;
                try {
                    var payload = await readWorkingSet(signal);
                    if (own !== generation) return false;
                    return state.accept(payload);
                } catch (_) {
                    if (own === generation) state.fail();
                    return false;
                }
            },
            invalidate: function () { generation += 1; }
        });
    }
    global.PeerSlateGuideApi = Object.freeze({create: create});
})(window);
