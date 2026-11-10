// Small deterministic renderer for the kernel's own Markdown subset. Raw HTML is always text.
export const escapeHtml = value => String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
function plainText(value) {
  return value.replace(/\\([\\[\]()*_`|])/g,'$1').replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&');
}
function content(value) { return escapeHtml(plainText(value)); }
function cells(line) {
  let s=line.trim(); if(s.startsWith('|'))s=s.slice(1);if(s.endsWith('|'))s=s.slice(0,-1);
  const out=[];let part='',slashes=0;
  for(const char of s){if(char==='|' && slashes%2===0){out.push(part.trim());part='';}else part+=char;slashes=char==='\\'?slashes+1:0;}
  out.push(part.trim());return out;
}
const divider = line => /^\s*\|?[\s:|\-]+\|?\s*$/.test(line) && /---/.test(line);
export function renderSemanticMarkdown(markdown) {
  if(typeof markdown!=='string')throw new TypeError('markdown must be text');
  const lines=markdown.replaceAll('\r','').split('\n'), body=[], toc=[];let i=0,serial=0;
  const heading = line => /^(#{1,3})\s+(.+)$/.exec(line);
  const list = line => /^\s*-\s+(.+)$/.exec(line);
  while(i<lines.length){
    const line=lines[i];if(!line.trim()){i++;continue;}
    const h=heading(line);
    if(h){const level=h[1].length,id='section-'+(++serial);body.push(`<h${level} id="${id}">${content(h[2])}</h${level}>`);if(level===2)toc.push({id,title:plainText(h[2])});i++;continue;}
    if(i+1<lines.length && line.includes('|') && divider(lines[i+1])){
      const headers=cells(line);i+=2;const rows=[];
      while(i<lines.length && lines[i].trim() && lines[i].includes('|')){rows.push(cells(lines[i]));i++;}
      body.push('<div class="table-scroll" role="region" aria-label="研究比较表" tabindex="0"><table><thead><tr>'+headers.map(x=>'<th scope="col">'+content(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+headers.map((_,n)=>'<td>'+content(row[n]||'')+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>');continue;
    }
    if(list(line)){
      const items=[];
      while(i<lines.length && list(lines[i])){const match=list(lines[i]);items.push('<li'+(/^\s{2,}/.test(lines[i])?' class="supporting-detail"':'')+'>'+content(match[1])+'</li>');i++;}
      body.push('<ul>'+items.join('')+'</ul>');continue;
    }
    const paragraphs=[];
    while(i<lines.length && lines[i].trim() && !heading(lines[i]) && !list(lines[i]) && !(i+1<lines.length&&lines[i].includes('|')&&divider(lines[i+1]))){paragraphs.push(content(lines[i]));i++;}
    body.push('<p>'+paragraphs.join('<br>')+'</p>');
  }
  const navigation=toc.length?'<nav class="toc" aria-label="报告目录"><strong>本报告</strong><ol>'+toc.map(x=>'<li><a href="#'+x.id+'">'+escapeHtml(x.title)+'</a></li>').join('')+'</ol></nav>':'';
  return {body:body.join('\n'),navigation,headings:toc,rawHtmlExecuted:false};
}

export const RESEARCH_CSS = `:root{color-scheme:light;--ink:#172c35;--muted:#52656d;--line:#dce5e6;--accent:#087d78}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f6f5;color:var(--ink);font:17px/1.85 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:#006e74;text-decoration-thickness:1px;text-underline-offset:3px}p,li,td,th,a{overflow-wrap:anywhere}.page{max-width:1120px;margin:auto;padding:42px 24px 64px}.brand{color:var(--accent);font-size:13px;letter-spacing:.12em;font-weight:700}.scope-note{border-left:3px solid var(--accent);padding:10px 16px;background:#eaf4f1;color:var(--muted);font-size:14px}.report-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:28px;align-items:start}.toc{position:sticky;top:20px;background:#fff;border:1px solid var(--line);padding:18px;font-size:14px;max-height:85vh;overflow:auto}.toc ol{padding-left:20px}.toc li{margin:7px 0}main{min-width:0;background:#fff;padding:30px 34px;border:1px solid var(--line);border-radius:4px}h1{font-size:clamp(27px,3vw,38px);line-height:1.35;letter-spacing:-.025em;margin:0 0 24px}h2{font-size:23px;line-height:1.5;padding-top:22px;border-top:1px solid var(--line);margin:36px 0 16px;scroll-margin-top:22px}h3{font-size:19px}p{margin:14px 0}ul{padding-left:24px}li{margin:7px 0}.supporting-detail{font-size:14px;color:var(--muted);margin:4px 0;list-style-type:circle}.table-scroll{overflow-x:auto;max-width:100%;border:1px solid var(--line);margin:18px 0}.table-scroll:focus{outline:2px solid var(--accent)}table{border-collapse:collapse;min-width:100%;font-size:14px}td,th{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{background:#edf4f2;font-weight:650}tbody tr:nth-child(even){background:#f8faf9}.audit-table{min-width:1300px}.appendix{margin-top:24px;background:#fff;border:1px solid var(--line);padding:18px}summary{cursor:pointer;font-weight:650}.source-index{padding-left:24px}.footer{color:var(--muted);font-size:13px;margin-top:24px}@media(max-width:760px){.page{padding:24px 12px 36px}.report-layout{display:block}.toc{position:static;max-height:none;margin-bottom:16px}.toc ol{columns:2;column-gap:20px}.toc li{break-inside:avoid}main{padding:22px 18px}h2{font-size:21px}body{font-size:16px}}@media(max-width:420px){.toc ol{columns:1}main{padding:20px 14px}.page{padding-left:9px;padding-right:9px}}@media print{body{background:white}.page{max-width:none;padding:0}.report-layout{display:block}.toc{position:static;max-height:none}main{border:0;padding:0}.table-scroll{overflow:visible}h2{break-after:avoid}p,li{orphans:3;widows:3}}`;
