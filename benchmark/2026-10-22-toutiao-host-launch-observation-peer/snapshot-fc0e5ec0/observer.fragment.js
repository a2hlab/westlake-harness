// Passive evidence only. This token identifies one loaded host JS instance,
// not an authenticated OS process or a human action.
let launchInstance;
let launchSequence = 0;
function launchField(object, key) {
    try {
        if (!object || typeof object !== 'object') { return undefined; }
        const descriptor = Object.getOwnPropertyDescriptor(object, key);
        return descriptor && Object.prototype.hasOwnProperty.call(descriptor, 'value')
            ? descriptor.value : undefined;
    } catch (_) { return undefined; }
}
function launchMessageClass(message) {
    // Pinned SDK AbilityConstant, API20. Classification is not authentication.
    return message === 'ReasonMessage_DesktopShortcut' ? 'desktop_shortcut' : 'unknown';
}
function launchHomeAction(action) {
    return action === 'ohos.want.action.home' || action === 'action.system.home' ? 'home' : 'unknown';
}
function launchHomeEntity(entities) {
    try {
        if (!Array.isArray(entities) || entities.length > 16) { return 'unknown'; }
        for (let i = 0; i < entities.length; i++) {
            if (launchField(entities, String(i)) === 'entity.system.home') { return 'home'; }
        }
    } catch (_) {}
    return 'unknown';
}
function observeLaunch(ability, callback, want, launchParam) {
    let temporary;
    let file;
    let phase = 'identity';
    try {
        if (!launchInstance) {
            const id = globalThis.requireNapi('util').generateRandomUUID(true);
            if (typeof id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)) {
                throw new Error('invalid instance');
            }
            launchInstance = id;
        }
        if (launchSequence >= Number.MAX_SAFE_INTEGER) { throw new Error('sequence exhausted'); }
        const sequence = ++launchSequence; // Failed writes consume a number too.
        const reason = launchField(launchParam, 'launchReason');
        const now = Date.now();
        const record = {
            callback: callback,
            instance: launchInstance,
            sequence: sequence,
            time: Number.isSafeInteger(now) && now >= 0 ? now : 'unknown',
            launchReason: Number.isInteger(reason) && reason >= 0 && reason <= 2147483647 ? reason : 'unknown',
            launchReasonMessage: launchMessageClass(launchField(launchParam, 'launchReasonMessage')),
            home_action: launchHomeAction(launchField(want, 'action')),
            home_entity: launchHomeEntity(launchField(want, 'entities')),
            manual_origin: 'unverified',
            eligible_for_reentry: false
        };
        const value = JSON.stringify(record); // All emitted strings are bounded ASCII.
        if (value.length > 1024) { throw new Error('record bound'); }
        const target = ability.context.filesDir + '/launch-observation.json';
        temporary = target + '.' + launchInstance + '.tmp';
        phase = 'open';
        file = fs.openSync(temporary, fs.OpenMode.CREATE | fs.OpenMode.WRITE_ONLY | fs.OpenMode.TRUNC);
        phase = 'write';
        if (fs.writeSync(file.fd, value) !== value.length) { throw new Error('short write'); }
        phase = 'close';
        const closing = file;
        file = undefined; // Do not retry a close with an unknown outcome.
        fs.closeSync(closing);
        phase = 'replace';
        fs.renameSync(temporary, target); // Same directory; old record untouched until commit.
        temporary = undefined;
        // The file is authoritative; logging failure cannot revoke its commit.
        try { hilog.info(0, TAG, 'launch-observation committed %{public}s', value); } catch (_) {}
    } catch (_) {
        // Never stringify an exception: it may contain input, paths or caller data.
        if (file) { try { fs.closeSync(file); } catch (_) {} }
        if (temporary) { try { fs.unlinkSync(temporary); } catch (_) {} }
        try { hilog.error(0, TAG, 'launch-observation failed %{public}s', phase); } catch (_) {}
    }
}
