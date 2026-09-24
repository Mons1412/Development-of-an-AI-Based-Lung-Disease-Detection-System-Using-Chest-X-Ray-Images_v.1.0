const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const tick = () => new Promise(resolve => setImmediate(resolve));
const sample = {user_id:2, patient_code:'PX2', username:'patient2', full_name:'Nguyen An',
    phone:'0900000002', email:'an@example.com', address:'Le Loi', date_of_birth:'2000-01-01', sex:'MALE', is_active:true};
function setup() {
    const html = fs.readFileSync(path.join(__dirname, '../../frontend/index.html'), 'utf8');
    const elements = new Map();
    function element() {
        return {value:'', textContent:'', disabled:false, children:[], handlers:{}, style:{},
            classList:{add(){},remove(){},toggle(){}},
            addEventListener(name, fn) {this.handlers[name]=fn;},
            replaceChildren(){this.children=[];}, append(...children){this.children.push(...children);},
            appendChild(child){this.children.push(child);}, focus(){}, reportValidity(){return true;},
            showModal(){this.open=true;}, close(){this.open=false;},
            createTHead(){const child=element();this.children.push(child);return child;},
            createTBody(){const child=element();this.children.push(child);return child;},
            insertRow(){const child=element();this.children.push(child);return child;},
        };
    }
    for(const match of html.matchAll(/id="([^"]+)"/g)) elements.set(match[1],element());
    const window={handlers:{},addEventListener(name,fn){this.handlers[name]=fn;},confirm:()=>true};
    const context=vm.createContext({AbortController,atob,URLSearchParams,console,window,
        document:{getElementById:id=>elements.get(id)||null,querySelectorAll:()=>[],createElement:element,
            createTextNode:value=>({textContent:value})}});
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/script.js'),'utf8'),context);
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/admin_patients.js'),'utf8'),context);
    elements.get('token-input').value='h.'+Buffer.from(JSON.stringify({role:'ADMIN'})).toString('base64url')+'.s';
    elements.get('admin-patient-limit').value='20';
    const calls=[];
    context.fetch=async (url,options)=>{
        calls.push({url,options});
        if(url.endsWith('/details')){
            return {
                ok:true,
                text:async()=>JSON.stringify({
                    patient_profile:{
                        ...sample,
                        patient_id:22,
                        birth_year:2000,
                        height_cm:175,
                        weight_kg:62
                    },
                    medical_history:[{
                        id:51,
                        recorded_at:'2026-09-23T09:00:00',
                        current_complaint_hpi:'Cough for 4 days',
                        past_medical_history:'Hypertension',
                        past_medication_history:'Medication A',
                        allergy_history:'Penicillin allergy',
                        diet:'Regular diet',
                        appetite:'Normal',
                        sleep:'7 hours',
                        exercise:'Walking',
                        bowel_bladder:'Normal',
                        habits:'No smoking',
                        family_history:'None reported',
                        diseases:['Hypertension'],
                        medications:['Medication A'],
                        allergies:['Penicillin'],
                        smoking_status:'Never',
                        alcohol_status:'None',
                        occupational_exposure:'Office',
                        notes:'Follow-up history'
                    }],
                    analysis_history:[{
                        analysis_id:341,
                        analysis_code:'AN341',
                        status:'COMPLETED',
                        input_source:'UPLOAD',
                        original_filename:'test.png',
                        model_key:'mobilenetv2',
                        model_name:'MobileNetV2',
                        model_version:'1.1.0',
                        predicted_class:'normal',
                        confidence:0.8367,
                        has_image:true,
                        report_id:71,
                        report_code:'RP-AN341',
                        report_language:'vi',
                        report_created_at:'2026-09-23T10:16:00',
                        created_at:'2026-09-23T10:14:56',
                        completed_at:'2026-09-23T10:15:00'
                    }]
                })
            };
        }
        return {
            ok:true,
            text:async()=>JSON.stringify({
                items:[sample],
                total:1,
                page:1,
                limit:20
            })
        };
    };
    const get=id=>elements.get(id);
    const search=async()=>{get('admin-patient-search-form').handlers.submit({preventDefault(){}});await tick();};
    const actions=()=>get('admin-search-results').children[0].children[1].children[0].children[6].children;
    return {context,get,search,calls,actions,window};
}

test('full scripts initialize; submit searches by text and renders patient table with actions',async()=>{
    const {get,search,calls,actions}=setup();
    get('admin-patient-query').value=' Le Loi ';
    await search();
    assert.equal(calls[0].url,'/api/v1/admin/patients?q=Le+Loi&page=1&limit=20');
    assert.match(get('admin-search-status').textContent,/1 patient account/);
    assert.deepEqual(actions().map(x=>x.textContent),['View','Edit','Delete']);
    assert.equal(get('admin-history-offset'),undefined);
});

