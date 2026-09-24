const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
    const elements = new Map();
    function element() {
        return { value: '10', textContent: '', style: {}, children: [],
            addEventListener() {}, appendChild(child) { this.children.push(child); },
            replaceChildren() { this.children = []; } };
    }
    const token = role => 'header.' + Buffer.from(JSON.stringify({ role })).toString('base64url') + '.sig';
    const tokenInput = element();
    tokenInput.value = token('ADMIN');
    const context = vm.createContext({
        resetAdminPaginationForQueryChange() {},
        tokenInput, normalizeToken: value => value.trim(), AbortController, atob,
        document: { getElementById(id) {
            if (!elements.has(id)) elements.set(id, element());
            return elements.get(id);
        }, createElement: element },
        window: { addEventListener() {} },
        parseResponse: response => response.json(), getErrorMessage: data => data.detail,
    });
    const source = fs.readFileSync(path.join(__dirname, '../../frontend/script.js'), 'utf8');
    vm.runInContext(source.slice(source.indexOf('const adminDashboardSection ='),
        source.indexOf('async function analyzeBatch()')), context);
    return { context, tokenInput, token, get: suffix => elements.get('admin-dashboard-' + suffix) };
}

const data = { overview: { total_users: 7 }, prediction_distribution: [
    { class_name: '<img onerror=alert(1)>', count: 3 },
], model_usage: [], recent_analyses: [] };

test('dashboard sends token and renders exactly four overview cards', async () => {
    const { context, get, tokenInput } = setup();
    context.fetch = async (url, options) => {
        assert.equal(url, '/api/v1/admin/dashboard/summary');
        assert.equal(options.headers.Authorization, `Bearer ${tokenInput.value}`);
        return { ok: true, json: async () => data };
    };
    await context.loadAdminDashboard();
    assert.equal(get('overview').children[0].children[1].textContent, '7');
    assert.equal(get('predictions').children[0].children[0].textContent, '<img onerror=alert(1)>: 3');
    assert.match(get('status').textContent, /successfully/);
    assert.equal(get('overview').children.length, 4);
});

test('USER login automatically loads overview and guest makes no request', async () => {
    const { context, get, tokenInput, token } = setup();
    let calls = 0;
    context.fetch = async () => { calls++; return { ok: true, json: async () => data }; };
    tokenInput.value = token('USER');
    await context.initializeAdminDashboard();
    assert.equal(calls, 1);
    assert.equal(get('section').hidden, false);
    assert.equal(get('overview').children.length, 4);
    tokenInput.value = '';
    await context.initializeAdminDashboard();
    assert.equal(calls, 1);
    assert.equal(get('section').hidden, true);
    assert.equal(get('overview').children.length, 0);
});

test('API rejection clears data and allows retry', async () => {
    const { context, get } = setup();
    context.fetch = async () => ({ ok: false, status: 403, json: async () => ({}) });
    await context.loadAdminDashboard();
    assert.match(get('status').textContent, /Access denied/);
    assert.equal(get('overview').children.length, 0);
    context.fetch = async () => ({ ok: true, json: async () => data });
    await context.loadAdminDashboard();
    assert.equal(get('overview').children.length, 4);
});

test('duplicate clicks are ignored and logout prevents late rendering', async () => {
    const { context, get, tokenInput } = setup();
    let finish;
    let calls = 0;
    context.fetch = () => { calls++; return new Promise(resolve => { finish = resolve; }); };
    const loading = context.loadAdminDashboard();
    await context.loadAdminDashboard();
    assert.equal(calls, 1);
    tokenInput.value = '';
    context.initializeAdminDashboard();
    finish({ ok: true, json: async () => data });
    await loading;
    assert.equal(get('overview').children.length, 0);
    assert.equal(get('section').hidden, true);
});

test('ADMIN automatically loads overview using existing backend when summary route is missing', async () => {
    const {context,get} = setup();
    const urls=[];
    context.fetch=async url=>{
        urls.push(url);
        return url.endsWith('/summary') ? {ok:false,status:404,json:async()=>({detail:'Not Found'})}
            : {ok:true,json:async()=>({...data,overview:{total_users:7,active_users:6,total_patients:5,total_analyses:12}})};
    };
    await context.initializeAdminDashboard();
    assert.deepEqual(urls,['/api/v1/admin/dashboard/summary','/api/v1/admin/dashboard?recent_limit=1']);
    assert.deepEqual(get('overview').children.map(card=>card.children[1].textContent),['7','6','5','12']);
});

test('USER never falls back to the privileged dashboard endpoint', async () => {
    const {context,get,tokenInput,token} = setup();tokenInput.value=token('USER');
    const urls=[];
    context.fetch=async url=>{urls.push(url);return {ok:false,status:404,json:async()=>({detail:'Not Found'})};};
    await context.initializeAdminDashboard();
    assert.equal(urls.length,1);
    assert.match(get('status').textContent,/restart the backend/);
});
