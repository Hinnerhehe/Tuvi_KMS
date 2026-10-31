import { Browser, sleep } from 'file:///C:/Users/admin/.codex/skills/design-taste-frontend/scripts/lib/cdp.mjs';
import {writeFileSync} from 'node:fs';
const browser = await Browser.launch();
try {
 const p=await browser.newPage(); await p.goto('http://127.0.0.1:8502'); await sleep(1000);
 await p.eval(()=>[...document.querySelectorAll('summary')].find(e=>e.textContent.includes('Tùy chọn bài đọc')).click());
 const box=await p.eval(()=>{const e=[...document.querySelectorAll('[data-testid="stSelectbox"]')].find(e=>e.textContent.includes('Bản luận giải')); const r=e.querySelector('[role="combobox"]').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2,html:e.outerHTML};});
 await p.eval(()=>[...document.querySelectorAll('[data-testid="stSelectbox"]')].find(e=>e.textContent.includes('Bản luận giải')).scrollIntoView({block:'center'}));
 const point=await p.eval(()=>{const r=[...document.querySelectorAll('[data-testid="stSelectbox"]')].find(e=>e.textContent.includes('Bản luận giải')).getBoundingClientRect();return{x:r.x+r.width/2,y:r.bottom-20};});
 await p.send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
 await p.send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1}); await sleep(300);
 console.log(JSON.stringify({box,options:await p.eval(()=>[...document.querySelectorAll('[role="option"], [role="listbox"]')].map(e=>e.outerHTML.slice(0,1500)))}));
 await p.setViewport({width:768,height:1024}); await sleep(300);
 console.log(JSON.stringify(await p.eval(()=>({sidebar:document.querySelector('[data-testid="stSidebar"]').outerHTML.slice(0,3000),nav:[...document.querySelectorAll('button')].filter(e=>/sidebar|expand|collapse/i.test(e.outerHTML)).map(e=>e.outerHTML.slice(0,800)),main:document.querySelector('[data-testid="stMain"]').outerHTML.slice(0,500)}))));
 await p.screenshot({path:'.taste-skill/debug.jpg'});
}finally{await browser.close();}
