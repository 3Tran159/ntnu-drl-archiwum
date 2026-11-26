const fs=require('fs'),path=require('path');
const root='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/doc/client/html/star';
const clean=x=>x.replace(/<[^>]+>/g,' ').replaceAll('&nbsp;',' ').replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&').replace(/\s+/g,' ').trim();
for(const arg of process.argv.slice(2)){
const [name,pattern]=arg.split('~'),file=path.join(root,name.replaceAll('.','/')+'.html');
if(!fs.existsSync(file)){console.log('MISSING '+name);continue;}
const s=fs.readFileSync(file,'utf8'); console.log('TYPE '+name+': '+clean(s.match(/<div class="type-signature"[\s\S]*?<\/div>/)?.[0]||''));
for(const m of s.matchAll(/<section class="detail"[^>]*>[\s\S]*?<\/section>/g)){
let x=clean(m[0]); if(!pattern||new RegExp(pattern,'i').test(x))console.log(x.slice(0,2200));
}}