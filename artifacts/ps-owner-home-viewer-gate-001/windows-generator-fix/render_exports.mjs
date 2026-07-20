import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';

const require=createRequire(import.meta.url);
const sharp=require('sharp');

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.dirname(here);
const out=path.join(root,'exports');
const atmosphere=`data:image/png;base64,${fs.readFileSync(path.join(root,'assets','owner-home-alpine-atmosphere.png')).toString('base64')}`;
const svgs=fs.readdirSync(out).filter(name=>name.endsWith('.svg')).sort();

for(const name of svgs){
  const source=path.join(out,name);
  const target=path.join(out,name.replace(/\.svg$/,'.png'));
  const temporary=`${target}.rendering`;
  const svg=fs.readFileSync(source,'utf8').replaceAll('href="../assets/owner-home-alpine-atmosphere.png"',`href="${atmosphere}"`);
  await sharp(Buffer.from(svg),{density:72}).png().toFile(temporary);
  fs.renameSync(temporary,target);
}

console.log(`Rendered ${svgs.length} PNG review exports.`);
