const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function setup() {
    function element() {
        return {children:[],handlers:{},textContent:'',className:'',open:false,
            append(...items){this.children.push(...items);},appendChild(item){this.children.push(item);},
            addEventListener(name,fn){this.handlers[name]=fn;}};
    }
    const context = vm.createContext({document:{createElement:element},formatHistoryDate:()=> '2026-09-22'});
    const source = fs.readFileSync(path.join(__dirname,'../../frontend/script.js'),'utf8');
    vm.runInContext(source.slice(source.indexOf('function createDrAIAdviceCard('),source.indexOf('function renderDrAIAdviceHistory(')),context);
    return context;
}
for(const [level,label] of [['LOW','🟢 Low Risk'],['MEDIUM','🟡 Medium Risk'],['HIGH','🔴 High Risk']]) {
    test(`${level} card shows one conclusion and recommendation with expandable report`,()=>{
        const context=setup();
        const report='PHIẾU TƯ VẤN\nPHẦN I\n<!> disclaimer';
        const card=context.createDrAIAdviceCard({language:'vi',advice_text:report,
            summary:{risk_level:level,conclusion:'One conclusion.',recommendation:'One recommendation.'}});
        assert.deepEqual(card.children.slice(0,3).map(item=>item.textContent),[label,'One conclusion.','One recommendation.']);
        const details=card.children[3];
        assert.equal(details.open,false);
        assert.equal(details.children[0].textContent,'Hiển thị thêm');
        assert.equal(details.children[2].textContent,report);
        details.open=true;details.handlers.toggle();
        assert.equal(details.children[0].textContent,'Thu gọn');
    });
}
test('old advice receives no invented risk and untrusted content is plain text',()=>{
    const context=setup();const html='<img src=x onerror=alert(1)>';
    const card=context.createDrAIAdviceCard({language:'en',advice_text:html});
    assert.match(card.children[0].textContent,/no warning level/);
    assert.equal(card.children[1].children[2].textContent,html);
    assert.equal(card.children[1].children[2].innerHTML,undefined);
});
