export const C = {
  ink: '#151820',
  navy: '#071421',
  navy2: '#0D2133',
  navy3: '#183249',
  cloud: '#FFFDF8',
  ivory: '#F5F0E7',
  paper: '#FBF8F2',
  paper2: '#ECE4D8',
  line: '#D6CDBF',
  lineDark: '#31485D',
  gold: '#B87900',
  goldSafe: '#8A5A00',
  marigold: '#D9AA2B',
  paleGold: '#F2D992',
  warm: '#E9D39D',
  muted: '#666B70',
  mutedDark: '#B7C0C9',
  teal: '#1E725F',
  red: '#A43737',
  white: '#FFFFFF',
  black: '#000000'
};

let atmosphereImageHref='';
export function setAtmosphereImage(href='') { atmosphereImageHref=href; }

export const esc = value => String(value).replace(/[&<>"']/g, ch => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'
}[ch]));

export const rect = (x,y,w,h,fill,stroke='none',sw=0,r=0,opacity=1,extra='') =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" opacity="${opacity}" ${extra}/>`;

export const line = (x1,y1,x2,y2,stroke,width=1,opacity=1,dash='') =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}" opacity="${opacity}" ${dash ? `stroke-dasharray="${dash}"` : ''}/>`;

export const circle = (x,y,r,fill='none',stroke='none',sw=0,opacity=1) =>
  `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" opacity="${opacity}"/>`;

export const path = (d,fill='none',stroke='none',sw=0,opacity=1,extra='') =>
  `<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" opacity="${opacity}" ${extra}/>`;

export const text = (x,y,value,size,fill=C.ink,weight=400,family='Arial',anchor='start',spacing=0,extra='') =>
  `<text x="${x}" y="${y}" font-family="${family}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" letter-spacing="${spacing}" ${extra}>${esc(value)}</text>`;

export function linesText(x,y,lines,size,fill=C.ink,weight=400,family='Arial',lineHeight=size*1.35,anchor='start',extra='') {
  return `<text x="${x}" y="${y}" font-family="${family}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" ${extra}>`+
    lines.map((entry,i)=>`<tspan x="${x}" dy="${i===0?0:lineHeight}">${esc(entry)}</tspan>`).join('')+
    `</text>`;
}

export function wrap(value, max=42) {
  const words=String(value).split(/\s+/); const rows=[]; let row='';
  for (const word of words) {
    if (!row) row=word;
    else if ((row+' '+word).length<=max) row+=' '+word;
    else { rows.push(row); row=word; }
  }
  if (row) rows.push(row);
  return rows;
}

export function defs() {
  return `<defs>
    <linearGradient id="bgNavy" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#03080D"/><stop offset=".55" stop-color="#071421"/><stop offset="1" stop-color="#12283B"/></linearGradient>
    <linearGradient id="heroSky" x1="0" y1="0" x2="1" y2=".2"><stop offset="0" stop-color="#050B12"/><stop offset=".55" stop-color="#0B1A28"/><stop offset="1" stop-color="#39434A"/></linearGradient>
    <linearGradient id="heroGlow" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#D9AA2B" stop-opacity="0"/><stop offset=".74" stop-color="#D9AA2B" stop-opacity=".06"/><stop offset="1" stop-color="#F0B340" stop-opacity=".34"/></linearGradient>
    <linearGradient id="copyVeil" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#050B12" stop-opacity=".98"/><stop offset=".68" stop-color="#071421" stop-opacity=".74"/><stop offset="1" stop-color="#071421" stop-opacity=".06"/></linearGradient>
    <linearGradient id="photoVeil" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#050B12" stop-opacity=".98"/><stop offset=".46" stop-color="#071421" stop-opacity=".68"/><stop offset=".78" stop-color="#071421" stop-opacity=".2"/><stop offset="1" stop-color="#071421" stop-opacity=".08"/></linearGradient>
    <linearGradient id="copyZone" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0B1C2A" stop-opacity="1"/><stop offset=".78" stop-color="#0B1C2A" stop-opacity=".96"/><stop offset="1" stop-color="#0B1C2A" stop-opacity="0"/></linearGradient>
    <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#31404D" stop-opacity=".83"/><stop offset=".55" stop-color="#141E28" stop-opacity=".91"/><stop offset="1" stop-color="#080E15" stop-opacity=".96"/></linearGradient>
    <linearGradient id="ivoryStage" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFDF8"/><stop offset="1" stop-color="#EEE7DC"/></linearGradient>
    <linearGradient id="warmPanel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F4E5BA"/><stop offset="1" stop-color="#D9B968"/></linearGradient>
    <linearGradient id="dormantNavy" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#12283A"/><stop offset="1" stop-color="#071421"/></linearGradient>
    <linearGradient id="brandFog" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#20394F" stop-opacity=".1"/><stop offset=".5" stop-color="#D9AA2B" stop-opacity=".2"/><stop offset="1" stop-color="#20394F" stop-opacity=".04"/></linearGradient>
    <radialGradient id="goldOrb"><stop offset="0" stop-color="#F7D77E" stop-opacity=".95"/><stop offset=".38" stop-color="#D9AA2B" stop-opacity=".36"/><stop offset="1" stop-color="#D9AA2B" stop-opacity="0"/></radialGradient>
    <pattern id="quietLines" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(28)"><line x1="0" y1="0" x2="0" y2="18" stroke="#B87900" stroke-opacity=".08" stroke-width="1"/></pattern>
    <filter id="shadow"><feDropShadow dx="0" dy="8" stdDeviation="14" flood-color="#000" flood-opacity=".28"/></filter>
    <filter id="softShadow"><feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#08101A" flood-opacity=".18"/></filter>
    <clipPath id="roundApp"><rect x="40" y="28" width="1360" height="1044" rx="24"/></clipPath>
  </defs>`;
}

export function svgRoot(width,height,titleValue,descValue,body,extraDefs='') {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="svg-title svg-desc">
    <title id="svg-title">${esc(titleValue)}</title>
    <desc id="svg-desc">${esc(descValue)}</desc>
    ${defs()}${extraDefs}${body}
  </svg>`;
}

export function pill(x,y,label,{fill=C.paper,stroke=C.line,ink=C.muted,w=112,h=24,weight=700,size=8}={}) {
  return rect(x,y,w,h,fill,stroke,1,h/2)+text(x+w/2,y+h*.67,label,size,ink,weight,'Arial','middle',.8);
}

export function comingLaterPill(x,y,w=112) {
  return pill(x,y,'COMING LATER',{fill:'#F8F3E8',stroke:'#C8A968',ink:C.goldSafe,w,h:26,size:9});
}

export function fixturePill(x,y,w=104,label='TEST FIXTURE') {
  return pill(x,y,label,{fill:'#F2DFAB',stroke:'#BE9131',ink:C.goldSafe,w,h:24,size:9});
}

export function iconCamera(x,y,size=28,stroke=C.paleGold) {
  return rect(x,y+4,size,size-7,'none',stroke,1.8,6)+circle(x+size/2,y+size/2,5,'none',stroke,1.8)+rect(x+7,y,size/3,7,'none',stroke,1.6,2);
}

export function iconDocument(x,y,size=28,stroke=C.goldSafe) {
  return path(`M${x+6} ${y+2}h${size-14}l8 8v${size-6}H${x+6}z`,'none',stroke,1.6,1,'stroke-linejoin="round"')+
    path(`M${x+size-8} ${y+2}v9h8`,'none',stroke,1.3)+line(x+11,y+16,x+size-7,y+16,stroke,1.2)+line(x+11,y+22,x+size-7,y+22,stroke,1.2);
}

export function iconLink(x,y,size=28,stroke=C.goldSafe) {
  return circle(x+9,y+14,7,'none',stroke,1.8)+circle(x+size-9,y+14,7,'none',stroke,1.8)+line(x+12,y+14,x+size-12,y+14,stroke,1.8);
}

export function iconSpark(x,y,size=28,stroke=C.goldSafe) {
  return path(`M${x+size/2} ${y}l3.2 ${size/2-4}L${x+size} ${y+size/2}l-${size/2-4} 3.2L${x+size/2} ${y+size}l-3.2-${size/2-4}L${x} ${y+size/2}l${size/2-4}-3.2z`,'none',stroke,1.6);
}

export function iconRefresh(x,y,size=24,stroke=C.goldSafe) {
  return path(`M${x+size-4} ${y+8}a${size/2-4} ${size/2-4} 0 1 0 1 10M${x+size-4} ${y+8}v-6m0 6h-6`,'none',stroke,1.8,1,'stroke-linecap="round" stroke-linejoin="round"');
}

export function focusRing(x,y,w,h,r=12) {
  return rect(x-5,y-5,w+10,h+10,'none','#FFD75E',4,r+5)+rect(x-9,y-9,w+18,h+18,'none','#071421',2,r+9);
}

export function cinematicAtmosphere(x,y,w,h,{light=false,accent=true}={}) {
  const sky=light?'#DCE5EA':'url(#heroSky)';
  let s=`<g data-component="cinematic-atmosphere">${rect(x,y,w,h,sky)}`;
  if(atmosphereImageHref&&!light){
    const fit='xMidYMid slice';
    s+=`<image data-component="independent-alpine-atmosphere" href="${atmosphereImageHref}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="${fit}"/>`;
    s+=rect(x,y,w,h,'url(#photoVeil)');
    s+=rect(x,y,w,h,'url(#heroGlow)');
    s+='</g>';
    return s;
  }
  s+=rect(x,y,w,h,'url(#heroGlow)');
  const base=y+h;
  s+=path(`M${x} ${base-24} L${x+w*.12} ${base-78} L${x+w*.2} ${base-56} L${x+w*.31} ${base-134} L${x+w*.39} ${base-83} L${x+w*.48} ${base-162} L${x+w*.55} ${base-94} L${x+w*.66} ${base-188} L${x+w*.75} ${base-102} L${x+w*.86} ${base-153} L${x+w} ${base-66} L${x+w} ${base} L${x} ${base} Z`,light?'#8A969E':'#263746','none',0,.72);
  s+=path(`M${x} ${base-2} L${x+w*.16} ${base-102} L${x+w*.25} ${base-62} L${x+w*.39} ${base-151} L${x+w*.48} ${base-66} L${x+w*.62} ${base-134} L${x+w*.7} ${base-70} L${x+w*.86} ${base-123} L${x+w} ${base-38} L${x+w} ${base} Z`,light?'#5E6C75':'#122332','none',0,.9);
  s+=path(`M${x} ${base} L${x+w*.22} ${base-84} L${x+w*.34} ${base-28} L${x+w*.52} ${base-116} L${x+w*.63} ${base-32} L${x+w*.8} ${base-88} L${x+w} ${base-12} L${x+w} ${base} Z`,light?'#35434D':'#071421','none',0,1);
  if(accent){
    s+=path(`M${x+w*.47} ${base-161}l${w*.02} -18 l${w*.025} 27 l${w*.026} 14`, 'none', C.marigold, 2.4, .88, 'stroke-linecap="round"');
    s+=path(`M${x+w*.655} ${base-187}l${w*.019} -18 l${w*.02} 24`, 'none', C.marigold, 2.1, .76, 'stroke-linecap="round"');
  }
  s+=rect(x,y,w,h,'url(#brandFog)','none',0,0,.8);
  s+='</g>'; return s;
}

