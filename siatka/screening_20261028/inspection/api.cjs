const fs=require('fs'),p=require('path');
const root='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/doc/client/html/star';
for(const name of process.argv.slice(2)){
 const file=p.join(root,name.replaceAll('.','/')+'.html');
 if(!fs.existsSync(file)){console.log('MISSING '+name);continue;}
 const s=fs.readFileSync(file,'utf8');
 const section=s.match(/<section class="method-summary"[\s\S]*?<\/section>/)?.[0]||'';
 const clean=section.replace(/<[^>]+>/g,' ').replaceAll('&nbsp;',' ').replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&').replace(/\s+/g,' ').split('Methods inherited')[0];
 console.log(name+': '+clean);
}

for(const name of process.argv.slice(2)){
 const file=p.join(root,name.replaceAll('.','/')+'.html');if(!fs.existsSync(file))continue;
 const s=fs.readFileSync(file,'utf8');const t=s.match(/<div class="type-signature"[\s\S]*?<\/div>/)?.[0]||'';
 console.log('TYPE '+name+': '+t.replace(/<[^>]+>/g,' ').replace(/\s+/g,' '));
}
