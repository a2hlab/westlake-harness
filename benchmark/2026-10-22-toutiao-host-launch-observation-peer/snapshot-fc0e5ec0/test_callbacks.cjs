'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const D = __dirname;
const candidate = fs.readFileSync(path.join(D, 'sources/candidate/EntryAbility.js'), 'utf8');
const baseline = fs.readFileSync(path.join(D, 'sources/baseline/EntryAbility.js'), 'utf8');
const TARGET = '/sandbox/files/launch-observation.json';
const SECRET = 'PRIVATE_SENTINEL_uri_parameters_caller_exception';
let uuidCount = 0, tests = 0;
function environment(source = candidate) {
    const files = new Map(), writes = [], logs = [], calls = [], handles = new Map();
    let fault = '', fd = 0, stageCallback, color, loaded;
    function fail(op, name) {
        if (fault === op && name.includes('launch-observation')) throw new Error(SECRET);
    }
    const mockfs = {
        OpenMode: {CREATE: 1, WRITE_ONLY: 2, TRUNC: 4},
        openSync(name, flags) {
            calls.push(['open',name,flags]); fail('open',name);
            files.set(name,''); handles.set(++fd,name); return {fd};
        },
        writeSync(number, value) {
            const name = handles.get(number); assert.ok(name); fail('write',name);
            const count = fault === 'partial' && name.includes('launch-observation') ? value.length - 1 : value.length;
            files.set(name,value.slice(0,count)); writes.push([name,value.slice(0,count)]); return count;
        },
        closeSync(file) {
            const name = handles.get(file.fd); assert.ok(name); handles.delete(file.fd);
            fail('close',name);
        },
        renameSync(from,to) {
            assert.ok(files.has(from)); fail('rename',from);
            files.set(to,files.get(from)); files.delete(from); calls.push(['rename',from,to]);
        },
        unlinkSync(name) { fail('unlink',name); files.delete(name); }
    };
    const win = {getWindowProperties: () => ({id:17}), setWindowBackgroundColor: x => {color=x;}};
    const stage = {
        on: (name, fn) => {assert.equal(name,'windowStageEvent');stageCallback=fn;},
        getMainWindowSync: () => win,
        loadContent: (page, fn) => {loaded=page;fn({code:0});}
    };
    const modules = {
        'app.ability.UIAbility': class {constructor(){this.context={filesDir:'/sandbox/files'};}},
        'file.fs': mockfs,
        hilog: {
            info: (...args) => {if(fault==='hilog') throw new Error(SECRET);logs.push(['info',...args]);},
            error: (...args) => {logs.push(['error',...args]);}
        },
        util: {generateRandomUUID: () => {
            if (fault==='uuid') throw new Error(SECRET);
            return '00000000-0000-4000-8000-'+String(++uuidCount).padStart(12,'0');
        }}
    };
    const context = vm.createContext({exports:{}, Date:class extends Date {static now(){return 1700000000000;}}, requireNapi:name=>{
        assert.ok(Object.hasOwn(modules,name),'Unexpected module '+name);return modules[name];
    }});
    vm.runInContext(source,context,{filename:'EntryAbility.js',timeout:1000});
    const newAbility = () => new context.exports.default();
    return {files,writes,logs,calls,stage,newAbility, ability:newAbility(),
        setFault: x=>{fault=x;}, emit: x=>stageCallback(x),
        get color(){return color;}, get loaded(){return loaded;},
        record:()=>JSON.parse(files.get(TARGET)),
        committed:()=>logs.filter(x=>x[3]==='launch-observation committed %{public}s'),
        privateCheck:()=>assert.ok(!JSON.stringify([...files,...writes,...logs]).includes(SECRET))};
}
function test(name, fn){fn();tests++;console.log('PASS '+name);}
function assertRecord(r){
    assert.deepEqual(Object.keys(r).sort(), ['callback','instance','sequence','time','launchReason','launchReasonMessage','home_action','home_entity','manual_origin','eligible_for_reentry'].sort());
    assert.equal(r.manual_origin,'unverified');assert.equal(r.eligible_for_reentry,false);
    assert.ok(Buffer.byteLength(JSON.stringify(r))<=1024);
}
test('real callbacks, registered stage event and unchanged baseline lifecycle',()=>{
    const a=environment(),b=environment(baseline);
    for (const e of [a,b]){e.ability.onCreate(); e.ability.onWindowStageCreate(e.stage); e.ability.onForeground();}
    assert.equal(a.loaded,'pages/Index');assert.equal(a.color,'#fff4f6f8');
    const first=a.record();assert.equal(first.sequence,1);
    a.ability.onNewWant({action:'ohos.want.action.home',entities:['entity.system.home']},{launchReason:1,launchReasonMessage:'ReasonMessage_DesktopShortcut'});
    const before=a.files.get(TARGET);assert.equal(a.record().sequence,2);assert.equal(a.record().home_action,'home');assert.equal(a.record().home_entity,'home');assert.equal(a.record().launchReasonMessage,'desktop_shortcut');
    for(const e of[a,b]){e.emit(3);e.ability.onBackground();e.ability.onWindowStageDestroy();e.ability.onDestroy();assert.equal(e.ability.stage,undefined);}
    assert.equal(a.files.get(TARGET),before);assert.equal(a.committed().length,2);
    assert.deepEqual(a.writes.filter(x=>x[0].endsWith('/window-state.json')), b.writes);
    assert.deepEqual(a.logs.filter(x=>!String(x[3]).startsWith('launch-observation')), b.logs);
    assertRecord(a.record());
});
for (const action of ['ohos.want.action.home','action.system.home']) test('home action whitelist '+action,()=>{
    const e=environment();e.ability.onNewWant({action}, {launchReason:1});assert.equal(e.record().home_action,'home');assertRecord(e.record());
});
test('all bounded numeric reasons and non-manual reasons never authorize reentry',()=>{
    const e=environment();
    for(const reason of [0,1,2,3,4,5,6,7,8,9,10,11,12,2147483647]){
        e.ability.onNewWant({}, {launchReason:reason});const r=e.record();assert.equal(r.launchReason,reason);assertRecord(r);
    }
});
test('missing, malformed, unknown launch parameters remain unknown',()=>{
    const e=environment();
    for(const lp of [undefined,null,1,'text',{}, {launchReason:-1},{launchReason:NaN},{launchReason:Infinity},{launchReason:1.5},{launchReason:'1'},{launchReason:2147483648}]){
        e.ability.onNewWant(undefined,lp);const r=e.record();assert.equal(r.launchReason,'unknown');assert.equal(r.launchReasonMessage,'unknown');assert.equal(r.home_entity,'unknown');assertRecord(r);
    }
});
test('private inputs, huge strings and getters never escape in any file or log',()=>{
    const e=environment(),want={uri:SECRET,parameters:{launchReason:1,launchReasonMessage:'ReasonMessage_DesktopShortcut',secret:SECRET},caller:SECRET,action:SECRET.repeat(5000),entities:[SECRET]},lp={launchReason:SECRET,launchReasonMessage:SECRET.repeat(5000)};
    e.ability.onCreate(want,lp);assert.equal(e.record().launchReason,'unknown');
    let invoked=0;
    const hostile={get action(){invoked++;throw new Error(SECRET);},get parameters(){invoked++;throw new Error(SECRET);}};
    e.ability.onNewWant(hostile,{get launchReason(){invoked++;throw new Error(SECRET);}});
    assert.equal(invoked,0);e.privateCheck();assertRecord(e.record());
});
test('oversized entity array and throwing proxies become unknown',()=>{
    const e=environment();e.ability.onNewWant({entities:new Array(17).fill('entity.system.home')},{});assert.equal(e.record().home_entity,'unknown');
    const hostile=new Proxy({}, {getOwnPropertyDescriptor(){throw new Error(SECRET);}});
    e.ability.onNewWant(hostile,hostile);assert.equal(e.record().launchReason,'unknown');e.privateCheck();
});
for(const failure of ['open','write','partial','close','rename']) test(failure+' failure preserves old committed record, no success claim, lifecycle survives',()=>{
    const e=environment();e.ability.onCreate();const old=e.files.get(TARGET),n=e.committed().length;
    e.setFault(failure);e.ability.onCreate({uri:SECRET},{launchReasonMessage:SECRET});
    assert.equal(e.files.get(TARGET),old);assert.equal(e.committed().length,n);assert.equal(JSON.parse(e.files.get('/sandbox/files/window-state.json')).event,'created');
    assert.ok(e.logs.some(x=>x[0]==='error'&&x[3]==='launch-observation failed %{public}s'));
    assert.equal([...e.files.keys()].filter(x=>x.endsWith('.tmp')).length,0);e.privateCheck();
    e.setFault('');e.ability.onNewWant();assert.equal(e.record().sequence,3);assert.equal(e.record().instance,JSON.parse(old).instance);
});
test('same millisecond, different JS instances and multiple Ability objects',()=>{
    const a=environment(),b=environment();a.ability.onCreate();b.ability.onCreate();
    assert.equal(a.record().time,b.record().time);assert.notEqual(a.record().instance,b.record().instance);assert.equal(a.record().sequence,1);assert.equal(b.record().sequence,1);
    const same=a.record().instance;a.newAbility().onNewWant();assert.equal(a.record().sequence,2);assert.equal(a.record().instance,same);
});
test('UUID unavailable fails visibly without disrupting original lifecycle',()=>{
    const e=environment();e.setFault('uuid');e.ability.onCreate();assert.ok(!e.files.has(TARGET));assert.equal(e.committed().length,0);assert.ok(e.files.has('/sandbox/files/window-state.json'));e.privateCheck();
});
test('logging exception after commit does not escape onNewWant',()=>{
    const e=environment();e.setFault('hilog');e.ability.onNewWant();assertRecord(e.record());e.privateCheck();
});
test('loadContent error callback and window operations preserved',()=>{
    const a=environment(),b=environment(baseline);
    for(const e of [a,b]) e.ability.onWindowStageCreate({...e.stage,loadContent:(page,fn)=>fn({code:9,message:'controlled-load-error'})});
    assert.deepEqual(a.writes,b.writes);assert.deepEqual(a.logs,b.logs);assert.equal(a.color,undefined);
});
console.log(JSON.stringify({status:'PASS_OFFLINE_CALLBACKS_ONLY',tests,candidate_sha256:crypto.createHash('sha256').update(candidate).digest('hex'),device_commands:0,hap_builds:0}));