export function brandMaterial(x,y,w,h,{dark=true,seed=0}={}) {
  let s=`<g data-component="brand-material">${rect(x,y,w,h,dark?'url(#dormantNavy)':'#EFE6D7','none',0,12)}`;
  s+=rect(x,y,w,h,'url(#quietLines)','none',0,12,.7);
  const stroke=dark?C.paleGold:C.goldSafe;
  for(let i=0;i<4;i++){
    const yy=y+h*(.28+i*.16);
    s+=path(`M${x-20} ${yy} C${x+w*.2} ${yy-35-seed*2}, ${x+w*.48} ${yy+40+i*3}, ${x+w+20} ${yy-8}`, 'none', stroke, 1+i*.15, .2+i*.08, 'stroke-linecap="round"');
  }
  for(let i=0;i<16;i++){
    const px=x+w*(.52+((i*37+seed*13)%47)/100);
    const py=y+h*(.18+((i*23+seed*7)%62)/100);
    s+=circle(px,py,1+(i%3)*.45,stroke,'none',0,.28+(i%4)*.1);
  }
  s+=circle(x+w*.72,y+h*.45,Math.min(w,h)*.35,'url(#goldOrb)','none',0,.34);
  s+='</g>'; return s;
}

export function relationshipMaterial(x,y,w,h) {
  let s=`<g data-component="abstract-relationship-material" aria-hidden="true">`;
  s+=rect(x,y,w,h,'url(#quietLines)','none',0,12,.8);
  s+=circle(x+w*.78,y+h*.48,Math.min(w,h)*.32,'url(#goldOrb)','none',0,.22);
  s+=path(`M${x+w*.48} ${y+h*.22} C${x+w*.62} ${y+h*.08},${x+w*.76} ${y+h*.12},${x+w*.91} ${y+h*.3}`,'none','#A87925',1.5,.28,'stroke-linecap="round"');
  s+=path(`M${x+w*.42} ${y+h*.7} C${x+w*.58} ${y+h*.48},${x+w*.78} ${y+h*.5},${x+w*.94} ${y+h*.7}`,'none','#A87925',1.5,.24,'stroke-linecap="round"');
  s+='</g>';return s;
}

export function fixtureArtwork(x,y,w,h,{variant='city'}={}) {
  let s=`<g data-component="fixture-artwork">${rect(x,y,w,h,'url(#dormantNavy)','none',0,12)}`;
  if(variant==='missing-media'){
    s+=rect(x+12,y+12,w-24,h-24,'#102536','#49647A',1.2,10);
    s+=iconDocument(x+w/2-20,y+h/2-48,40,C.paleGold);
    s+=text(x+w/2,y+h/2+18,'NO OPTIONAL MEDIA',11,C.cloud,800,'Arial','middle',.4);
    s+=text(x+w/2,y+h/2+42,'Text remains the primary content',9,'#C8D1D8',600,'Arial','middle');
  } else if(variant.startsWith('editorial-')&&atmosphereImageHref){
    const fit=variant==='editorial-ridge'?'xMaxYMid slice':'xMidYMid slice';
    s+=`<image data-component="generic-fixture-editorial-image" href="${atmosphereImageHref}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="${fit}"/>`;
    s+=rect(x,y,w,h,'#071421','none',0,12,.28);
    s+=text(x+16,y+h-14,'GENERIC TEST FIXTURE IMAGE',8,C.paleGold,800,'Arial','start',.55);
  } else if(variant==='city'){
    const widths=[.08,.12,.07,.1,.09,.13,.08,.11]; let cx=x+w*.04;
    widths.forEach((ratio,i)=>{const bw=w*ratio,bh=h*(.28+((i*17)%35)/100);s+=rect(cx,y+h-bh-14,bw,bh,'#1B3347','#3A566C',1,2);for(let r=0;r<3;r++)s+=rect(cx+bw*.22,y+h-bh+12+r*16,bw*.18,4,C.marigold,'none',0,1,.75);cx+=bw+w*.014;});
    s+=line(x+12,y+h-14,x+w-12,y+h-14,C.marigold,2,.7);
  } else if(variant==='path'){
    s+=path(`M${x+w*.06} ${y+h*.86} C${x+w*.31} ${y+h*.7},${x+w*.44} ${y+h*.48},${x+w*.72} ${y+h*.28}`,'none',C.paleGold,5,.8,'stroke-linecap="round"');
    s+=path(`M${x+w*.64} ${y+h*.3}l0 -32 l32 10 l-32 11`,'none',C.marigold,2,1,'stroke-linejoin="round"');
  } else {
    s+=path(`M${x+w*.08} ${y+h*.78} L${x+w*.34} ${y+h*.38} L${x+w*.5} ${y+h*.61} L${x+w*.72} ${y+h*.22} L${x+w*.94} ${y+h*.78} Z`,'#1B3347','#456179',1.4,.95);
    s+=circle(x+w*.75,y+h*.2,18,'url(#goldOrb)');
  }
  s+='</g>';return s;
}

export function ownerAvatar(x,y,r,label='M',fixture=false) {
  let s=`<g data-component="owner-avatar">${circle(x,y,r,fixture?'#20384B':'#142A3C','#8B7955',2)}`;
  s+=circle(x-r*.24,y-r*.16,r*.22,'none',C.paleGold,1.8);
  s+=path(`M${x-r*.48} ${y+r*.42}q${r*.48} -${r*.56} ${r*.96} 0`,'none',C.paleGold,1.8,1,'stroke-linecap="round"');
  s+=text(x,y+r*.08,label,fixture?0:1,'transparent',400,'Arial','middle');
  s+='</g>'; return s;
}

export function logo(x,y,{dark=true,size=28}={}) {
  return `<g data-component="brand-logo">${text(x,y,'PeerSlate',size,dark?C.cloud:C.navy,500,'Georgia')}${line(x,y+10,x+54,y+10,C.marigold,2,.8)}</g>`;
}

export function navItem(x,y,label,{disabled=false,current=false,w=92}={}) {
  let s=`<g data-component="nav-item" data-state="${disabled?'disabled':current?'context':'available'}" ${disabled?'aria-disabled="true" pointer-events="none"':''}>`;
  if(current) s+=rect(x,y,w,48,'#101E2B','none',0,10,.72);
  s+=text(x+w/2,y+19,label,12,disabled?'#C4C8CC':C.cloud,current?700:500,'Arial','middle');
  if(disabled) s+=text(x+w/2,y+38,'COMING LATER',9,C.paleGold,700,'Arial','middle',.18);
  if(current) s+=text(x+w/2,y+38,'CURRENT CONTEXT',9,C.paleGold,700,'Arial','middle',.18);
  s+='</g>';return s;
}

export function desktopNav({fixture=false}={}) {
  let s=`<g data-component="desktop-navigation">${rect(40,28,1360,74,'#070C12','#3A4650',1,24,.98)}`;
  s+=logo(72,73,{dark:true,size:28});
  s+=pill(248,50,'OWNER VIEW',{fill:'#0E1924',stroke:'#6E5A33',ink:C.paleGold,w:122,h:30,size:9});
  s+=navItem(590,42,'Home',{current:true,w:92});
  s+=navItem(686,42,'Journal',{disabled:true,w:105});
  s+=navItem(795,42,'My Slate',{disabled:true,w:104});
  s+=navItem(903,42,'Connections',{disabled:true,w:124});
  s+=navItem(1031,42,'More',{disabled:true,w:88});
  s+=pill(1150,49,fixture?'TEST FIXTURE':'DESIGN ONLY',{fill:fixture?'#2E2518':'#111B25',stroke:fixture?'#9B7427':'#435264',ink:fixture?C.paleGold:'#B8C1CB',w:110,h:30,size:9});
  s+=text(1280,62,'Owner menu',10,C.cloud,600,'Arial')+text(1280,79,'Settings foundation',8.5,'#B8C1C9',400,'Arial');
  s+='</g>';return s;
}

export function mobileTopBar(w,{fixture=false}={}) {
  let s=`<g data-component="mobile-top-bar">${rect(0,0,w,72,'#070C12','none',0,0,1)}`;
  s+=logo(20,43,{dark:true,size:w<=320?23:26});
  s+=pill(w-132,20,fixture?'TEST FIXTURE':'OWNER VIEW',{fill:fixture?'#2E2518':'#101A24',stroke:'#7A6132',ink:C.paleGold,w:112,h:30,size:9});
  s+='</g>';return s;
}

export function capturePanel(x,y,w,h,{focused=false,compact=false}={}) {
  let s=`<g data-component="capture-action" data-availability="available">`;
  if(focused) s+=focusRing(x,y,w,h,16);
  s+=rect(x,y,w,h,'url(#glass)','#8B754B',1.2,16,1,'filter="url(#softShadow)"');
  const iconBox=compact?48:62;
  s+=rect(x+16,y+(h-iconBox)/2,iconBox,iconBox,'#4A3A24','#8C7041',1,12,.98);
  s+=iconCamera(x+16+(iconBox-30)/2,y+(h-30)/2,30,C.paleGold);
  const tx=x+32+iconBox;
  s+=text(tx,y+(compact?30:39),'Capture a Moment',compact?17:21,C.cloud,600,'Georgia');
  s+=text(tx,y+(compact?51:65),'Protected private Capture',compact?11:12,'#DCE2E6',500,'Arial');
  if(!compact)s+=text(tx,y+84,'Speak or Type continues in the existing flow.',10,'#BEC7CF',400,'Arial');
  s+=text(x+w-30,y+h/2+6,'→',compact?24:30,C.paleGold,400,'Arial','middle');
  s+='</g>';return s;
}

export function ownerHero({fixture=false,owner='Member',initials='M',focused=false}={}) {
  let s=`<g data-component="owner-hero">${cinematicAtmosphere(40,96,1360,250)}`;
  s+=ownerAvatar(112,194,48,initials,fixture);
  const ownerSize=owner.length>22?26:(fixture?31:34);
  s+=text(178,179,`Welcome back, ${owner}.`,ownerSize,C.cloud,500,'Georgia');
  s+=text(178,207,'Owner Home · private workspace',12,C.paleGold,700,'Arial');
  s+=text(178,232,'Capture what matters. Return to a finite set of meaningful work.',11,'#CCD3D9',400,'Arial');
  s+=text(178,255,'Viewing this design did not publish, share, connect, or save anything.',10,'#BCC5CD',400,'Arial');
  if(fixture) s+=pill(500,248,'FUTURE DESIGN FIXTURE · NOT MEMBER DATA',{fill:'#302516',stroke:'#A9791C',ink:C.paleGold,w:290,h:28,size:9});
  s+=capturePanel(988,140,360,126,{focused});
  s+='</g>';return s;
}

