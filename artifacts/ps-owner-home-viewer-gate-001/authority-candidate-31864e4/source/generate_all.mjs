import fs from 'node:fs';
import path from 'node:path';
import {
  C, esc, rect, text, linesText, line, pill, fixturePill, svgRoot,
  setAtmosphereImage,
  desktopScreen, mobileScreen, reflow200Evidence, highContrastEvidence,
  reducedMotionEvidence, loadingEvidence, partialFailureEvidence,
  completeFailureEvidence, staleEvidence, restrictedEvidence, recoveryEvidence,
  finiteBudgetEvidence, accessLifecycleEvidence
} from './design_system.mjs';

const here=path.dirname(new URL(import.meta.url).pathname);
const root=path.dirname(here);
const out=path.join(root,'exports');
fs.mkdirSync(out,{recursive:true});

setAtmosphereImage('../assets/owner-home-alpine-atmosphere.png');

const files={
  '01-owner-home-desktop-current.svg':desktopScreen({future:false,owner:'Member',initials:'M'}),
  '02-owner-home-desktop-maximum-future-fixture-a.svg':desktopScreen({future:true,owner:'Avery Morgan',initials:'AM'}),
  '03-owner-home-mobile-current-390.svg':mobileScreen({w:390,future:false,owner:'Member',initials:'M'}),
  '04-owner-home-mobile-future-fixture-b-390.svg':mobileScreen({w:390,future:true,owner:'Samira Patel',initials:'SP'}),
  '05-owner-home-mobile-current-320.svg':mobileScreen({w:320,future:false,owner:'Member',initials:'M'}),
  '06-owner-home-mobile-future-fixture-b-320.svg':mobileScreen({w:320,future:true,owner:'Samira Patel',initials:'SP'}),
  '07-owner-home-200-percent-reflow.svg':reflow200Evidence(),
  '08-owner-home-long-content-fixture-b.svg':desktopScreen({future:true,owner:'Alexandria-Mae Fernández-Singh',initials:'AF',long:true,evidenceNote:'LONG CONTENT · BIDI · MISSING MEDIA FALLBACK'}),
  '09-owner-home-visible-focus.svg':desktopScreen({future:false,owner:'Member',initials:'M',focused:true,evidenceNote:'VISIBLE FOCUS · CAPTURE · 3 PX MARIGOLD + SEPARATION EDGE'}),
  '10-owner-home-high-contrast.svg':highContrastEvidence(),
  '11-owner-home-reduced-motion.svg':reducedMotionEvidence(),
  '12-owner-home-loading.svg':loadingEvidence(),
  '13-owner-home-empty.svg':desktopScreen({future:false,owner:'Member',initials:'M',evidenceNote:'EMPTY HOME · NO FABRICATED RECORDS · CAPTURE REMAINS AVAILABLE'}),
  '14-owner-home-partial-failure.svg':partialFailureEvidence(),
  '15-owner-home-complete-failure.svg':completeFailureEvidence(),
  '16-owner-home-stale.svg':staleEvidence(),
  '17-owner-home-restricted.svg':restrictedEvidence(),
  '18-owner-home-recovery.svg':recoveryEvidence(),
  '19-owner-home-finite-nine-object-evidence.svg':finiteBudgetEvidence(),
  '22-owner-home-access-lifecycle-evidence.svg':accessLifecycleEvidence(),
  '23-owner-home-orientation-landscape-current-844.svg':mobileScreen({w:844,future:false,owner:'Member',initials:'M'})
};

for(const [name,svg] of Object.entries(files))fs.writeFileSync(path.join(out,name),svg);

function dataUrl(file,mime){return `data:${mime};base64,${fs.readFileSync(file).toString('base64')}`;}

function authorityReferenceDataUrl(){
  const supplied=path.resolve(root,'../upload/01_owner_home_interface_mockup(1).png');
  if(fs.existsSync(supplied))return dataUrl(supplied,'image/png');
  const existing=path.join(out,'20-owner-home-authority-comparison.svg');
  if(fs.existsSync(existing)){
    const encoded=fs.readFileSync(existing,'utf8').match(/<image href="(data:image\/png;base64,[^"]+)" x="58"/);
    if(encoded)return encoded[1];
  }
  throw new Error('The binding authority may only be sourced from the supplied attachment or the existing side-by-side comparison export.');
}

