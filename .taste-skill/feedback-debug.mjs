// Local, offline UI acceptance: uses the real running Streamlit app and mock API mode.
import { mkdirSync, writeFileSync } from 'node:fs';
import { Browser, sleep } from 'file:///C:/Users/admin/.codex/skills/design-taste-frontend/scripts/lib/cdp.mjs';
import { probe, layout, app } from 'file:///C:/Users/admin/.codex/skills/design-taste-frontend/scripts/lib/probe.mjs';
import { judge, judgeLayout, judgeApp, APP_SKIP } from 'file:///C:/Users/admin/.codex/skills/design-taste-frontend/scripts/lib/rules.mjs';

const folder = '.taste-skill/feedback-ui';
mkdirSync(folder, { recursive: true });
const browser = await Browser.launch();
const page = await browser.newPage({width: 1440, height: 1200});
const until = async (fn) => {
  for (let attempt = 0; attempt < 40; attempt++) {
    if (await page.eval(fn)) return;
    await sleep(300);
  }
  throw new Error('UI condition timed out');
};
const clickText = async (selector, label) => {
  const ok = await page.eval(({selector, label}) => {
    const element = [...document.querySelectorAll(selector)].find(e => e.textContent.includes(label));
    element?.click();
    return !!element;
  }, {selector, label});
  if (!ok) throw new Error('Missing control: ' + label);
};
const results = [];
const physicalClick = async (selector, label) => {
  await page.eval(({selector,label}) => [...document.querySelectorAll(selector)].find(e=>e.textContent.includes(label)).scrollIntoView({block:'center'}), {selector,label});
  await sleep(650);
  const p = await page.eval(({selector,label}) => {const r=[...document.querySelectorAll(selector)].find(e=>e.textContent.includes(label)).getBoundingClientRect();return {x:r.x+20,y:r.y+r.height/2};}, {selector,label});
  await page.send('Input.dispatchMouseEvent', {type:'mousePressed', ...p, button:'left', clickCount:1});
  await page.send('Input.dispatchMouseEvent', {type:'mouseReleased', ...p, button:'left', clickCount:1});
};
try {
  await page.goto('http://127.0.0.1:8503');
  await until(() => !!document.querySelector('h1'));
  await until(() => [...document.querySelectorAll('summary')].some(e => e.textContent.includes('Tùy chọn bài đọc')));
  await clickText('summary', 'Tùy chọn bài đọc');
  await sleep(650);
  await page.eval(() => [...document.querySelectorAll('[data-testid="stSelectbox"]')].find(e => e.textContent.includes('Bản luận giải')).querySelector('button').scrollIntoView({block:'center'}));
  await sleep(400);
  const point = await page.eval(() => {
    const r = [...document.querySelectorAll('[data-testid="stSelectbox"]')].find(e => e.textContent.includes('Bản luận giải')).querySelector('button').getBoundingClientRect();
    return {x:r.x+r.width/2, y:r.y+r.height/2};
  });
  await page.send('Input.dispatchMouseEvent', {type:'mousePressed', ...point, button:'left', clickCount:1});
  await page.send('Input.dispatchMouseEvent', {type:'mouseReleased', ...point, button:'left', clickCount:1});
  console.log('click point', point);
  await page.screenshot({path: `${folder}/dropdown-debug.jpg`});
  console.log(await page.eval(() => ({options:[...document.querySelectorAll('[role="option"]')].map(e=>e.textContent),inputs:[...document.querySelectorAll('[role="combobox"]')].map(e=>({value:e.value,expanded:e.getAttribute('aria-expanded')}))})));
  await until(() => [...document.querySelectorAll('[role="option"]')].some(e => e.textContent.includes('Dữ kiện lá số')));
  await page.eval(() => [...document.querySelectorAll('[role="option"]')].find(e => e.textContent.includes('Dữ kiện lá số')).click());
  await clickText('summary', 'Tùy chọn bài đọc');
  await clickText('button', 'Tạo bản luận giải');
  await until(() => !!document.querySelector('.report-heading'));

  console.log('TABLE', await page.eval(() => [...document.querySelectorAll('table')].map(e=>({html:e.outerHTML.slice(0,700),font:getComputedStyle(e).fontFamily}))));
  console.log('SOURCE_FONTS', await page.eval(() => [...document.querySelectorAll('body *')].filter(e=>e.children.length===0 && e.textContent.trim() && getComputedStyle(e).fontFamily.includes('Source')).slice(0,15).map(e=>({tag:e.tagName,cl:e.className,text:e.textContent.slice(0,60)}))));
  console.log('CSS', await page.eval(() => [...document.querySelectorAll('style')].find(e=>e.textContent.includes('.star-table-wrap'))?.textContent.slice(-2500)));
  process.exitCode=0;
} finally { await page.close(); await browser.close(); }