export function audienceRail(x,y,w,{fixture=false,mobile=false}={}) {
  const narrow=mobile&&w<330;
  const h=mobile?252:112;
  let s=`<g data-component="my-slate-audience-shell" data-availability="coming-later" aria-label="My Slate preview — coming later. Viewer preview modes are not yet available.">`;
  s+=rect(x,y,w,h,'#0B1824','#725A30',1.2,16,.98,'filter="url(#softShadow)"');
  s+=text(x+20,y+28,'My Slate preview',mobile?(narrow?14.5:16):15,C.cloud,600,'Georgia');
  s+=comingLaterPill(mobile?x+w-(narrow?128:146):x+180,y+10,mobile?(narrow?108:126):116);
  if(mobile){
    s+=linesText(x+20,y+62,wrap('Owner View is the current private workspace context—not a viewer preview.',narrow?44:62).slice(0,2),narrow?9.5:10.5,'#CBD2D8',400,'Arial',narrow?13.5:14.5);
    s+=text(x+20,y+95,'Viewer modes below are approved future capabilities.',narrow?9.5:10.5,'#CBD2D8',400,'Arial');
  }else{
    s+=text(x+20,y+53,'Owner View is the current private workspace context—not a viewer preview.',9,'#BDC6CE',400,'Arial');
  }
  const labels=['SELECTED PERSON','CONNECTION','AUTHENTICATED MEMBER','PUBLIC'];
  if(mobile){
    const narrow=w<330;
    const ownerBarY=y+110,previewY=y+174;
    s+=rect(x+20,ownerBarY,w-40,36,'#D9AA2B','#F0D17B',1,18)+text(x+w/2,ownerBarY+14,'OWNER VIEW',9,C.navy,800,'Arial','middle',.3)+text(x+w/2,ownerBarY+28,'CURRENT PRIVATE CONTEXT · NOT A PREVIEW MODE',narrow?8.2:8.8,C.navy,750,'Arial','middle',.06);
    s+=text(x+20,previewY-10,'PREVIEW AS',9,C.paleGold,750,'Arial','start',.4);
    const chipW=(w-48)/2,positions=[[x+20,previewY],[x+28+chipW,previewY],[x+20,previewY+40],[x+28+chipW,previewY+40]];
    labels.forEach((label,i)=>{
      const [cx,cy]=positions[i],cw=chipW;
      s+=`<g data-capability="viewer-preview" aria-disabled="true" pointer-events="none">`;
      s+=rect(cx,cy,cw,32,'#142A3C','#36516A',1,16,.94);
      s+=text(cx+cw/2,cy+12,label,narrow?8.8:9.2,'#E0E5E9',750,'Arial','middle',.04);
      s+=text(cx+cw/2,cy+25,'COMING LATER',narrow?8.5:9,C.paleGold,700,'Arial','middle',.04);
      s+='</g>';
    });
  }else{
    s+=rect(x+20,y+68,196,30,'#D9AA2B','#F0D17B',1,15)+text(x+118,y+80,'OWNER VIEW',9,C.navy,800,'Arial','middle',.3)+text(x+118,y+92,'CURRENT PRIVATE CONTEXT',8.5,C.navy,750,'Arial','middle',.08);
    s+=text(x+235,y+86,'PREVIEW AS',9,C.paleGold,750,'Arial','start',.4);
    const widths=[150,118,154,88]; let cx=x+305;
    labels.forEach((label,i)=>{
      const cw=widths[i];
      s+=`<g data-capability="viewer-preview" aria-disabled="true" pointer-events="none">`;
      s+=rect(cx,y+68,cw,30,'#142A3C','#36516A',1,15,.92);
      s+=text(cx+cw/2,y+80,label,9,'#D5DBE1',750,'Arial','middle',.12);
      s+=text(cx+cw/2,y+92,'COMING LATER',9,C.paleGold,700,'Arial','middle',.06);
      s+='</g>';
      cx+=cw+10;
    });
  }
  if(!mobile)s+=text(x+w-18,y+101,'Shell context · not a Home content object',8.5,'#A9B3BC',600,'Arial','end',.2);
  s+='</g>';return s;
}

export function sectionHeading(x,y,title,{subtitle='',right='',dark=false}={}) {
  let s=`<g data-component="section-heading">${text(x,y,title,16,dark?C.cloud:C.ink,600,'Georgia')}`;
  if(subtitle)s+=text(x,y+21,subtitle,9.5,dark?'#BFC8D0':C.muted,400,'Arial');
  if(right)s+=text(x+right.x,y,right.label,9,dark?C.paleGold:C.goldSafe,700,'Arial','end',.3);
  s+='</g>';return s;
}

export function dormantCard(x,y,w,h,{title,purpose,theme='ivory',icon='spark',seed=0,compact=false}={}) {
  const dark=theme==='dark',warm=theme==='warm';
  const fill=dark?'url(#dormantNavy)':warm?'url(#warmPanel)':C.paper;
  const stroke=dark?C.lineDark:warm?'#C4A04E':C.line;
  const ink=dark?C.cloud:C.ink,muted=dark?'#BEC7CF':'#666B70';
  let s=`<g data-component="capability-preview" data-availability="coming-later" aria-disabled="true" pointer-events="none" aria-label="${esc(title)} - coming later. Not yet available.">`;
  s+=rect(x,y,w,h,fill,stroke,1,14,1,'filter="url(#softShadow)"');
  if(dark)s+=brandMaterial(x,y,w,h,{dark:true,seed});
  else if(icon==='link')s+=relationshipMaterial(x,y,w,h);
  else s+=rect(x,y,w,h,'url(#quietLines)','none',0,14,.8);
  const ix=x+20,iy=y+20;
  if(icon==='document')s+=iconDocument(ix,iy,30,dark?C.paleGold:C.goldSafe);
  else if(icon==='link')s+=iconLink(ix,iy,30,dark?C.paleGold:C.goldSafe);
  else s+=iconSpark(ix,iy,30,dark?C.paleGold:C.goldSafe);
  if(compact){
    const titleSize=title.length>=22?11.5:13;
    s+=text(x+64,y+31,title,titleSize,ink,600,'Georgia');
    s+=comingLaterPill(x+64,y+43,112);
    const rows=wrap(purpose,Math.max(24,Math.floor((w-84)/6))).slice(0,4);
    s+=linesText(x+64,y+82,rows,11,muted,400,'Arial',15);
  }else{
    const titleSize=title.length>=20?11.5:15;
    s+=text(x+64,y+32,title,titleSize,ink,600,'Georgia');
    s+=comingLaterPill(x+w-128,y+16,112);
    const rows=wrap(purpose,58).slice(0,3);
    s+=linesText(x+64,y+56,rows,11,muted,400,'Arial',15.5);
  }
  s+=text(x+20,y+h-16,compact?'Not available · no member record or result':'Not yet available · no member record or generated result',9.5,dark?'#B9C3CB':'#555C61',600,'Arial');
  s+='</g>';return s;
}

export function emptyLiveCard(x,y,w,h,{title,message,purpose,theme='ivory',icon='document',seed=0,compact=false}={}) {
  const dark=theme==='dark',fill=dark?'url(#dormantNavy)':C.paper,stroke=dark?C.lineDark:C.line,ink=dark?C.cloud:C.ink,muted=dark?'#BEC7CF':C.muted;
  const editorialEmpty=!dark&&icon==='document'&&w>=400;
  let s=`<g data-component="live-category-empty" data-state="empty">${rect(x,y,w,h,fill,stroke,1,14,1,'filter="url(#softShadow)"')}`;
  if(dark)s+=brandMaterial(x,y,w,h,{dark:true,seed});
  else {
    s+=rect(x,y,w,h,'url(#quietLines)','none',0,14,.8);
    if(editorialEmpty){
      const ax=x+w*.73,aw=w*.27;
      s+=brandMaterial(ax,y,aw,h,{dark:true,seed:seed+2});
      s+=iconDocument(ax+aw/2-22,y+h/2-22,44,C.paleGold);
    }
  }
  if(icon==='document')s+=iconDocument(x+20,y+20,30,dark?C.paleGold:C.goldSafe); else s+=iconSpark(x+20,y+20,30,dark?C.paleGold:C.goldSafe);
  s+=text(x+64,y+32,title,compact?15:16,ink,600,'Georgia');
  s+=pill(x+w-96,y+16,'EMPTY',{fill:dark||editorialEmpty?'#152A3C':'#F3EEE6',stroke:dark||editorialEmpty?'#466077':C.line,ink:dark||editorialEmpty?'#E1E6EA':C.muted,w:80,h:24,size:9});
  const messageWrap=compact?Math.max(22,Math.floor((w-84)/7)):(editorialEmpty?28:52);
  const purposeWrap=compact?Math.max(22,Math.floor((w-84)/6.5)):(editorialEmpty?38:56);
  s+=linesText(x+64,y+64,wrap(message,messageWrap).slice(0,3),compact?12:13,ink,600,'Georgia',compact?16:18);
  s+=linesText(x+64,y+112,wrap(purpose,purposeWrap).slice(0,3),11,muted,400,'Arial',15.5);
  s+=text(x+20,y+h-16,compact||editorialEmpty?'No member record, count, timestamp, or media':'No fixture record, count, timestamp, or member media is shown',9.5,dark?'#B9C3CB':'#555C61',600,'Arial');
  s+='</g>';return s;
}

export function currentNextCard(x,y,w,h,{compact=false}={}) {
  const narrow=w<330;
  let s=`<g data-component="next-useful-step" data-state="current">${rect(x,y,w,h,'url(#warmPanel)','#C29E4A',1,14)}`;
  s+=fixtureArtwork(x+w*.58,y,w*.42,h,{variant:'path'});
  s+=linesText(x+20,y+29,wrap('Your next useful step',narrow?13:26),compact?12.5:15,C.ink,600,'Georgia',compact?15:18);
  s+=pill(x+w-102,y+16,'AVAILABLE',{fill:'#FBF4DF',stroke:'#B48D34',ink:C.goldSafe,w:86,h:24,size:9});
  s+=linesText(x+20,y+78,wrap('Start a private Capture',compact?19:21).slice(0,2),compact?15:17,C.ink,600,'Georgia',compact?18:21);
  s+=linesText(x+20,y+(compact?118:126),wrap('Capture is the only available next step in this state. Use the dominant action above.',compact?(narrow?22:28):44).slice(0,compact?4:3),11,'#514A3E',400,'Arial',15.5);
  if(compact)s+=linesText(x+20,y+h-34,wrap('No automatic save, share, or publication',narrow?22:30).slice(0,2),9.5,C.goldSafe,700,'Arial',13);
  else s+=text(x+20,y+h-18,'No automatic save, share, or publication',9.5,C.goldSafe,700,'Arial');
  s+='</g>';return s;
}

export function reviewFixtureRow(x,y,w,{title,status='Private draft',long=false,index=1}={}) {
  const narrow=w<340,rowH=long?102:(narrow?76:68);
  let s=`<g data-component="review-item" data-fixture="true">${rect(x,y,w,rowH,C.paper,C.line,1,12)}`;
  s+=rect(x+12,y+12,44,44,'#201A12','#806633',1,10)+iconDocument(x+20,y+20,26,C.paleGold);
  const titleRows=wrap(title,long?29:(narrow?25:42)).slice(0,long?4:(narrow?2:1));
  s+=linesText(x+68,y+24,titleRows,long||narrow?11.5:12,C.ink,600,'Georgia',long||narrow?13.5:15);
  s+=text(x+68,y+rowH-10,narrow?`${status} · Fixture ${index}`:`${status} · Test fixture ${index}`,9.5,C.goldSafe,700,'Arial');
  s+=fixturePill(x+w-(narrow?82:104),y+rowH-29,narrow?70:92,'FIXTURE');
  s+='</g>';return s;
}

