/* Real Chrome checks without third-party dependencies. Serves the publishing package at a project URL. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const CDPSocket = require('./cdp-socket.cjs');
const root = path.resolve(__dirname, '../..');
const site = path.join(root, 'github-pages');
const output = path.join(root, '.qa');
fs.mkdirSync(output, {recursive: true});
const mime = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.jpg':'image/jpeg', '.svg':'image/svg+xml', '.mp4':'video/mp4', '.json':'application/json'};
const prefix = '/conference-test/';
const requests = [], errors = [], results = [];
let chrome, ws, server, closeBrowser;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  server = http.createServer((req, res) => {
    const requested = new URL(req.url, 'http://localhost');
    const url = decodeURIComponent(requested.pathname);
    if (!url.startsWith(prefix)) { res.writeHead(404).end(); return; }
    const filename = path.resolve(site, url.slice(prefix.length) || 'index.html');
    if (!filename.startsWith(site + path.sep) || !fs.existsSync(filename) || !fs.statSync(filename).isFile()) { res.writeHead(404).end(); requests.push({url,status:404}); return; }
    const stat = fs.statSync(filename);
    let start = 0, end = stat.size - 1, status = 200;
    const headers = {'Content-Type':mime[path.extname(filename)] || 'application/octet-stream', 'Accept-Ranges':requested.searchParams.has('no-range')?'none':'bytes'};
    const range = requested.searchParams.has('no-range') ? null : req.headers.range?.match(/^bytes=(\d+)-(\d*)$/);
    if (range) { start = Number(range[1]); end = range[2] ? Math.min(end, Number(range[2])) : end; status = 206; headers['Content-Range'] = `bytes ${start}-${end}/${stat.size}`; }
    headers['Content-Length'] = Math.max(0, end - start + 1);
    res.writeHead(status, headers); requests.push({url,status});
    if (!stat.size) res.end(); else fs.createReadStream(filename,{start,end}).pipe(res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}${prefix}`;
  const profile = path.join(output, 'chrome-profile-' + Date.now());
  const executable = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  const portFile = path.join(profile, 'DevToolsActivePort');
  fs.rmSync(portFile, {force:true});
  chrome = spawn(executable, ['--headless=new', '--remote-debugging-port=0', '--remote-allow-origins=*', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--disable-sync', '--disable-background-networking', 'about:blank'], {windowsHide:true, stdio:'ignore'});
  for (let i = 0; i < 100 && !fs.existsSync(portFile); i++) await sleep(100);
  if (!fs.existsSync(portFile)) throw new Error('Chrome did not expose its debugging port.');
  const port = fs.readFileSync(portFile,'utf8').split('\n')[0];
  let pages;
  for (let i = 0; i < 50; i++) {
    try { pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (pages.some(page => page.type === 'page')) break; } catch {}
    await sleep(100);
  }
  ws = new CDPSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl);
  console.log('Chrome ready; connecting to browser controls.');
  await new Promise((resolve,reject) => {
    const timeout=setTimeout(()=>reject(new Error('Timed out connecting browser controls.')),10000);
    ws.onopen=()=>{clearTimeout(timeout);resolve();};
    ws.onerror=event=>{clearTimeout(timeout);reject(new Error(event.message + ': ' + String(event.error)));};
  });
  let serial = 0; const pending = new Map();
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const handler = pending.get(message.id); pending.delete(message.id); clearTimeout(handler?.timeout);
      if (message.error) handler?.reject(new Error(JSON.stringify(message.error))); else handler?.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
  };
  const send = (method, params={}) => new Promise((resolve,reject) => { const id=++serial; const timeout=setTimeout(()=>{pending.delete(id);reject(new Error('Browser command timed out: '+method));},10000); pending.set(id,{resolve,reject,timeout}); ws.send(JSON.stringify({id,method,params})); });
  closeBrowser = () => send('Browser.close');
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text + ': ' + result.result.description);
    return result.result.value;
  };
  const waitFor = async expression => { for(let i=0;i<100;i++) { if(await evaluate(expression)) return; await sleep(100); } throw new Error('Timed out: '+expression); };
  const click = async selector => { assert.equal(await evaluate(`!!document.querySelector(${JSON.stringify(selector)})`),true,'Control exists: '+selector); await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); };
  const check = async (expression, description) => { assert.ok(await evaluate(expression),description); results.push(description); };
  const screenshot = async name => { const data=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true}); fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(data.data,'base64')); };
  await send('Runtime.enable'); await send('Page.enable');
  console.log('Browser controls connected.');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:base});
  await waitFor(`!!window.CONFERENCE_CONTENT && document.getElementById('practiceButton') && typeof game !== 'undefined'`);
  await evaluate(`localStorage.clear()`); await send('Page.reload');
  await waitFor(`!!document.querySelectorAll('.mosaic-tile').length`);
  await screenshot('welcome-desktop');
  await check(`document.querySelector('.brand-title').textContent==='Willowbrook Ward Conference Story Challenge' && !document.querySelector('.brand br') && getComputedStyle(document.querySelector('.brand')).fontSize==='24px' && document.querySelector('.brand-title').getBoundingClientRect().height<36`,'Ward title is on one line at twice the original desktop font size');
  await check(`document.querySelectorAll('.mosaic-tile').length===6 && document.querySelectorAll('#teamFields input').length===6`,'Six topic cards and six team fields load at a GitHub-style project URL');
  await click('#practiceButton'); await click('#practiceQuestion'); await click('#practiceReveal');
  await check(`document.getElementById('modal').open && !localStorage.getItem(STORAGE_KEY)`,'Practice works without consuming a clue or a saved game');
  await click('#practiceDone'); await click('#startButton');
  await check(`game.teams.length===6 && document.querySelectorAll('.board-cell').length===30 && document.querySelectorAll('.board-cell:not(:disabled)').length===5`,'Board loads all 30 clues with assigned-category opening');
  await screenshot('board-desktop');
  await click('[data-card="following-100"]');
  await check(`document.querySelector('.retelling').textContent===cardFor('following-100').intro && !document.querySelector('#clueView').innerText.toLowerCase().includes('peaches') && !document.querySelector('#clueView [data-clip]') && document.querySelector('.clue-side img').src.endsWith(cardFor('following-100').image)`,'Clue page shows the speaker picture and no video hints or fruit answer');
  await screenshot('story-desktop');
  await click('#questionButton');
  await check(`document.getElementById('answerClock') && document.querySelector('.media-details summary').textContent==='Optional video hint'`,'Question page keeps its timer and optional video hint');
  await sleep(1150);
  await check(`game.active.remaining<20 && game.active.running && document.getElementById('answerPause').textContent==='Pause'`,'Opening the question automatically starts its countdown');
  await click('#answerPause');
  const pausedTime = await evaluate(`game.active.remaining`);
  await sleep(300);
  await check(`game.active.remaining===${pausedTime} && !game.active.running`,'Pause holds the automatic countdown');
  await click('.media-details summary'); await click('[data-clip="0"]');
  await waitFor(`document.getElementById('storyVideo').readyState>=1 || !document.getElementById('mediaError').hidden`);
  await check(`document.getElementById('storyVideo').duration>40 && document.getElementById('mediaError').hidden`,'Prepared conference clip loads with playable metadata');
  await click('#answerPause'); await sleep(1150);
  await check(`game.active.remaining<20 && game.active.running`,'Paused countdown resumes');
  await click('#answerPause'); await click('#answerReset');
  await check(`game.active.remaining>19.5 && game.active.running`,'Reset restores the full answer time and restarts automatically');
  await click('#answerPause');
  await click('#rereadButton'); await check(`document.getElementById('modal').open && document.querySelector('#modalBody .retelling').textContent===cardFor('following-100').intro && !document.getElementById('modalBody').innerText.includes('peaches')`,'Rereading the clue preserves the reminder without revealing the answer'); await click('#backToQuestion');
  await screenshot('question-desktop'); await click('#revealButton');
  await click('.story-recap summary');
  await check(`document.querySelector('.story-recap p').textContent===cardFor('following-100').retelling && document.querySelectorAll('.clip-preview').length===cardFor('following-100').clips.length && document.querySelector('.clip-preview-frame').style.backgroundImage.includes('clip-previews.jpg') && !document.querySelector('#clueView .media-details')`,'Answer page directly displays video previews for every clip');
  await click('.clip-preview[data-clip="0"]');
  await waitFor(`document.fullscreenElement===document.getElementById('storyVideo') && document.getElementById('storyVideo').readyState>=2`);
  await check(`document.fullscreenElement===document.getElementById('storyVideo') && !document.getElementById('storyVideo').paused && document.getElementById('storyVideo').controls`,'Clicking a clip preview starts full-screen playback with video controls');
  await evaluate(`document.getElementById('storyVideo').pause();document.getElementById('storyVideo').currentTime=document.getElementById('storyVideo').duration*.7`);
  await waitFor(`!document.getElementById('storyVideo').seeking`);
  await check(`Math.abs(document.getElementById('storyVideo').currentTime/document.getElementById('storyVideo').duration-.7)<.02`,'Video can seek forward before the full clip has streamed');
  await evaluate(`document.getElementById('storyVideo').currentTime=document.getElementById('storyVideo').duration*.2`);
  await waitFor(`!document.getElementById('storyVideo').seeking`);
  await check(`Math.abs(document.getElementById('storyVideo').currentTime/document.getElementById('storyVideo').duration-.2)<.02`,'Video can seek backward');
  // Exercise the actual native timeline, which Chrome exposes in its media shadow DOM.
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:700,y:970});
  await sleep(250);
  const tree=await send('DOM.getDocument',{depth:-1,pierce:true});
  function findTimeline(node) {
    const attrs=Object.fromEntries((node.attributes||[]).reduce((pairs,value,index,list)=>index%2?pairs:[...pairs,[value,list[index+1]]],[]));
    if(node.nodeName==='INPUT' && attrs.type==='range' && Number(attrs.max)>1) return node;
    for(const child of [...(node.children||[]),...(node.shadowRoots||[])]) {const found=findTimeline(child);if(found)return found;}
    return null;
  }
  const timeline=findTimeline(tree.root);
  assert.ok(timeline,'Native video timeline is available');
  const model=await send('DOM.getBoxModel',{nodeId:timeline.nodeId});
  const quad=model.model.content,left=quad[0],right=quad[2],y=(quad[1]+quad[5])/2;
  async function dragTimeline(from,to) {
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:left+(right-left)*from,y});
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x:left+(right-left)*from,y,button:'left',buttons:1,clickCount:1});
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:left+(right-left)*to,y,button:'left',buttons:1});
    await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:left+(right-left)*to,y,button:'left',buttons:0,clickCount:1});
    await waitFor(`!document.getElementById('storyVideo').seeking`);
  }
  await dragTimeline(.2,.7);
  await check(`Math.abs(document.getElementById('storyVideo').currentTime/document.getElementById('storyVideo').duration-.7)<.1`,'Dragging the actual video progress bar seeks forward');
  await dragTimeline(.7,.2);
  await check(`Math.abs(document.getElementById('storyVideo').currentTime/document.getElementById('storyVideo').duration-.2)<.1`,'Dragging the actual video progress bar seeks backward');
  await evaluate(`document.exitFullscreen()`);
  const realClipPath=await evaluate(`cardFor('following-100').clips[0].path`);
  await evaluate(`cardFor('following-100').clips[0].path+='?no-range=1'`);
  await click('.clip-preview[data-clip="0"]');
  await waitFor(`document.getElementById('storyVideo').src.startsWith('blob:') && document.getElementById('storyVideo').readyState>=2`);
  await evaluate(`document.getElementById('storyVideo').pause();document.getElementById('storyVideo').currentTime=30`);
  await waitFor(`!document.getElementById('storyVideo').seeking`);
  await check(`Math.abs(document.getElementById('storyVideo').currentTime-30)<.2`,'Fallback supports seeking on a local server without byte ranges');
  await evaluate(`document.getElementById('storyVideo').currentTime=5`);
  await waitFor(`!document.getElementById('storyVideo').seeking`);
  await check(`Math.abs(document.getElementById('storyVideo').currentTime-5)<.2`,'Fallback also supports backward seeking');
  await evaluate(`document.exitFullscreen();cardFor('following-100').clips[0].path=${JSON.stringify(realClipPath)}`);
  await check(`document.getElementById('completeButton').disabled`,'Scoring requires every team to receive an explicit award');
  for(let index=0;index<6;index++) await click(`[data-team="${index}"][data-award="${index===0?100:index===1?50:0}"]`);
  await screenshot('answer-desktop');
  await send('Page.reload'); await waitFor(`!!document.querySelector('#resumePanel:not([hidden])')`); await click('#resumeButton');
  await check(`game.active.phase==='reveal' && game.active.awards[0]===100 && !document.getElementById('completeButton').disabled`,'A reload preserves the in-progress reveal and uncommitted awards');
  await click('#completeButton');
  await check(`game.rounds.length===1 && game.teams[0].score===100 && game.teams[1].score===50 && rules.allowedTopics(game,content)[0]==='identity'`,'Full, half, and zero awards commit once and advance choosing team');
  await click('[data-card="following-100"]'); await check(`document.getElementById('modal').open && game.rounds.length===1`,'Played clue opens a review without awarding again'); await click('#modalClose');
  await click('#scoresButton'); await evaluate(`document.getElementById('correctScore0').value='150'`); await click('#scoreForm button');
  await check(`game.teams[0].score===150 && rules.validate(game,content)`,'Score corrections create a consistent saved game');
  await click('#undoButton');
  await check(`game.rounds.length===0 && game.teams[0].score===50 && game.teams[1].score===0`,'Undo restores the clue and retains manual score corrections');
  await click('[data-card="following-500"]'); await click('#cancelClue');
  await check(`game.rounds.length===0 && game.active===null`,'Canceling an unscored clue keeps it available');
  // Check every clue's UI and caption-based media references without altering the user's files.
  await evaluate(`game.balanced=false; save(); render()`);
  for (const id of await evaluate(`content.cards.map(card=>card.id)`)) {
    await click(`[data-card="${id}"]`);
    await check(`document.querySelector('#clueView .retelling').textContent===cardFor(${JSON.stringify(id)}).intro && !document.querySelector('#clueView .story-recap') && !document.querySelector('#clueView [data-clip]') && document.querySelector('.clue-side img').src.endsWith(cardFor(${JSON.stringify(id)}).image)`,'Clue has its speaker photo and keeps videos and answers for later: '+id);
    await click('#questionButton');
    await check(`game.active.running && game.active.remaining>0`,'Answer timer starts automatically: '+id);
    await click('#revealButton');
    await check(`document.querySelectorAll('.answer-list li').length>0 && document.querySelectorAll('.award-team').length===6 && document.querySelector('.takeaway p:last-child').textContent===cardFor(${JSON.stringify(id)}).takeaway && !document.querySelector('.source-context').open`,'Clue reveals its main takeaway, optional context, and all-team scoring: '+id);
    await click('#cancelClue');
  }
  // Verify real ended events advance all four Kearon clips without leaving full screen.
  await click('[data-card="revelation-300"]'); await click('#questionButton'); await click('#revealButton');
  await click('.clip-preview[data-clip="0"]');
  await waitFor(`document.fullscreenElement===document.getElementById('storyVideo') && document.getElementById('storyVideo').readyState>=2`);
  for (let index=1;index<4;index++) {
    await evaluate(`document.getElementById('storyVideo').currentTime=document.getElementById('storyVideo').duration-.1;document.getElementById('storyVideo').play()`);
    await waitFor(`document.getElementById('storyVideo').src.endsWith(cardFor('revelation-300').clips[${index}].path) && document.getElementById('storyVideo').readyState>=2 && !document.getElementById('storyVideo').paused`);
    await check(`document.fullscreenElement===document.getElementById('storyVideo') && document.getElementById('storyVideo').currentTime<2 && document.querySelector('.clip-preview[aria-current=true]').dataset.clip==='${index}'`,'Kearon clip '+(index+1)+' autoplays from its beginning in the same full-screen player');
  }
  await evaluate(`document.getElementById('storyVideo').currentTime=document.getElementById('storyVideo').duration-.1;document.getElementById('storyVideo').play()`);
  await waitFor(`!document.fullscreenElement && document.getElementById('clipStatus').textContent.startsWith('Clips finished')`);
  await check(`document.getElementById('storyVideo').ended && !document.querySelector('.clip-preview[aria-current=true]')`,'The last clip ends the sequence and returns to the answer');
  await click('.clip-preview[data-clip="2"]');
  await waitFor(`document.getElementById('storyVideo').src.endsWith(cardFor('revelation-300').clips[2].path) && document.getElementById('storyVideo').readyState>=2`);
  await check(`document.getElementById('storyVideo').currentTime<2 && document.querySelector('.clip-preview[aria-current=true]').dataset.clip==='2'`,'A later preview starts the sequence at the selected clip');
  await evaluate(`document.exitFullscreen()`); await click('#cancelClue');
  await click('[data-card="serving-100"]'); await click('#questionButton'); await click('#revealButton');
  await screenshot('sinclair-preview-desktop');
  await click('.clip-preview[data-clip="0"]');
  await waitFor(`document.getElementById('storyVideo').readyState>=2 && !document.getElementById('storyVideo').paused`);
  await check(`cardFor('serving-100').clips[0].previewTime===2 && document.getElementById('storyVideo').currentTime<1`,'Sinclair uses the 0:02 preview while playback starts at the beginning');
  await evaluate(`document.exitFullscreen()`); await click('#cancelClue');
  // A failed optional hint must not prevent answering or accessing context after reveal.
  await click('[data-card="covenants-500"]'); await click('#questionButton'); await click('.media-details summary');
  await evaluate(`cardFor('covenants-500').clips[0].path='assets/intentional-missing-test.mp4'`);
  await click('[data-clip="0"]');
  await waitFor(`!document.getElementById('mediaError').hidden`);
  await click('#revealButton');
  await check(`document.querySelector('.qualification').textContent.includes('adversity') && document.querySelector('.story-recap p').textContent.includes('no fault')`,'A failed video hint still allows the answer reveal with the passport adversity qualification');
  await click('#cancelClue'); await click('#finalButton'); await click('#finalExamplesButton');
  await check(`!document.getElementById('finalExamples').hidden && game.teams[0].score===50`,'Cooperative final reveals supported topic connections without adding points');
  await click('#closingButton'); await screenshot('closing-desktop');
  await check(`!game.sessionRunning && document.querySelectorAll('.next-step').length===3`,'Closing stops the activity clock and offers study, ponder, and act');
  await click('#closingClipButton'); await waitFor(`document.getElementById('closingVideo').readyState>=1`);
  await check(`document.getElementById('closingVideo').duration>20`,'Closing invitation clip loads');
  await click('#newGameButton');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await screenshot('welcome-mobile');
  await check(`document.documentElement.scrollWidth<=390`,'Mobile setup fits the viewport');
  await check(`document.querySelector('.brand-title').getBoundingClientRect().right<=390 && getComputedStyle(document.querySelector('.brand')).whiteSpace==='nowrap'`,'The full ward title remains on one line on mobile');
  await click('#resumeButton'); await click('#closingBoardButton'); await screenshot('board-mobile');
  await check(`document.documentElement.scrollWidth<=390 && document.querySelector('.board-scroll').scrollWidth>document.querySelector('.board-scroll').clientWidth`,'Mobile board scrolls within its container');
  await click('[data-card="identity-500"]'); await click('#questionButton'); await click('#revealButton'); await screenshot('answer-mobile');
  await check(`document.documentElement.scrollWidth<=390`,'Mobile question and scoring fit the viewport');
  const downloads=path.join(output,'downloads');fs.mkdirSync(downloads,{recursive:true});
  const backupPath=path.join(downloads,'conference-story-challenge-save.json');fs.rmSync(backupPath,{force:true});
  await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});
  await click('#exportButton');
  for(let i=0;i<50&&!fs.existsSync(backupPath);i++)await sleep(100);
  assert.ok(fs.existsSync(backupPath),'Backup downloads successfully');
  const backup=JSON.parse(fs.readFileSync(backupPath,'utf8'));
  assert.equal(backup.teams.length,6);results.push('Downloaded backup preserves all teams and the in-progress clue');
  await click('#homeButton');
  await evaluate(`document.getElementById('teamCount').value='1';document.getElementById('teamCount').dispatchEvent(new Event('change'));document.getElementById('teamName0').value='<img src=x onerror=alert(1)>'`);
  await click('#startButton'); await click('#confirmAction');
  await check(`game.teams.length===1 && document.querySelector('.team-score span').textContent.includes('<img') && !document.querySelector('.team-score img')`,'One-team leader preview works and team names render as text');
  const rootNode=await send('DOM.getDocument');
  const inputNode=await send('DOM.querySelector',{nodeId:rootNode.root.nodeId,selector:'#importFile'});
  await send('DOM.setFileInputFiles',{nodeId:inputNode.nodeId,files:[backupPath]});
  await waitFor(`document.getElementById('confirmAction') && document.getElementById('modal').open`);
  await click('#confirmAction');
  await check(`game.teams.length===6 && game.active.id==='identity-500' && game.active.phase==='reveal' && game.teams[0].score===50`,'Loading a backup restores the original teams, scores, and in-progress reveal');
  const invalidPath=path.join(output,'invalid-backup.json');fs.writeFileSync(invalidPath,'{"version":1,"teams":[null]}');
  await send('DOM.setFileInputFiles',{nodeId:inputNode.nodeId,files:[invalidPath]});
  await waitFor(`!document.getElementById('notice').hidden`);
  await check(`game.teams.length===6 && game.active.id==='identity-500'`,'An invalid backup leaves the current game intact');
  await evaluate(`window.print=()=>{};`); // Avoid opening an operating-system print dialog in automated QA.
  await click('#printButton');
  await check(`document.querySelectorAll('#printGuide article').length===30`,'Printable host guide contains all 30 retellings, questions, and answer keys');
  await click('#guideButton'); await check(`document.getElementById('modal').open`,'How-to-play guide is available'); await click('#modalClose');
  await send('Page.navigate',{url:pathToFileURL(path.join(site,'index.html')).href});
  await waitFor(`document.querySelectorAll('.mosaic-tile').length===6`);
  await click('#practiceButton');await click('#practiceQuestion');await click('#practiceReveal');
  await check(`document.getElementById('modal').open`,'The packaged game also opens directly from disk without a web server');
  const missing = requests.filter(request => request.status===404 && !request.url.includes('intentional-missing-test'));
  assert.equal(missing.length,0,'No unintended missing local assets');
  assert.equal(errors.length,0,'No uncaught browser errors');
  fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:results.length,checks:results,requests:requests.length,errors,projectUrl:base},null,2));
  console.log(`Passed ${results.length} real-Chrome checks. Screenshots and report: ${output}`);
}
main().catch(error => {console.error(error);process.exitCode=1;}).finally(async()=>{
  try {await Promise.race([closeBrowser?.(),sleep(1000)]);}catch{}
  try {if(ws?.readyState===1) ws.close();}catch{}
  if(chrome) chrome.kill();
  if(server) server.close();
});
