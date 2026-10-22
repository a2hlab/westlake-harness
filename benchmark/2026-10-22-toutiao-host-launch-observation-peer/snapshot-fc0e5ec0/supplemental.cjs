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
        if ((fault === op || (fault === 'partial_unlink' && op === 'unlink')) && name.includes('launch-observation')) throw new Error(SECRET);
    }
    const mockfs = {
        OpenMode: {CREATE: 1, WRITE_ONLY: 2, TRUNC: 4},
        openSync(name, flags) {
            calls.push(['open',name,flags]); fail('open',name);
            files.set(name,''); handles.set(++fd,name); return {fd};
        },
        writeSync(number, value) {
            const name = handles.get(number); assert.ok(name); fail('write',name);
            const count = (fault === 'partial' || fault === 'partial_unlink') && name.includes('launch-observation') ? value.length - 1 : value.length;
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

test('partial write plus failed cleanup leaves bounded temp only; next callback recovers',()=>{
 const e=environment();e.ability.onCreate();const old=e.files.get(TARGET),n=e.committed().length;
 e.setFault('partial_unlink');e.ability.onCreate({uri:SECRET,parameters:{secret:SECRET}}, {launchReasonMessage:SECRET});
 assert.equal(e.files.get(TARGET),old);assert.equal(e.committed().length,n);
 assert.equal([...e.files.keys()].filter(x=>x.endsWith('.tmp')).length,1);
 assert.equal(JSON.parse(e.files.get('/sandbox/files/window-state.json')).event,'created');e.privateCheck();
 e.setFault('');e.ability.onNewWant();assert.equal(e.record().sequence,3);assertRecord(e.record());
 assert.equal([...e.files.keys()].filter(x=>x.endsWith('.tmp')).length,0);
});
test('foreground after latest onNewWant preserves exact launch bytes',()=>{
 const e=environment();e.ability.onCreate();e.ability.onNewWant();const latest=e.files.get(TARGET);
 e.ability.onForeground();assert.equal(e.files.get(TARGET),latest);
 assert.equal(JSON.parse(e.files.get('/sandbox/files/window-state.json')).event,'foreground');
});
console.log(JSON.stringify({status:'PASS_SUPPLEMENTAL_MOCK_ONLY',tests}));