export function momentFixtureCard(x,y,w,h,{title,summary,variant='city',resurfaced=false,long=false}={}) {
  const narrow=w<330;
  let s=`<g data-component="${resurfaced?'resurfaced':'recent'}-moment-fixture" data-fixture="true">${rect(x,y,w,h,C.paper,C.line,1,14)}`;
  const artH=resurfaced?112:130;
  s+=fixtureArtwork(x+12,y+12,w-24,artH,{variant});
  s+=fixturePill(x+w-122,y+24,102);
  const titleRows=wrap(title,narrow?24:(long?34:38)).slice(0,long||narrow?3:2);
  const titleSize=narrow?13:(resurfaced?13:16),titleLine=narrow?16:(resurfaced?17:20);
  s+=linesText(x+20,y+artH+40,titleRows,titleSize,C.ink,600,'Georgia',titleLine);
  const summaryY=y+artH+40+(titleRows.length-1)*titleLine+24;
  const rtl=/[\u0600-\u06FF]/.test(summary);
  if(rtl){
    const parts=summary.split('·').map(part=>part.trim());
    s+=text(x+w-20,summaryY,parts[0],10.5,C.muted,400,'Arial','start',0,'direction="rtl" unicode-bidi="plaintext"');
    s+=linesText(x+20,summaryY+17,wrap(parts.slice(1).join(' · '),resurfaced?32:48).slice(0,2),10.5,C.muted,400,'Arial',14.5);
  }else s+=linesText(x+20,summaryY,wrap(summary,resurfaced?32:48).slice(0,3),10.5,C.muted,400,'Arial',14.5);
  s+=text(x+20,y+h-36,'PRIVATE FIXTURE · GENERIC DATE 2026-06-12',9.5,C.muted,700,'Arial');
  s+=text(x+20,y+h-16,'Prototype content · not member data',9.5,C.goldSafe,700,'Arial');
  s+='</g>';return s;
}

export function noticedFixtureCard(x,y,w,h,{long=false}={}) {
  let s=`<g data-component="noticed-fixture" data-fixture="true">${brandMaterial(x,y,w,h,{dark:true,seed:7})}`;
  s+=rect(x,y,w,h,'none',C.lineDark,1,14);
  s+=text(x+20,y+32,'What PeerSlate noticed',w<330?10.5:15,C.cloud,600,'Georgia');
  s+=fixturePill(x+w-122,y+16,102);
  const title=long?'A recurring theme across several eligible records is ready for careful owner review—not automatic acceptance.':'A recurring theme is ready for owner review.';
  s+=linesText(x+20,y+72,wrap(title,long?52:42).slice(0,long?4:2),long?11:14,C.cloud,500,'Georgia',long?16:19);
  if(w<360){
    s+=linesText(x+20,y+118,['Support: 2 eligible fixture Moments','Prototype support · not production'],9.5,'#D8DEE3',600,'Arial',13);
    s+=linesText(x+20,y+147,['May miss context · owner review','is required'],9.5,'#D8DEE3',600,'Arial',13);
  }else{
    s+=text(x+20,y+126,'Support: 2 eligible fixture Moments · prototype only',9.5,'#D8DEE3',600,'Arial');
    s+=text(x+20,y+148,'Limitation: may miss context · owner review required',9.5,'#D8DEE3',600,'Arial');
  }
  const ay=y+h-(w<360?62:66);
  if(w<360){
    s+=rect(x+16,ay,92,30,'#142A3C','#688096',1,15)+text(x+62,ay+12,'INSPECT',8.5,C.cloud,800,'Arial','middle')+text(x+62,ay+24,'SUPPORT',8.5,C.cloud,800,'Arial','middle');
    s+=pill(x+114,ay,'CORRECT',{fill:'#142A3C',stroke:'#688096',ink:C.cloud,w:68,h:30,size:8.5});
    s+=pill(x+188,ay,'DISMISS',{fill:'#142A3C',stroke:'#688096',ink:C.cloud,w:68,h:30,size:8.5});
  }else{
    s+=pill(x+20,ay,'INSPECT SUPPORT',{fill:'#142A3C',stroke:'#688096',ink:C.cloud,w:120,h:26,size:8});
    s+=pill(x+148,ay,'CORRECT',{fill:'#142A3C',stroke:'#688096',ink:C.cloud,w:82,h:26,size:8});
    s+=pill(x+238,ay,'DISMISS',{fill:'#142A3C',stroke:'#688096',ink:C.cloud,w:82,h:26,size:8});
  }
  s+=text(x+20,y+h-20,'Governed insight test fixture · not live member activity',9.5,C.paleGold,700,'Arial');
  s+='</g>';return s;
}

export function connectionFixtureCard(x,y,w,h,{name='Riley Chen',initials='RC',long=false}={}) {
  let s=`<g data-component="connection-fixture" data-fixture="true">${rect(x,y,w,h,C.paper,C.line,1,14)}`;
  s+=text(x+20,y+32,'Connections',15,C.ink,600,'Georgia')+fixturePill(x+w-122,y+16,102);
  s+=circle(x+56,y+93,28,'#173149','#9A7A3C',1.5)+text(x+56,y+99,initials,11,C.paleGold,700,'Arial','middle');
  s+=text(x+98,y+82,name,13,C.ink,600,'Georgia');
  s+=text(x+98,y+103,'Generic connection fixture',10,C.goldSafe,700,'Arial');
  const summary=long?'A permitted relationship update with a long translated description wraps without exposing contact details or hidden metadata.':'One permitted relationship update would appear here.';
  s+=linesText(x+98,y+127,wrap(summary,w<360?26:(long?46:42)).slice(0,3),10.5,C.muted,400,'Arial',14.5);
  s+=pill(x+98,y+h-66,'REVIEW PERMITTED UPDATE',{fill:'#F6EBCB',stroke:'#B68D38',ink:C.goldSafe,w:176,h:28,size:9});
  s+=text(x+20,y+h-18,w<360?'Test fixture · no production relationship':'Test fixture · exact action shown · no production relationship',9.5,C.goldSafe,700,'Arial');
  s+='</g>';return s;
}

export function nextFixtureCard(x,y,w,h,{long=false}={}) {
  const narrow=w<330;
  let s=`<g data-component="next-step-fixture" data-fixture="true">${rect(x,y,w,h,'url(#warmPanel)','#C29E4A',1,14)}`;
  s+=fixtureArtwork(x+w*.55,y,w*.45,h,{variant:'path'});
  s+=linesText(x+20,y+28,wrap('Your next useful step',narrow?13:26),narrow?12.5:15,C.ink,600,'Georgia',narrow?15:18)+fixturePill(x+w-122,y+16,102);
  const title=long?'Resolve the changed draft before returning to the rest of the bounded review list.':'Resolve the changed draft';
  const titleRows=wrap(title,long?28:(narrow?14:18)).slice(0,long?4:3);
  s+=linesText(x+20,y+(narrow?82:74),titleRows,long?13:15,C.ink,600,'Georgia',long?18:19);
  s+=text(x+20,y+h-(narrow?72:38),'Grounded in fixture review state',10.5,'#514A3E',500,'Arial');
  if(narrow)s+=linesText(x+20,y+h-42,['Test fixture · no save,','share, or publication'],9.5,C.goldSafe,700,'Arial',13);
  else s+=text(x+20,y+h-18,'Test fixture · no automatic save or publication',9.5,C.goldSafe,700,'Arial');
  s+='</g>';return s;
}

export function boundedRemainder(x,y,w,{count=2,mobile=false}={}) {
  const h=mobile?72:50;
  let s=`<g data-component="bounded-review-remainder" data-availability="coming-later" aria-disabled="true" pointer-events="none" aria-label="Review queue - coming later. Not yet available.">${rect(x,y,w,h,'#EFE7D8','#CDBFAD',1,10)}`;
  s+=text(x+14,y+(mobile?23:19),'Review queue',mobile?10:9,C.ink,700,'Arial');
  s+=comingLaterPill(x+w-(mobile?132:122),y+(mobile?10:8),mobile?118:108);
  if(mobile)s+=linesText(x+14,y+49,wrap('Additional eligible fixture items remain outside Home · no active route',Math.max(36,Math.floor((w-28)/5.3))).slice(0,2),9.5,C.goldSafe,700,'Arial',12);
  else s+=text(x+14,y+38,'Additional eligible fixture items remain outside Home · no active route',9,C.goldSafe,700,'Arial');
  s+='</g>';return s;
}

export function stageCurrent(x=60,y=392,w=1320) {
  const pad=20,gap=16,t1=450,t2=400,t3=w-pad*2-t1-t2-gap*2;
  const tx1=x+pad,tx2=tx1+t1+gap,tx3=tx2+t2+gap;
  const b1=430,b2=380,b3=w-pad*2-b1-b2-gap*2;
  const bx1=x+pad,bx2=bx1+b1+gap,bx3=bx2+b2+gap;
  let s=`<g data-component="owner-home-stage" data-state="current-capability">${rect(x,y,w,640,'url(#ivoryStage)','#C9C0B4',1.2,18,1,'filter="url(#shadow)"')}`;
  s+=sectionHeading(tx1,y+34,'Needs your attention',{subtitle:'Owner review aggregation'});
  s+=emptyLiveCard(tx1,y+62,t1,278,{title:'Needs Review',message:'Nothing requires review right now.',purpose:'When eligible owner-owned items exist, this list remains bounded to three.',theme:'ivory',icon:'document',seed:2});
  s+=sectionHeading(tx2,y+34,'Recent Moment',{subtitle:'One confirmed eligible Moment'});
  s+=emptyLiveCard(tx2,y+62,t2,278,{title:'Recent Moment',message:'No confirmed Moment to show.',purpose:'After the owner creates and confirms a Moment, one eligible recent item may appear here.',theme:'dark',icon:'spark',seed:4});
  s+=sectionHeading(tx3,y+34,'From your history',{subtitle:'One deterministic resurfaced Moment'});
  s+=dormantCard(tx3,y+62,t3,278,{title:'Resurfaced Moment',purpose:'An eligible earlier Moment can return here once the deterministic policy is available.',theme:'dark',icon:'spark',seed:9});
  const by=y+368,bh=242;
  s+=dormantCard(bx1,by,b1,bh,{title:'What PeerSlate noticed',purpose:'A source-linked insight can appear here only when PeerSlate can show what supports it.',theme:'dark',icon:'spark',seed:6});
  s+=dormantCard(bx2,by,b2,bh,{title:'Connections',purpose:'A permitted relationship update can appear only after owner-controlled Connections are available.',theme:'ivory',icon:'link',seed:1});
  s+=currentNextCard(bx3,by,b3,bh,{});
  s+=text(x+w-20,y+624,'Current capability evidence · Capture is the only active Home action shown',9,C.muted,650,'Arial','end',.3);
  s+='</g>';return s;
}