function authorityComparison(){
  const authority=authorityReferenceDataUrl();
  const atmosphere=dataUrl(path.join(root,'assets','owner-home-alpine-atmosphere.png'),'image/png');
  const proposedSource=fs.readFileSync(path.join(out,'01-owner-home-desktop-current.svg'),'utf8').replaceAll('href="../assets/owner-home-alpine-atmosphere.png"',`href="${atmosphere}"`);
  const proposed=`data:image/svg+xml;base64,${Buffer.from(proposedSource).toString('base64')}`;
  let s=rect(0,0,1920,1180,'#071421');
  s+=text(54,54,'UPDATED AUTHORITY COMPARISON',9,C.paleGold,750,'Arial','start',1.7);
  s+=text(54,104,'Same cinematic promise. Native editable reconstruction.',38,C.cloud,500,'Georgia');
  s+=text(54,134,'The reference board appears only here. The proposed screen contains no authority-board underlay, phone crop, paint-over layer, or flattened UI.',10,'#B8C2CB',400,'Arial');
  s+=text(54,184,'BINDING VISUAL AUTHORITY',8,C.paleGold,750,'Arial','start',1.1)+text(996,184,'PROPOSED EDITABLE RECONSTRUCTION · IN REVIEW',8,C.paleGold,750,'Arial','start',1.1);
  s+=rect(48,198,884,498,'#04080C','#395269',1.2,16)+`<image href="${authority}" x="58" y="208" width="864" height="478" preserveAspectRatio="xMidYMid meet"/>`;
  s+=rect(986,198,886,498,'#04080C','#395269',1.2,16)+`<image href="${proposed}" x="996" y="208" width="866" height="478" preserveAspectRatio="xMidYMid meet"/>`;
  const rows=[
    ['Recognizable shell and cinematic atmosphere','Preserved with a separate, independently generated alpine atmosphere component'],
    ['Owner orientation and private context','Preserved; identity is variable, not Pete-specific'],
    ['Capture placement and dominance','Preserved; only dominant active action'],
    ['Ivory working stage','Preserved as one continuous light-first stage'],
    ['Unequal editorial hierarchy','Preserved across Review / Recent / Resurfaced and three distinct lower materials'],
    ['Dormant capabilities','Integrated production-quality components with full Coming later labels'],
    ['My Slate and audience context','Readable shell rail; Owner View separated from disabled preview modes'],
    ['Finite content contract','Maximum fixture proves exactly 9 objects and one bounded remainder path'],
    ['Mobile behavior','Reconstructed as native 390 px and 320 px full-scroll screens'],
    ['Editable construction','UI surfaces, type, controls, icons, and states are vectors; alpine atmosphere is a separate replaceable image component'],
    ['Typography and material hierarchy','Editorial serif, restrained sans, glass, paper, dark insight, quiet relationship, and warm action surfaces'],
    ['Accessibility and state depth','Named 320 px, 200% reflow, long-content, focus, contrast, reduced-motion, loading, failure, stale, restricted, and recovery evidence']
  ];
  let y=728;
  rows.forEach((r,i)=>{s+=rect(54,y,1812,28,i%2?'#0C1A27':'#102131','#29445A',.8,5)+text(72,y+19,r[0],8.5,'#D6DEE5',600,'Arial')+text(994,y+19,r[1],8.5,i<5?C.paleGold:'#B9D7CC',650,'Arial');y+=31;});
  s+=text(54,1137,'VISUAL AUTHORITY STATUS: IN REVIEW · CONDITIONAL · NO IMPLEMENTATION AUTHORIZATION',8,C.paleGold,750,'Arial','start',1);
  s+=text(1866,1137,'ORIGINAL BOARD EMBEDDED ONLY IN THIS COMPARISON',8,'#9FAAB4',700,'Arial','end',.8);
  return svgRoot(1920,1180,'Owner Home updated authority comparison','Side-by-side binding visual authority and native editable reconstruction with measurable preservation rows.',s);
}

function statusBoundary(){
  let s=rect(0,0,1440,900,'url(#bgNavy)');
  s+=text(54,56,'STATUS AND CLAIM BOUNDARY',9,C.paleGold,750,'Arial','start',1.6)+text(54,108,'What this package is—and is not.',38,C.cloud,500,'Georgia');
  s+=text(54,138,'Every review artifact must preserve these distinctions.',10,'#B8C2CB',400,'Arial');
  const states=[
    ['VISUAL DESIGN','Editable proposed component reconstruction','IN REVIEW',C.marigold],
    ['FIXTURE','Generic test data; explicitly not member data','DEMONSTRATION',C.paleGold],
    ['FUTURE CAPABILITY','Visible production-quality silhouette; disabled; Coming later','NOT AVAILABLE','#B7C6D2'],
    ['IMPLEMENTATION','No application code, route, DOM behavior, request, or backend change','NOT PERFORMED','#D8B4AC'],
    ['DEPLOYMENT','No pipeline, environment, release, or production asset','NOT PERFORMED','#D8B4AC'],
    ['LIVE PRODUCTION','No claim that Owner Home, viewer modes, My Slate preview, insight, or connections are live','NO CLAIM','#D8B4AC']
  ];
  states.forEach((r,i)=>{const cx=54+(i%2)*666,cy=190+Math.floor(i/2)*192;s+=rect(cx,cy,636,164,i===0?'#10283B':i===1?'#F2E4BC':'#0C1B28',i===1?'#B9964B':'#344F65',1.2,16);s+=text(cx+22,cy+34,r[0],8,i===1?C.goldSafe:C.paleGold,750,'Arial','start',1.1)+linesText(cx+22,cy+74,r[1].match(/.{1,62}(?:\s|$)/g)?.map(v=>v.trim())||[r[1]],14,i===1?C.ink:C.cloud,600,'Georgia',19)+pill(cx+22,cy+116,r[2],{fill:i===1?'#FFF9EA':'#142A3C',stroke:r[3],ink:i===1?C.goldSafe:r[3],w:170,h:30,size:8});});
  s+=rect(54,792,1332,62,'#0B1824','#725A30',1,14)+text(76,819,'Homepage impact',9,C.paleGold,750,'Arial')+text(76,842,'No direct Owner Home homepage projection is currently identified; implementation must reassess this before release.',10,C.cloud,600,'Arial');
  return svgRoot(1440,900,'Owner Home status and claim boundary','Visual design, fixtures, future capability, implementation, deployment, live production, and homepage impact distinctions.',s);
}

fs.writeFileSync(path.join(out,'20-owner-home-authority-comparison.svg'),authorityComparison());
fs.writeFileSync(path.join(out,'21-owner-home-status-and-homepage-impact.svg'),statusBoundary());

console.log(`Wrote ${Object.keys(files).length+2} editable SVG review artifacts.`);
