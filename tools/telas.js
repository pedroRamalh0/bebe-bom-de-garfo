// Gera telas 1080x1920 com páginas REAIS do Bebê Bom de Garfo (cartão grande, celular e toque no sumário).
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
const R=path.join(__dirname,'..','telas'),P=path.join(R,'paginas');
const u=f=>'data:image/png;base64,'+fs.readFileSync(path.join(P,f)).toString('base64');
const logo='data:image/png;base64,'+fs.readFileSync(path.join(__dirname,'assets','logo.png')).toString('base64');
const bg=`background:radial-gradient(circle at 50% 40%,#FFFDF7,#F3E9D8 70%,#EADCC4)`;
const card=(img,extra='')=>`<div style="position:absolute;left:90px;top:210px;width:900px;border-radius:26px;overflow:hidden;box-shadow:0 40px 80px -24px rgba(23,68,42,.45),0 0 0 1px rgba(23,68,42,.08)"><img src="${u(img)}" style="display:block;width:100%">${extra}</div>`;
const tap=`<div style="position:absolute;left:3%;top:24.2%;width:94%;height:9.6%;border-radius:18px;background:rgba(232,115,28,.22);box-shadow:0 0 0 5px #E8731C inset"></div>
<div style="position:absolute;left:58%;top:29.5%;font-size:150px;line-height:1;filter:drop-shadow(0 10px 12px rgba(0,0,0,.3));font-family:'Noto Color Emoji'">👆</div>`;
const phone=(img,label)=>`<div style="position:absolute;left:170px;top:150px;width:740px;height:1560px;border-radius:90px;background:#1B1F1D;padding:20px;box-shadow:0 50px 90px -20px rgba(0,0,0,.45)">
<div style="width:100%;height:100%;border-radius:72px;overflow:hidden;background:#FFFDF7;position:relative">
<div style="height:200px;background:#17442A;display:flex;align-items:flex-end;justify-content:center;padding-bottom:22px"><img src="${logo}" style="height:64px;filter:brightness(0) invert(1)"></div>
<div style="padding:14px 26px;font:700 28px 'DM Sans',sans-serif;color:#17442A;background:#EAF4EC">${label}</div>
<img src="${u(img)}" style="display:block;width:100%">
<div style="position:absolute;top:18px;left:50%;transform:translateX(-50%);width:170px;height:40px;border-radius:22px;background:#1B1F1D"></div></div></div>`;
const shots={
 'cardapio-6m':card('cardapio-6m-03.png'),'cardapio-7a8m':card('cardapio-7a8m-05.png'),'cardapio-9a11m':card('cardapio-9a11m-07.png'),'compras-6m':card('compras-6m-03.png'),
 'cortes':card('cortes-3.png'),'sos-capa':card('sos-01.png'),'sos-pagina':card('sos-02.png'),
 'alerg-capa':card('alerg-capa-1.png'),'alerg-pagina':card('alerg-p3-3.png'),
 'sumario':card('sumario-003.png'),'sumario-toque':card('sumario-003.png',tap),
 'fase2':card('fase2-001.png'),'fase2-receita':card('fase2-002.png'),'receita-1a3':card('receita-e.png'),
 'celular-receita':phone('receita-b.png','Fase 2 · 7 a 8 meses'),
};
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
for(const [k,html] of Object.entries(shots)){
 await p.setContent(`<html><head><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@700&display=block" rel="stylesheet"></head><body style="margin:0;width:1080px;height:1920px;${bg};position:relative;overflow:hidden">${html}<script>document.fonts.ready.then(()=>window.r=1)</script></body></html>`);
 await p.waitForFunction(()=>window.r);await p.waitForTimeout(200);await p.screenshot({path:path.join(R,k+'.png')});console.log(k);}
await b.close();})();