export function stageFutureMax(x=60,y=392,w=1320,{owner='Avery Morgan',long=false}={}) {
  const pad=20,gap=16,t1=450,t2=400,t3=w-pad*2-t1-t2-gap*2;
  const tx1=x+pad,tx2=tx1+t1+gap,tx3=tx2+t2+gap;
  const b1=430,b2=380,b3=w-pad*2-b1-b2-gap*2;
  const bx1=x+pad,bx2=bx1+b1+gap,bx3=bx2+b2+gap;
  let s=`<g data-component="owner-home-stage" data-state="future-maximum-fixture">${rect(x,y,w,long?780:640,'url(#ivoryStage)','#C9C0B4',1.2,18,1,'filter="url(#shadow)"')}`;
  s+=sectionHeading(tx1,y+34,'Needs your attention',{subtitle:'Three-item maximum',right:{x:t1-8,label:'3 MAXIMUM'}});
  const reviewTitles=long?[
    'Confirm the project reflection with an intentionally long title that wraps naturally',
    'Review a milestone summary — ملخص تجريبي طويل',
    'Resolve a changed draft before another owner-safe action can continue'
  ]:['Confirm a project reflection','Review a milestone summary','Resolve a changed draft'];
  reviewTitles.forEach((title,i)=>s+=reviewFixtureRow(tx1,y+58+i*(long?110:76),t1,{title,index:i+1,status:i===2?'Stale fixture':'Private draft',long}));
  s+=boundedRemainder(tx1,y+(long?388:292),t1,{count:2});
  s+=sectionHeading(tx2,y+34,'Recent Moment',{subtitle:'One distinct confirmed fixture'});
  s+=momentFixtureCard(tx2,y+58,t2,long?350:282,{title:long?'A deliberately long launch retrospective title that remains readable at increased text spacing':'A launch lesson worth keeping',summary:long?'Prototype summary with missing optional media fallback, translated content, and safe wrapping for a verylongunbrokenexampleidentifier.test':'A generic reflection fixture with bounded owner-safe summary.',variant:long?'missing-media':'editorial-dawn',long});
  s+=sectionHeading(tx3,y+34,'From your history',{subtitle:'One deterministic distinct fixture'});
  s+=momentFixtureCard(tx3,y+58,t3,long?350:282,{title:long?'The decision that simplified the work and should never duplicate Recent':'The decision that simplified the work',summary:long?'مثال تجريبي ثنائي الاتجاه · Prototype only · no production history':'Deterministic resurfacing fixture · not member history.',variant:'editorial-ridge',resurfaced:true,long});
  const by=y+(long?438:368),bh=long?312:242;
  s+=noticedFixtureCard(bx1,by,b1,bh,{long});
  s+=connectionFixtureCard(bx2,by,b2,bh,{name:owner==='Avery Morgan'?'Riley Chen':'Morgan Lee',initials:owner==='Avery Morgan'?'RC':'ML',long});
  s+=nextFixtureCard(bx3,by,b3,bh,{long});
  s+=text(x+w-20,y+(long?764:624),'Future maximum fixture · exactly 9 product objects · not live member data',9,C.goldSafe,700,'Arial','end',.3);
  s+='</g>';return s;
}

export function desktopScreen({future=false,owner='Member',initials='M',focused=false,long=false,evidenceNote=''}={}) {
  const height=long?1240:1100;
  let s=rect(0,0,1440,height,'url(#bgNavy)');
  s+=circle(1290,110,210,'url(#goldOrb)','none',0,.22);
  s+=rect(40,28,1360,height-56,'#07111C','#6C7277',1.2,24,1,'filter="url(#shadow)"');
  s+=desktopNav({fixture:future});
  s+=ownerHero({fixture:future,owner,initials,focused});
  s+=audienceRail(120,286,900,{fixture:future,mobile:false});
  s+=future?stageFutureMax(60,392,1320,{owner,long}):stageCurrent(60,392,1320);
  if(evidenceNote)s+=pill(64,long?1164:1028,evidenceNote,{fill:'#101C27',stroke:'#9B772E',ink:C.paleGold,w:520,h:28,size:9});
  const footerY=long?1206:1068;
  s+=text(64,footerY,future?'FUTURE DESIGN FIXTURE · NOT MEMBER DATA · NOT IMPLEMENTED':'VISUAL DESIGN · CURRENT-CAPABILITY TREATMENT · OWNER HOME NOT IMPLEMENTED',8.5,'#AAB4BD',700,'Arial','start',.35);
  s+=text(1376,footerY,'NO ROUTE · NO DEPLOYMENT · NO LIVE PRODUCTION CLAIM',8.5,'#AAB4BD',700,'Arial','end',.35);
  return svgRoot(1440,height,future?'Owner Home maximum future design fixture':'Owner Home current-capability vector reconstruction',future?'Editable vector Owner Home showing exactly nine generic fixture objects.':'Editable vector Owner Home with Capture active and dormant capabilities labeled Coming later.',s);
}

export function mobileBottomNav(w,y) {
  const labels=[['Home','CURRENT CONTEXT'],['Journal','COMING LATER'],['Capture','AVAILABLE'],['Slate','COMING LATER'],['More','COMING LATER']];
  const cell=w/5; let s=`<g data-component="mobile-bottom-navigation">${rect(0,y,w,120,'#070C12','#293846',1,0)}`;
  labels.forEach((entry,i)=>{
    const cx=cell*(i+.5),capture=i===2;
    const disabled=entry[1]==='COMING LATER';
    s+=`<g data-component="mobile-nav-item" data-state="${disabled?'disabled':i===0?'context':'available'}" ${disabled?'aria-disabled="true" pointer-events="none"':''}>`;
    if(capture)s+=circle(cx,y+27,24,'#111D27','#D5AA48',2)+iconCamera(cx-12,y+15,24,C.paleGold);
    else s+=circle(cx,y+29,10,'none',i===0?C.paleGold:'#9DA8B2',1.6);
    s+=text(cx,y+65,entry[0],w<=320?9.5:10,i===0||capture?C.cloud:'#C2C8CE',i===0||capture?700:500,'Arial','middle');
    if(entry[1]==='COMING LATER'){
      const statusSize=w<=320?9:9.5;
      s+=`<text x="${cx}" y="${y+82}" font-family="Arial" font-size="${statusSize}" font-weight="700" fill="#C9A653" text-anchor="middle" letter-spacing=".12" aria-label="COMING LATER"><tspan x="${cx}" dy="0">COMING</tspan><tspan x="${cx}" dy="13">LATER</tspan></text>`;
    }else if(entry[1]==='CURRENT CONTEXT'){
      s+=`<text x="${cx}" y="${y+80}" font-family="Arial" font-size="9" font-weight="700" fill="${C.paleGold}" text-anchor="middle" aria-label="CURRENT CONTEXT"><tspan x="${cx}" dy="0">CURRENT</tspan><tspan x="${cx}" dy="13">CONTEXT</tspan></text>`;
    }else{
      s+=text(cx,y+86,entry[1],9,C.paleGold,700,'Arial','middle',.1);
    }
    s+='</g>';
  });
  s+='</g>';return s;
}

export function mobileSectionHeader(w,y,title,subtitle='') {
  let s=text(20,y,title,w<=320?17:19,C.cloud,600,'Georgia');
  if(subtitle)s+=text(20,y+21,subtitle,9.5,C.mutedDark,400,'Arial');
  return s;
}

export function mobileDormant(w,y,{title,purpose,theme='ivory',icon='spark',seed=0,h=178}={}) {
  return dormantCard(16,y,w-32,h,{title,purpose,theme,icon,seed,compact:true});
}

export function mobileScreen({w=390,future=false,owner='Member',initials='M'}={}) {
  const compact=w<=320;
  const audienceH=252;
  let y=0,body='';
  body+=rect(0,0,w,72,'#070C12')+mobileTopBar(w,{fixture:future}); y=72;
  body+=`<g data-component="mobile-owner-hero">${cinematicAtmosphere(0,y,w,250,{accent:false})}`;
  body+=rect(0,y,w,250,'url(#copyVeil)');
  body+=ownerAvatar(54,y+72,32,initials,future);
  body+=text(98,y+55,'Owner Home',compact?21:23,C.cloud,500,'Georgia');
  body+=text(98,y+79,`${owner} · private workspace`,compact?9:9.5,C.paleGold,700,'Arial');
  body+=linesText(20,y+124,['Viewing this design did not publish, share,','connect, or save anything.'],9.5,'#CBD2D8',400,'Arial',14);
  if(future)body+=pill(20,y+166,'FUTURE DESIGN FIXTURE · NOT MEMBER DATA',{fill:'#302516',stroke:'#A9791C',ink:C.paleGold,w:w-40,h:26,size:8.5});
  body+=capturePanel(16,y+(future?200:166),w-32,compact?86:92,{compact:true});
  body+='</g>'; y+=future?316:282;
  body+=audienceRail(12,y,w-24,{fixture:future,mobile:true}); y+=audienceH+24;
  if(!future){
    body+=mobileSectionHeader(w,y+36,'Needs your attention','Bounded owner review'); y+=58;
    body+=emptyLiveCard(16,y,w-32,compact?188:178,{title:'Needs Review',message:'Nothing requires review right now.',purpose:'Future eligible records remain bounded to three.',theme:'ivory',icon:'document',seed:2,compact}); y+=compact?206:196;
    body+=mobileSectionHeader(w,y+34,'Recent Moment','One confirmed eligible Moment'); y+=56;
    body+=emptyLiveCard(16,y,w-32,compact?190:180,{title:'Recent Moment',message:'No confirmed Moment to show.',purpose:'No member media, title, date, or result is represented.',theme:'dark',icon:'spark',seed:4,compact}); y+=compact?208:198;
    body+=mobileSectionHeader(w,y+34,'From your history','One deterministic distinct Moment'); y+=56;
    body+=mobileDormant(w,y,{title:'Resurfaced Moment',purpose:'An eligible earlier Moment can return here once the deterministic policy is available.',theme:'dark',icon:'spark',seed:9,h:compact?198:186}); y+=compact?216:204;
    body+=mobileDormant(w,y,{title:'What PeerSlate noticed',purpose:'A source-linked insight can appear only when PeerSlate can show what supports it.',theme:'dark',icon:'spark',seed:6,h:compact?198:186}); y+=compact?216:204;
    body+=mobileDormant(w,y,{title:'Connections',purpose:'A permitted relationship update can appear only after owner-controlled Connections are available.',theme:'ivory',icon:'link',seed:1,h:compact?198:186}); y+=compact?216:204;
    body+=currentNextCard(16,y,w-32,compact?208:196,{compact}); y+=compact?228:216;
  }else{
    body+=mobileSectionHeader(w,y+36,'Needs your attention','Three-item maximum · Test fixture'); y+=58;
    const titles=owner==='Avery Morgan'?['Confirm a project reflection','Review a milestone summary','Resolve a changed draft']:['Confirm a practice reflection','Review a project milestone','Resolve an updated private draft'];
    titles.forEach((title,i)=>{body+=reviewFixtureRow(16,y,w-32,{title,index:i+1,status:i===2?'Stale fixture':'Private draft'});y+=compact?86:78;});
    body+=boundedRemainder(16,y,w-32,{count:2,mobile:true});y+=84;
    body+=mobileSectionHeader(w,y+34,'Recent Moment','One distinct fixture');y+=56;
    body+=momentFixtureCard(16,y,w-32,282,{title:owner==='Avery Morgan'?'A launch lesson worth keeping':'A workshop lesson worth keeping',summary:'Generic prototype content with a bounded owner-safe summary.',variant:'editorial-dawn'});y+=300;
    body+=mobileSectionHeader(w,y+34,'From your history','One deterministic distinct fixture');y+=56;
    body+=momentFixtureCard(16,y,w-32,274,{title:'The decision that simplified the work',summary:'Deterministic resurfacing fixture · not member history.',variant:'editorial-ridge',resurfaced:true});y+=292;
    body+=noticedFixtureCard(16,y,w-32,226,{});y+=244;
    body+=connectionFixtureCard(16,y,w-32,226,{name:owner==='Avery Morgan'?'Riley Chen':'Morgan Lee',initials:owner==='Avery Morgan'?'RC':'ML'});y+=244;
    body+=nextFixtureCard(16,y,w-32,226,{});y+=246;
  }
  body+=rect(0,y,w,64,'#0B1722')+text(20,y+25,future?'Exactly 9 fixture objects · no production data':'Capture is the only active Home action shown',8.5,future?C.paleGold:'#C3CBD2',700,'Arial');
  body+=text(20,y+47,'Visual design only · Owner Home not implemented',8.5,'#A9B3BC',600,'Arial'); y+=64;
  body+=mobileBottomNav(w,y); y+=120;
  body+=rect(0,y,w,22,'#04070B'); y+=22;
  const titleValue=future?`${w}px mobile maximum future fixture`:`${w}px mobile current-capability design`;
  body=rect(0,0,w,y,'url(#bgNavy)')+body;
  return svgRoot(w,y,titleValue,'Standalone full-scroll mobile Owner Home vector design with bottom navigation and explicit Coming later capability states.',body);
}

