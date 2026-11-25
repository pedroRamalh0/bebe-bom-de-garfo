// Gera a tela final (1080x1920 PNG): logo, kit 3D, oferta e botão. Uso: node tools/endcard.js
const fs = require("fs"), path = require("path"), { chromium } = require("playwright");
const A = path.join(__dirname, "assets");
const b64 = (f) => "data:image/png;base64," + fs.readFileSync(path.join(A, f)).toString("base64");
const html = `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,600;1,9..144,500&family=DM+Sans:wght@500;700;800&display=block" rel="stylesheet">
<style>*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;background:radial-gradient(circle at 50% 42%,#FFFDF7 0,#F6EEE1 60%,#EDE0CB 100%);font-family:"DM Sans";color:#17442A;display:flex;flex-direction:column;align-items:center;padding-top:150px}
.logo{height:118px}.k{font-size:30px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:#E0661F;margin-top:56px}
h1{font-family:Fraunces;font-weight:600;font-size:96px;line-height:1;text-align:center;margin-top:14px;letter-spacing:-.02em}h1 em{font-style:italic;font-weight:500;color:#E0661F}
.kit{width:980px;margin-top:30px;filter:drop-shadow(0 30px 40px rgba(40,40,20,.18))}
.price{display:flex;align-items:baseline;gap:18px;margin-top:10px}.old{font-size:40px;color:#8A7F70;text-decoration:line-through}.new{font-family:Fraunces;font-size:120px;font-weight:600;color:#2E9E5B}
.btn{margin-top:34px;padding:34px 70px;border-radius:999px;background:#E8731C;color:#fff;font-size:50px;font-weight:800;box-shadow:0 12px 0 #B5520F,0 26px 40px rgba(232,115,28,.35)}
.s{margin-top:34px;font-size:30px;font-weight:700;color:#5E6E64}</style></head><body>
<img class="logo" src="${b64("logo.png")}">
<div class="k">Do 1º purê aos 3 anos</div>
<h1>300 receitinhas<br><em>separadas por idade</em></h1>
<img class="kit" src="${b64("kit-completo.png")}">
<div class="price"><span class="old">R$185</span><span class="new">R$27,90</span></div>
<div class="btn">TOQUE EM SAIBA MAIS 👇</div>
<div class="s">Acesso imediato · Garantia de 30 dias</div>
<script>document.fonts.ready.then(()=>window.__r=1)</script></body></html>`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.setContent(html, { waitUntil: "networkidle" }); await p.waitForFunction(() => window.__r);
  await p.screenshot({ path: path.join(A, "endcard.png") });
  // cartão de apresentação do produto (sem preço) para o meio do vídeo
  await p.evaluate(() => { document.querySelector(".price").remove(); document.querySelector(".btn").remove(); document.querySelector(".s").remove(); document.querySelector(".k").textContent = "Indicado por uma amiga"; document.querySelector(".kit").style.marginTop = "80px"; });
  await p.screenshot({ path: path.join(A, "reveal.png") });
  await b.close(); console.log("ok");
})();