test('Edit submits patient data plus latest medical history',async()=>{
    const {
        context,
        get,
        search,
        calls,
        actions
    }=setup();

    await search();

    actions()[1].handlers.click();

    assert.equal(
        get('admin-patient-editor').open,
        true
    );

    assert.equal(
        get('admin-edit-name').value,
        sample.full_name
    );

    await tick();
    await tick();

    assert.equal(
        calls[1].url,
        '/api/v1/admin/patients/2/details'
    );

    assert.equal(
        get(
            'admin-edit-current-complaint'
        ).value,
        'Cough for 4 days'
    );

    assert.equal(
        get(
            'admin-edit-medical-id'
        ).value,
        '51'
    );

    get(
        'admin-edit-name'
    ).value =
        'Changed Name';

    get(
        'admin-edit-medical-notes'
    ).value =
        'Changed medical note';

    context.initializeAdminDashboard =
        ()=>{};

    await get(
        'admin-patient-edit-form'
    ).handlers.submit({
        preventDefault(){}
    });

    const putCall = calls.find(
        call =>
            call.options
            && call.options.method === 'PUT'
    );

    assert.ok(
        putCall
    );

    const body =
        JSON.parse(
            putCall.options.body
        );

    assert.equal(
        body.full_name,
        'Changed Name'
    );

    assert.equal(
        body.latest_medical_history.id,
        51
    );

    assert.equal(
        body.latest_medical_history.notes,
        'Changed medical note'
    );

    assert.deepEqual(
        body.latest_medical_history.diseases,
        ['Hypertension']
    );

    assert.equal(
        get(
            'admin-patient-editor'
        ).open,
        false
    );
});


test('Delete requires confirmation and calls the patient endpoint',async()=>{
    const {context,search,calls,actions,window}=setup();await search();
    window.confirm=()=>false;await actions()[2].handlers.click();assert.equal(calls.length,1);
    window.confirm=()=>true;context.initializeAdminDashboard=()=>{};
    await actions()[2].handlers.click();
    assert.equal(calls[1].url,'/api/v1/admin/patients/2');
    assert.equal(calls[1].options.method,'DELETE');
});

test('edit conflicts keep form open and show error',async()=>{
    const {context,get,search,actions}=setup();await search();actions()[1].handlers.click();
    context.fetch=async()=>({ok:false,status:409,text:async()=>'{"detail":"Phone already exists."}'});
    await get('admin-patient-edit-form').handlers.submit({preventDefault(){}});
    assert.equal(get('admin-patient-editor').open,true);
    assert.match(get('admin-patient-edit-status').textContent,/Phone already exists/);
    assert.equal(get('admin-patient-save').disabled,false);
});

test('logout clears records and prevents a late response restoring them',async()=>{
    const {context,get,search,window}=setup();let finish;
    context.fetch=()=>new Promise(resolve=>{finish=resolve;});
    await search();window.handlers['lungxray:auth-guest']();
    finish({ok:true,text:async()=>JSON.stringify({items:[sample],total:1,page:1,limit:20})});await tick();
    assert.equal(get('admin-search-results').children.length,0);
});


test('View opens Patient Details and loads profile plus analysis history',async()=>{
    const {get,search,calls,actions}=setup();

    await search();

    actions()[0].handlers.click();

    await tick();
    await tick();

    assert.equal(
        calls[1].url,
        '/api/v1/admin/patients/2/details'
    );

    assert.equal(
        get('admin-patient-viewer').open,
        true
    );

    assert.match(
        get('admin-patient-view-identity').textContent,
        /PX2/
    );

    assert.match(
        get('admin-patient-view-status').textContent,
        /1 analysis record/
    );

    assert.ok(
        get('admin-patient-view-profile').children.length > 0
    );

    assert.ok(
        get('admin-patient-view-medical').children.length > 0
    );

    assert.ok(
        get('admin-patient-view-analyses').children.length > 0
    );

    assert.match(
        get('admin-patient-view-status').textContent,
        /1 medical history record/
    );
});


test('Analysis History exposes image, Dr.AI, and PDF read-only actions',async()=>{
    const {get,search,actions}=setup();

    await search();

    actions()[0].handlers.click();

    await tick();
    await tick();

    function flatten(root) {
        const items = [];

        function walk(node) {
            items.push(node);

            for (
                const child
                of (node.children || [])
            ) {
                walk(child);
            }
        }

        walk(root);

        return items;
    }

    const labels = flatten(
        get('admin-patient-view-analyses')
    )
    .map(item => item.textContent);

    assert.ok(
        labels.includes('View X-ray Image')
    );

    assert.ok(
        labels.includes('View Dr.AI Advice')
    );

    assert.ok(
        labels.includes('Preview Report PDF')
    );

    assert.ok(
        labels.includes('Download Report PDF')
    );

    assert.ok(
        labels.includes('Preview Dr.AI PDF')
    );

    assert.ok(
        labels.includes('Download Dr.AI PDF')
    );
});