function evidenceHero({focused=false,label='STATE EVIDENCE'}={}) {
  let s=cinematicAtmosphere(40,96,1360,250);
  s+=ownerAvatar(112,194,48,'M',false);
  s+=text(178,179,'Owner Home',34,C.cloud,500,'Georgia');
  s+=text(178,207,'Private workspace for the signed-in member',12,C.paleGold,700,'Arial');
  s+=text(178,232,'Nothing here publishes, shares, connects, or previews another audience.',10,'#C2CBD2',400,'Arial');
  s+=pill(178,256,label,{fill:'#111D27',stroke:'#7A6132',ink:C.paleGold,w:210,h:28,size:9});
  s+=capturePanel(988,140,360,126,{focused});
  return s;
}

function failureCard(x,y,w,h,{title='This section could not load',message='Retry repeats the same bounded owner request.',complete=false,focused=false}={}) {
  let s=`<g data-component="failure-state">${rect(x,y,w,h,complete?'#0C1823':'#FFF8ED',complete?'#4C657A':'#C49A57',1.3,16)}`;
  s+=text(x+24,y+40,complete?'HOME DATA FAILED':'PARTIAL FAILURE',8,complete?C.paleGold:C.goldSafe,750,'Arial','start',1.1);
  s+=text(x+24,y+82,title,22,complete?C.cloud:C.ink,600,'Georgia');
  s+=linesText(x+24,y+112,wrap(message,62).slice(0,3),10,complete?'#BBC5CE':C.muted,400,'Arial',15);
  const bx=x+24,by=y+h-62,bw=126,bh=40;
  if(focused)s+=focusRing(bx,by,bw,bh,10);
  s+=rect(bx,by,bw,bh,complete?C.marigold:C.navy,complete?C.paleGold:C.navy,1,10)+text(bx+bw/2,by+25,'RETRY',9,complete?C.navy:C.cloud,750,'Arial','middle',.8);
  s+=rect(x+170,by,178,bh,'none',complete?'#AFC1CF':'#667989',1.3,10)+text(x+259,by+25,'SAFE RETURN',8,complete?C.cloud:C.navy,750,'Arial','middle',.6);
  s+='</g>';return s;
}

function stateFrame(body,title,desc,{focused=false,label='STATE EVIDENCE'}={}) {
  let s=rect(0,0,1440,960,'url(#bgNavy)')+rect(40,28,1360,904,'#07111C','#6C7277',1.2,24,1,'filter="url(#shadow)"');
  s+=desktopNav({fixture:false})+evidenceHero({focused,label})+audienceRail(120,286,900,{mobile:false});
  s+=body;
  s+=text(64,918,'STATIC VISUAL EVIDENCE · BEHAVIOR, DOM, REQUEST, AND FOCUS MANAGEMENT NOT YET VERIFIED',8.5,'#AAB4BD',700,'Arial','start',.35);
  return svgRoot(1440,960,title,desc,s);
}

export function loadingEvidence() {
  const x=60,y=392,w=1320,h=490,col=(w-72)/3; let s=`<g data-component="loading-stage">${rect(x,y,w,h,'url(#ivoryStage)','#C9C0B4',1.2,18)}`;
  s+=text(x+24,y+38,'Loading Owner Home',20,C.ink,600,'Georgia')+pill(x+w-146,y+18,'LOADING',{fill:'#F1E9DA',stroke:C.line,ink:C.muted,w:122,h:28,size:8});
  s+=text(x+24,y+62,'One polite status announcement · no prior payload is represented as current',9,C.muted,400,'Arial');
  const labels=['Needs Review','Recent Moment','Resurfaced Moment','What PeerSlate noticed','Connections','Next Useful Step'];
  for(let i=0;i<6;i++){
    const row=Math.floor(i/3),cx=x+24+(i%3)*(col+12),cy=y+92+row*176;
    if([2,3,4].includes(i)){
      const purposes={2:'Deterministic resurfacing is not yet available.',3:'Governed insights are not yet available.',4:'Authorized connection items are not yet available.'};
      s+=dormantCard(cx,cy,col,154,{title:labels[i],purpose:purposes[i],theme:i===3?'dark':'ivory',icon:i===4?'link':'spark',seed:i,compact:true});
    }else{
      s+=rect(cx,cy,col,154,'#F8F4ED',C.line,1,14);
      s+=text(cx+18,cy+28,labels[i],12,C.ink,600,'Georgia');
      s+=rect(cx+18,cy+48,col*.58,12,'#DED5C8','none',0,6);
      s+=rect(cx+18,cy+78,col*.82,9,'#E6DED2','none',0,5);
      s+=rect(cx+18,cy+102,col*.68,9,'#E6DED2','none',0,5);
      s+=text(cx+18,cy+136,'Skeleton is aria-hidden in implementation',9,C.muted,600,'Arial');
    }
  }
  s+='</g>';
  return stateFrame(s,'Owner Home loading evidence','Stable heading and Capture with inert skeleton surfaces and no fake records or counts.',{label:'LOADING EVIDENCE'});
}

export function partialFailureEvidence() {
  const x=60,y=392,w=1320; let s=`<g data-component="partial-failure-stage">${rect(x,y,w,490,'url(#ivoryStage)','#C9C0B4',1.2,18)}`;
  s+=emptyLiveCard(x+20,y+28,400,212,{title:'Needs Review',message:'Nothing requires review right now.',purpose:'This independent category remains understandable.',theme:'ivory'});
  s+=failureCard(x+436,y+28,404,212,{title:'Recent Moment could not load',message:'Only this category is unavailable. No broader or cached private data is substituted.'});
  s+=dormantCard(x+856,y+28,444,212,{title:'Resurfaced Moment',purpose:'Deterministic resurfacing is not yet available.',theme:'dark',icon:'spark',seed:9});
  s+=dormantCard(x+20,y+256,400,206,{title:'What PeerSlate noticed',purpose:'Governed insights remain a future capability.',theme:'dark',icon:'spark',seed:6});
  s+=dormantCard(x+436,y+256,404,206,{title:'Connections',purpose:'Connections remain a future capability.',theme:'ivory',icon:'link'});
  s+=currentNextCard(x+856,y+256,444,206,{});
  s+='</g>';
  return stateFrame(s,'Owner Home partial failure evidence','One failed category with Retry while independent categories and Capture remain safe.',{label:'PARTIAL FAILURE EVIDENCE'});
}

export function completeFailureEvidence() {
  const x=60,y=392,w=1320; let s=`<g data-component="complete-failure-stage">${rect(x,y,w,490,'url(#ivoryStage)','#C9C0B4',1.2,18)}`;
  s+=failureCard(x+170,y+76,w-340,330,{title:'Owner Home data could not load',message:'Capture remains shown only because this evidence assumes its protected destination was independently verified. Retry requests the same bounded owner payload.',complete:true,focused:true});
  s+='</g>';
  return stateFrame(s,'Owner Home complete failure evidence','Usable heading, independently safe Capture, bounded Retry, and no private fallback payload.',{label:'COMPLETE FAILURE EVIDENCE'});
}

export function staleEvidence() {
  const x=60,y=392,w=1320;let s=`<g data-component="stale-stage">${rect(x,y,w,490,'url(#ivoryStage)','#C9C0B4',1.2,18)}`;
  s+=rect(x+24,y+28,650,430,C.paper,C.line,1,16)+fixturePill(x+44,y+48,112)+pill(x+166,y+48,'STALE',{fill:'#F3E1B7',stroke:'#B98B2E',ink:C.goldSafe,w:86,h:24,size:8});
  s+=text(x+44,y+104,'Resolve a changed private draft',22,C.ink,600,'Georgia');
  s+=linesText(x+44,y+140,['Test fixture · the item changed after this view loaded.','Protected actions remain disabled until the owner refreshes.'],10,C.muted,400,'Arial',16);
  s+=rect(x+44,y+204,580,110,'#EFE8DD','#D6CDBF',1,12)+text(x+64,y+246,'No stale write will be applied or silently overwrite the newer version.',10,C.ink,600,'Arial');
  s+=focusRing(x+44,y+352,150,44,10)+rect(x+44,y+352,150,44,C.navy,C.navy,1,10)+iconRefresh(x+60,y+362,22,C.paleGold)+text(x+126,y+380,'REFRESH',9,C.cloud,750,'Arial','middle');
  s+=dormantCard(x+700,y+28,596,430,{title:'Viewer modes',purpose:'Preview modes remain disabled and cannot be used to bypass stale owner authorization.',theme:'dark',icon:'link',seed:5});
  s+='</g>';
  return stateFrame(s,'Owner Home stale-version evidence','Generic stale fixture with protected action disabled and Refresh focus evidence.',{label:'STALE VERSION · TEST FIXTURE'});
}

