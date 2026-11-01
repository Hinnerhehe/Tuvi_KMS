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
  for (const width of [1440, 768, 390]) {
    await page.setViewport({width, height: width === 768 ? 1024 : 900, mobile: width < 600});
    if (width < 1000) {
      await page.eval(() => document.querySelector('button[data-testid="stCollapseSidebarButton"]')?.click());
    }
    await sleep(500);
    await page.eval(() => document.fonts.ready);
    await page.screenshot({path: `${folder}/${width}-report.jpg`});
    const metrics = await page.eval(probe);
    const appMetrics = await page.eval(app);
    const findings = [...judge(metrics, {width}), ...judgeLayout(await page.eval(layout), {width})].filter(f => !APP_SKIP.has(f.id) && !['no-title','small-title'].includes(f.id));
    findings.push(...judgeApp(appMetrics, metrics, {width}));
    results.push({width, findings, horizontalOverflow: await page.eval(() => document.documentElement.scrollWidth > innerWidth)});
    if (width === 390) {
      await clickText('[role="tab"]', 'Tài chính');
      await page.eval(() => document.querySelector('[role="tablist"]').scrollIntoView({block:'start'}));
      await page.screenshot({path: `${folder}/390-finance.jpg`});
    }
  }

  await page.eval(() => [...document.querySelectorAll('h3,h2')].find(e => e.textContent.includes('Sao &')).scrollIntoView({block:'start'}));
  await page.screenshot({path: `${folder}/390-stars.jpg`});
  await page.setViewport({width:1440, height:900});
  await page.screenshot({path: `${folder}/1440-stars.jpg`});
  await page.setViewport({width:390, height:900, mobile:true});
  writeFileSync(`${folder}/checks.json`, JSON.stringify({results}, null, 2));
  console.log('toggles', await page.eval(() => [...document.querySelectorAll('label')].filter(e=>e.textContent.includes('Xem lá số')).map(e=>e.outerHTML)));
  await physicalClick('label', 'Xem lá số chi tiết 12 cung');
  await until(() => document.querySelectorAll('.horoscope-chart .cell:not(.center)').length === 12);
  await physicalClick('label', 'Xem trích dẫn sách gốc');
  await until(() => [...document.querySelectorAll('summary')].some(e => e.textContent.includes('[1]')));
  await page.eval(() => document.querySelector('.horoscope-chart').scrollIntoView({block:'start'}));
  await page.screenshot({path: `${folder}/390-chart.jpg`});
  await page.eval(() => {
    const expander = [...document.querySelectorAll('[data-testid="stExpander"]')].find(e => e.textContent.includes('[1]'));
    expander.querySelector('summary').click();
    expander.scrollIntoView({block:'start'});
  });
  await sleep(300);
  await page.screenshot({path: `${folder}/390-source.jpg`});
  await page.setViewport({width:1440, height:900});
  await page.eval(() => document.querySelector('.horoscope-chart').scrollIntoView({block:'start'}));
  await page.screenshot({path: `${folder}/1440-chart.jpg`});
  const rendered = await page.eval(() => ({palaces: document.querySelectorAll('.horoscope-chart .cell:not(.center)').length,
    sources: [...document.querySelectorAll('summary')].filter(e => /\[\d+\]/.test(e.textContent)).length,
    isMock: document.querySelector('.notice')?.textContent.includes('Phân tích dữ kiện lá số'),
    errors: document.querySelectorAll('[data-testid="stException"]').length}));
  writeFileSync(`${folder}/checks.json`, JSON.stringify({results, rendered, consoleErrors: page.consoleErrors}, null, 2));
  console.log(JSON.stringify({results, rendered, consoleErrors:page.consoleErrors}, null, 2));
  if (rendered.palaces !== 12 || !rendered.isMock || rendered.errors) process.exitCode = 1;
} finally { await page.close(); await browser.close(); }