export function restrictedEvidence() {
  const x=60,y=392,w=1320;let s=`<g data-component="restricted-stage">${rect(x,y,w,490,'url(#ivoryStage)','#C9C0B4',1.2,18)}`;
  s+=rect(x+205,y+70,w-410,340,'#0B1824',C.lineDark,1.3,18)+pill(x+237,y+100,'RESTRICTED',{fill:'#142A3C',stroke:'#506A80',ink:'#E3E8EC',w:118,h:28,size:8});
  s+=text(x+237,y+170,'This item is not available in this context.',24,C.cloud,600,'Georgia');
  s+=linesText(x+237,y+210,['No private title, media, count, timestamp, source,','or reason is revealed. The safe return path remains available.'],10,'#BBC5CE',400,'Arial',17);
  s+=rect(x+237,y+300,160,44,'none','#AFC1CF',1.4,10)+text(x+317,y+327,'RETURN TO HOME',8,C.cloud,750,'Arial','middle',.7);
  s+='</g>';
  return stateFrame(s,'Owner Home restricted evidence','Neutral non-enumerating restricted treatment with safe navigation and no private detail leak.',{label:'RESTRICTED EVIDENCE'});
}

export function recoveryEvidence() {
  const x=60,y=392,w=1320;let s=`<g data-component="recovery-stage">${rect(x,y,w,490,'url(#ivoryStage)','#C9C0B4',1.2,18)}`;
  s+=rect(x+24,y+28,624,430,C.paper,C.line,1,16)+pill(x+46,y+50,'RETRY SUCCEEDED',{fill:'#E0EFE9',stroke:C.teal,ink:C.teal,w:142,h:26,size:9});
  s+=text(x+46,y+106,'Home updated',22,C.ink,600,'Georgia')+text(x+46,y+138,'One completion announcement. No duplicate card narration.',9,C.muted,400,'Arial');
  s+=emptyLiveCard(x+46,y+174,580,220,{title:'Needs Review',message:'Nothing requires review right now.',purpose:'Focus moves to this updated heading only if the Retry control disappears.',theme:'ivory'});
  s+=rect(x+672,y+28,624,430,'#0B1824',C.lineDark,1,16)+pill(x+694,y+50,'RETRY STILL FAILED',{fill:'#2A1D1C',stroke:'#8F5448',ink:'#F2C9C1',w:154,h:26,size:9});
  s+=text(x+694,y+106,'The same bounded request still failed',22,C.cloud,600,'Georgia')+linesText(x+694,y+140,['Context is preserved. The control remains repeatable.','No duplicate error is appended and scope is not broadened.'],9,'#BBC5CE',400,'Arial',15);
  s+=focusRing(x+694,y+214,126,44,10)+rect(x+694,y+214,126,44,C.marigold,C.paleGold,1,10)+text(x+757,y+241,'RETRY',9,C.navy,750,'Arial','middle');
  s+=rect(x+840,y+214,176,44,'none','#AFC1CF',1.3,10)+text(x+928,y+241,'SAFE RETURN',8,C.cloud,750,'Arial','middle');
  s+='</g>';
  return stateFrame(s,'Owner Home recovery evidence','Successful and failed retry treatments with predictable focus and bounded request behavior.',{label:'RECOVERY EVIDENCE'});
}

export function accessLifecycleEvidence() {
  const w=1440,h=1080;let s=rect(0,0,w,h,'url(#bgNavy)')+rect(40,28,1360,1024,'#07111C','#6C7277',1.2,24,1,'filter="url(#shadow)"');
  s+=logo(64,78,{dark:true,size:28})+text(64,136,'Access and lifecycle evidence',34,C.cloud,500,'Georgia');
  s+=text(64,166,'Neutral component treatments only · no owner controls or viewer payload are present on this evidence board.',11,'#C3CBD2',400,'Arial');
  s+=pill(1138,62,'STATIC DESIGN EVIDENCE',{fill:'#111D27',stroke:'#7A6132',ink:C.paleGold,w:228,h:30,size:9});
  const states=[
    {label:'VIEWER EMPTY / UNPUBLISHED',title:'No eligible published content in this view.',copy:['Viewer empty: an authorized projection exists with zero eligible items.','Unpublished: no viewer projection exists. Neither implies private content.'],action:'SAFE RETURN',dark:false},
    {label:'ACCESS CHANGED · REVOKED',title:'Access has changed.',copy:['Previously rendered sensitive content is cleared before','this heading receives focus. No stale fallback remains.'],action:'RETURN SAFELY',dark:true,focus:true},
    {label:'DELETED',title:'This source is no longer available.',copy:['Approved tombstone only. No reconstructed title, body,','media, timestamp, relationship, or prior action remains.'],action:'RETURN TO HOME',dark:false},
    {label:'SESSION EXPIRED',title:'Your private session ended.',copy:['Protected data is cleared. The sign-in return carries no','private payload in its URL, title, or analytics label.'],action:'SIGN IN SAFELY',dark:true},
    {label:'SLOW RESPONSE · TIMEOUT',title:'This bounded request took too long.',copy:['Status updates without starting a duplicate request. Retry','repeats the same authorization scope; safe navigation remains.'],action:'RETRY',dark:false},
    {label:'NOT FOUND · FAIL CLOSED',title:'This item is not available.',copy:['Unknown and direct-object requests use one neutral response.','The screen does not confirm that a private subject exists.'],action:'SAFE RETURN',dark:true}
  ];
  states.forEach((item,i)=>{
    const col=i%2,row=Math.floor(i/2),x=64+col*668,y=206+row*260,cw=644,ch=230;
    const fill=item.dark?'#0B1824':C.paper,stroke=item.dark?C.lineDark:C.line,ink=item.dark?C.cloud:C.ink,muted=item.dark?'#C3CCD3':C.muted;
    s+=`<g data-component="lifecycle-state" data-state="${esc(item.label.toLowerCase().replaceAll(' ','-'))}">`+rect(x,y,cw,ch,fill,stroke,1.4,16);
    s+=pill(x+20,y+18,item.label,{fill:item.dark?'#142A3C':'#F3EEE6',stroke:item.dark?'#668096':'#BCA46C',ink:item.dark?C.paleGold:C.goldSafe,w:224,h:28,size:8.5});
    s+=text(x+20,y+82,item.title,20,ink,600,'Georgia');
    s+=linesText(x+20,y+116,item.copy,11,muted,400,'Arial',17);
    if(item.focus)s+=focusRing(x+14,y+52,cw-28,44,8);
    s+=rect(x+20,y+170,156,40,item.dark?'#000':'#071421',item.dark?'#FFF':'#071421',1.2,10)+text(x+98,y+195,item.action,9,item.dark?'#FFF':C.cloud,800,'Arial','middle',.35);
    if(item.label.startsWith('SLOW'))s+=text(x+196,y+195,'Same bounded request · no duplicate request',9,C.goldSafe,700,'Arial');
    s+='</g>';
  });
  s+=text(64,1018,'STATIC VISUAL EVIDENCE · DOM CLEARING, LIVE REGIONS, AUTHORIZATION, CACHE/MEDIA INVALIDATION, AND FOCUS MOVEMENT REQUIRE IMPLEMENTATION TESTS',8,'#9AA6B0',700,'Arial','start',.4);
  return svgRoot(w,h,'Owner Home access and lifecycle evidence','Empty published projection, unpublished, revoked, deleted, session expired, timeout, and fail-closed treatments.',s);
}

export function reflow200Evidence() {
  const w=1024,h=2640,cw=w-140;
  let s=rect(0,0,w,h,'url(#bgNavy)')+rect(36,28,w-72,h-60,'#07111C','#68747D',1.3,24,1,'filter="url(#shadow)"');
  s+=rect(36,28,w-72,96,'#070C12','none',0,24)+logo(70,84,{dark:true,size:34})+pill(w-254,56,'200% REFLOW · 512 CSS PX',{fill:'#2E2518',stroke:'#A9791C',ink:C.paleGold,w:184,h:34,size:10});
  s+=text(70,174,'Owner Home',44,C.cloud,500,'Georgia');
  s+=text(70,214,'Member · private workspace',18,C.paleGold,700,'Arial');
  s+=linesText(70,248,['Nothing here publishes, shares, connects,','or previews another audience.'],16,'#D0D7DD',400,'Arial',24);

  const captureY=310;
  s+=rect(70,captureY,cw,160,'url(#glass)','#A08248',1.5,18)+rect(94,captureY+36,82,82,'#4A3A24','#A08248',1.5,14)+iconCamera(116,captureY+57,38,C.paleGold);
  s+=text(202,captureY+58,'Capture a Moment',30,C.cloud,600,'Georgia')+text(202,captureY+92,'Protected private Capture',16,'#E0E5E9',600,'Arial')+text(202,captureY+124,'Speak or Type continues in the existing protected flow.',14,'#C4CDD4',400,'Arial')+text(918,captureY+94,'→',34,C.paleGold,400,'Arial','middle');

  const audienceY=494;
  s+=rect(70,audienceY,cw,350,'#0B1824','#806633',1.5,18)+text(96,audienceY+46,'My Slate preview',26,C.cloud,600,'Georgia')+comingLaterPill(754,audienceY+20,176);
  s+=linesText(96,audienceY+84,['Owner View is the current private workspace context—not a viewer preview.','Viewer modes below are approved future capabilities.'],15,'#D1D8DE',400,'Arial',22);
  s+=rect(96,audienceY+140,cw-52,52,'#D9AA2B','#F0D17B',1,26)+text(122,audienceY+162,'OWNER VIEW',14,C.navy,800,'Arial')+text(904,audienceY+174,'CURRENT PRIVATE CONTEXT · NOT A PREVIEW MODE',12,C.navy,750,'Arial','end');
  s+=text(96,audienceY+226,'PREVIEW AS',13,C.paleGold,800,'Arial','start',.4);
  const modes=['SELECTED PERSON','CONNECTION','AUTHENTICATED MEMBER','PUBLIC'];
  modes.forEach((mode,i)=>{const mx=96+(i%2)*414,my=audienceY+244+Math.floor(i/2)*54;s+=`<g aria-disabled="true" pointer-events="none">`+rect(mx,my,394,44,'#142A3C','#4F6A80',1.2,22)+text(mx+197,my+18,mode,12,'#E2E7EA',800,'Arial','middle')+text(mx+197,my+35,'COMING LATER',11,C.paleGold,800,'Arial','middle')+'</g>';});

  function zoomCard(y,title,status,message,purpose,{dark=false,warm=false,icon='spark'}={}){
    const fill=dark?'url(#dormantNavy)':warm?'url(#warmPanel)':C.paper,stroke=dark?C.lineDark:warm?'#C29E4A':C.line,ink=dark?C.cloud:C.ink,muted=dark?'#D0D8DE':'#555C61';
    let z=`<g data-component="200-percent-reflow-card">${rect(70,y,cw,242,fill,stroke,1.4,16)}`;
    if(dark){z+=brandMaterial(70,y,cw,242,{dark:true,seed:y%11});z+=rect(70,y,cw*.84,242,'url(#copyZone)','none',0,16,.98);} else if(icon==='link')z+=relationshipMaterial(70,y,cw,242);
    z+=text(96,y+48,title,24,ink,600,'Georgia');
    z+=pill(746,y+22,status,{fill:dark?'#142A3C':'#F8F3E8',stroke:dark?'#668096':'#C8A968',ink:dark?C.paleGold:C.goldSafe,w:184,h:34,size:11});
    z+=linesText(96,y+98,wrap(message,62).slice(0,2),19,ink,600,'Georgia',25);
    z+=linesText(96,y+154,wrap(purpose,76).slice(0,3),15,muted,400,'Arial',21);
    z+=text(96,y+220,status==='COMING LATER'?'Not yet available · no member record or generated result':'No fixture record, count, timestamp, or member media is shown',12,muted,650,'Arial');
    z+='</g>';return z;
  }
  let y=872;
  s+=zoomCard(y,'Needs Review','EMPTY','Nothing requires review right now.','Future eligible owner-owned records remain bounded to three.',{icon:'document'});y+=266;
  s+=zoomCard(y,'Recent Moment','EMPTY','No confirmed Moment to show.','No member media, title, date, or result is represented.',{dark:true});y+=266;
  s+=zoomCard(y,'Resurfaced Moment','COMING LATER','A deterministic earlier Moment can return here later.','The unavailable slot uses only abstract brand material.',{dark:true});y+=266;
  s+=zoomCard(y,'What PeerSlate noticed','COMING LATER','A source-linked insight can appear only after its governed lifecycle exists.','No observation, evidence count, recommendation, or generated output is shown.',{dark:true});y+=266;
  s+=zoomCard(y,'Connections','COMING LATER','A permitted relationship update can appear only after authorization exists.','No person, avatar, count, message, notification, or activity is shown.',{icon:'link'});y+=266;
  s+=zoomCard(y,'Your next useful step','AVAILABLE','Start a private Capture.','Capture is the only available next step; there is no automatic save, placement, share, or publication.',{warm:true});y+=270;
  s+=text(70,y,'One column · no horizontal canvas · flexible-height content · semantic order preserved',13,'#B7C1C9',700,'Arial');
  s+=text(70,y+30,'Static 512 CSS-pixel equivalent at 200% · browser zoom, text-spacing, DOM order, and focus remain implementation tests',12,'#9DA8B2',600,'Arial');
  return svgRoot(w,h,'Owner Home 200 percent reflow evidence','Single-column 512 CSS-pixel equivalent at 200 percent with complete readable text, explicit states, and no horizontal layout.',s);
}

export function highContrastEvidence() {
  const w=1440,h=960;let s=rect(0,0,w,h,'#000')+rect(40,28,1360,904,'#000','#FFF',3,22);
  s+=text(72,76,'PeerSlate',30,'#FFF',600,'Georgia')+pill(1190,48,'HIGH CONTRAST',{fill:'#000',stroke:'#FFF',ink:'#FFF',w:146,h:32,size:9});
  const nav=[['Home','CURRENT'],['Journal','COMING LATER'],['My Slate','COMING LATER'],['Connections','COMING LATER'],['More','COMING LATER']];
  nav.forEach((item,i)=>{const cx=470+i*138;s+=`<g ${i?'aria-disabled="true" pointer-events="none"':''}>`+text(cx,58,item[0],11,'#FFF',i===0?800:600,'Arial','middle')+text(cx,78,item[1],8.5,'#FFF',800,'Arial','middle',.1)+'</g>';});
  s+=line(40,100,1400,100,'#FFF',2);
  s+=text(72,150,'Owner Home',38,'#FFF',600,'Georgia')+text(72,180,'Member · private workspace · no publication or sharing',13,'#FFF',500,'Arial');
  s+=rect(944,118,392,134,'none','#FFF',4,22)+rect(950,124,380,122,'#000','#FFF',3,16)+iconCamera(978,164,34,'#FFF')+text(1032,166,'Capture a Moment',22,'#FFF',700,'Georgia')+text(1032,194,'Protected private Capture',11,'#FFF',500,'Arial');
  s+=rect(72,274,1296,122,'#000','#FFF',3,14)+text(94,310,'My Slate preview',16,'#FFF',700,'Georgia')+text(94,338,'COMING LATER · Not yet available',11,'#FFF',700,'Arial')+text(94,365,'Owner View is current context—not viewer preview.',10,'#FFF',600,'Arial');
  const modes=['SELECTED PERSON','CONNECTION','AUTHENTICATED MEMBER','PUBLIC'];
  modes.forEach((mode,i)=>{const cx=598+i*188;s+=`<g aria-disabled="true" pointer-events="none">`+rect(cx,296,172,72,'#000','#FFF',2,10)+text(cx+86,322,mode,9,'#FFF',800,'Arial','middle')+text(cx+86,348,'COMING LATER',9,'#FFF',800,'Arial','middle')+'</g>';});
  const cards=[['Needs Review','EMPTY · Nothing requires review right now.'],['Recent Moment','EMPTY · No confirmed Moment to show.'],['Resurfaced Moment','COMING LATER · Not yet available.'],['What PeerSlate noticed','COMING LATER · Not yet available.'],['Connections','COMING LATER · Not yet available.'],['Your next useful step','AVAILABLE · Start a private Capture.']];
  cards.forEach((item,i)=>{const cx=72+(i%3)*432,cy=426+Math.floor(i/3)*190;s+=rect(cx,cy,408,166,'#000','#FFF',3,14)+text(cx+20,cy+40,item[0],18,'#FFF',700,'Georgia')+linesText(cx+20,cy+78,wrap(item[1],42),11,'#FFF',600,'Arial',17);});
  s+=text(72,822,'Meaning survives without gold, opacity, gradients, or decorative imagery.',11,'#FFF',600,'Arial');
  s+=text(72,856,'Implementation maps tokens to Canvas, CanvasText, ButtonText, Highlight, and currentColor.',9,'#FFF',500,'Arial');
  s+=text(72,904,'STATIC FORCED-COLORS EVIDENCE · WINDOWS HIGH CONTRAST REMAINS AN IMPLEMENTATION TEST',8,'#FFF',700,'Arial');
  return svgRoot(w,h,'Owner Home high-contrast evidence','Forced-colors visual treatment using black, white, text status, borders, and visible focus.',s);
}

export function reducedMotionEvidence() {
  let s=rect(0,0,1440,960,'url(#bgNavy)')+rect(40,28,1360,904,'#07111C','#6C7277',1.2,24,1,'filter="url(#shadow)"');
  s+=desktopNav({fixture:false})+evidenceHero({label:'REDUCED MOTION EVIDENCE'});
  s+=rect(60,378,1320,494,'url(#ivoryStage)','#C9C0B4',1.2,18);
  const rules=[
    ['Atmosphere','Static atmosphere component · no parallax'],
    ['Loading','Status text remains meaningful without shimmer'],
    ['Ordering','No carousel, auto-advance, or animated reordering'],
    ['State change','Immediate replacement · no delayed exit animation'],
    ['Focus','Predictable placement · no animated scrolling'],
    ['Access revoked','Sensitive content clears immediately']
  ];
  rules.forEach((r,i)=>{const cx=84+(i%2)*640,cy=410+Math.floor(i/2)*136;s+=rect(cx,cy,612,112,i%3===1?'#0D1E2C':C.paper,i%3===1?C.lineDark:C.line,1,14)+text(cx+20,cy+36,r[0],16,i%3===1?C.cloud:C.ink,600,'Georgia')+text(cx+20,cy+66,r[1],10,i%3===1?'#BDC6CE':C.muted,500,'Arial')+pill(cx+470,cy+24,'NO MOTION',{fill:i%3===1?'#142A3C':'#F3EEE6',stroke:i%3===1?'#49647A':C.line,ink:i%3===1?C.paleGold:C.goldSafe,w:118,h:26,size:9});});
  s+=text(64,918,'STATIC REDUCED-MOTION EVIDENCE · CSS MEDIA-QUERY AND RUNTIME BEHAVIOR NOT YET VERIFIED',8.5,'#AAB4BD',700,'Arial','start',.35);
  return svgRoot(1440,960,'Owner Home reduced-motion evidence','Static component treatment documenting removal of parallax, shimmer dependence, carousels, reordering animation, and delayed removal.',s);
}

export function finiteBudgetEvidence() {
  const w=1440,h=960;let s=rect(0,0,w,h,'url(#bgNavy)');
  s+=text(54,54,'FINITE HOME CONTRACT · MAXIMUM FIXTURE',9,C.paleGold,750,'Arial','start',1.5)+text(54,104,'Exactly nine product objects. No tenth object.',38,C.cloud,500,'Georgia');
  s+=text(54,134,'My Slate, audience controls, navigation, status, and the bounded remainder path are shell/context—not Home content objects.',10,'#B8C2CB',400,'Arial');
  const items=[
    ['1','Capture action','Always one dominant action'],['2','Review item 1','Owner-owned fixture'],['3','Review item 2','Owner-owned fixture'],['4','Review item 3','Owner-owned fixture'],
    ['5','Recent Moment','One distinct confirmed fixture'],['6','Resurfaced Moment','One different deterministic fixture'],['7','What PeerSlate noticed','One governed-insight fixture'],['8','Connection item','One authorized-relationship fixture'],['9','Next Useful Step','One grounded action fixture']
  ];
  items.forEach((it,i)=>{const cx=54+(i%3)*448,cy=190+Math.floor(i/3)*194;const dark=i===6, warm=i===8;s+=rect(cx,cy,420,166,dark?'url(#dormantNavy)':warm?'url(#warmPanel)':C.paper,dark?C.lineDark:warm?'#C29E4A':C.line,1.2,16);s+=circle(cx+42,cy+45,24,dark?C.marigold:C.navy,'none',0)+text(cx+42,cy+52,it[0],16,dark?C.navy:C.cloud,800,'Arial','middle');s+=text(cx+82,cy+44,it[1],17,dark?C.cloud:C.ink,600,'Georgia');s+=text(cx+82,cy+72,it[2],9,dark?'#BEC8D0':C.muted,500,'Arial');s+=fixturePill(cx+282,cy+112,112);});
  s+=rect(54,794,640,86,C.paper,C.line,1,14)+text(78,827,'One-item fixture',14,C.ink,600,'Georgia')+text(78,853,'1 eligible review renders exactly 1 row · no filler or empty placeholders.',9,C.muted,500,'Arial')+pill(520,818,'1 REVIEW',{fill:'#F3EEE6',stroke:'#BFA979',ink:C.goldSafe,w:146,h:30,size:9});
  s+=rect(714,794,672,86,'#0B1824','#725A30',1,14)+text(738,827,'Over-budget remainder',14,C.cloud,600,'Georgia')+text(738,853,'5 eligible reviews render 3 rows plus one disabled remainder · no fourth card or active route.',9,'#BEC8D0',400,'Arial')+pill(1180,818,'SHELL · NOT OBJECT 10',{fill:'#142A3C',stroke:'#506A80',ink:C.paleGold,w:178,h:30,size:8.5});
  s+=text(54,922,'FUTURE DESIGN FIXTURE · NOT MEMBER DATA · NOT IMPLEMENTED · NOT DEPLOYED · NOT LIVE',8,'#8F9AA5',700,'Arial');
  return svgRoot(w,h,'Finite Home nine-object maximum evidence','Numbered evidence for exactly nine Home objects and one shell-level bounded remainder path.',s);
}
