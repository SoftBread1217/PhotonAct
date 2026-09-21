# ruff: noqa: E501
"""Generate a local, self-contained interactive curve explorer."""

from __future__ import annotations

import csv
import json
import webbrowser
from math import isfinite
from pathlib import Path
from typing import Any

from photonact.curves import CurveData, load_curve


def _read_optional_quantity(path: Path, name: str) -> tuple[float, ...] | None:
    """Read an optional numeric point field while preserving source order."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as stream:
            points: Any = list(csv.DictReader(stream))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        points = payload if isinstance(payload, list) else payload.get("points", [])
    if not points or any(name not in point or point[name] in (None, "") for point in points):
        return None
    try:
        values = tuple(float(point[name]) for point in points)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Optional {name!r} values must be numeric") from error
    if not all(isfinite(value) for value in values):
        raise ValueError(f"Optional {name!r} values must be finite")
    return values


def _quantity_payload(
    curve: CurveData,
    values: tuple[float, ...],
    *,
    label: str,
    label_zh: str,
    unit: str,
) -> dict[str, Any]:
    branches: dict[str, list[list[float]]] = {"up": [], "down": []}
    for input_power, value, branch in zip(curve.input_power, values, curve.branch, strict=True):
        if branch in branches:
            branches[branch].append([input_power, value])
    return {"label": label, "label_zh": label_zh, "unit": unit, "branches": branches}


def build_demo_payload(path: str | Path) -> dict[str, Any]:
    """Load a hysteresis curve and return the browser-demo payload."""
    curve_path = Path(path)
    curve = load_curve(curve_path)
    present = set(curve.branch)
    if not {"up", "down"}.issubset(present):
        raise ValueError("The demo requires explicit 'up' and 'down' branches")
    metadata = curve.metadata
    if metadata.lower_threshold is None or metadata.upper_threshold is None:
        raise ValueError("The demo requires lower_threshold and upper_threshold metadata")

    quantities: dict[str, dict[str, Any]] = {
        "output_power": _quantity_payload(
            curve,
            curve.output_power,
            label="Output power",
            label_zh="输出功率",
            unit=metadata.output_unit,
        )
    }
    transmittance = _read_optional_quantity(curve_path, "transmittance")
    if transmittance is not None:
        if len(transmittance) != len(curve.input_power):
            raise ValueError("Optional transmittance values must align with curve points")
        quantities["transmittance"] = _quantity_payload(
            curve,
            transmittance,
            label="Power transmittance",
            label_zh="功率透射率",
            unit="dimensionless",
        )
    return {
        "file_name": curve_path.name,
        "metadata": metadata.to_dict(),
        "quantities": quantities,
    }


def _json_for_html(payload: dict[str, Any]) -> str:
    """Serialize JSON without allowing data to terminate the script element."""
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_demo(path: str | Path, output: str | Path) -> Path:
    """Write a self-contained HTML explorer and return its resolved path."""
    output_path = Path(output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _HTML_TEMPLATE.replace("__PHOTONACT_PAYLOAD__", _json_for_html(build_demo_payload(path)))
    output_path.write_text(html, encoding="utf-8")
    return output_path


def open_demo(path: str | Path) -> bool:
    """Open a generated demo in the default browser."""
    return webbrowser.open(Path(path).resolve().as_uri())


_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>PhotonAct 本地曲线体验器</title>
  <style>
    :root{color-scheme:light;--ink:#12213f;--muted:#68738a;--line:#dce2ee;--up:#4169e1;--down:#14a47b;--hot:#ef6c57;--panel:#fff;--wash:#f4f7fb}
    *{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#edf3ff,#fbfcff 48%,#edf9f5);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
    main{max-width:1180px;margin:0 auto;padding:36px 22px 52px}header{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin-bottom:22px}h1{font-size:clamp(28px,4vw,46px);line-height:1.04;margin:0 0 9px;letter-spacing:-.035em}header p{margin:0;color:var(--muted);max-width:700px}.badge{white-space:nowrap;border:1px solid #b9c8ea;background:#eef3ff;border-radius:999px;padding:7px 12px;color:#2b4b9c;font-weight:700;font-size:12px}.layout{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(290px,.8fr);gap:18px}.card{background:rgba(255,255,255,.92);border:1px solid var(--line);border-radius:22px;box-shadow:0 18px 48px rgba(42,61,98,.1)}.chart-card{padding:20px}.side{padding:20px;display:flex;flex-direction:column;gap:16px}.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}.toolbar label{color:var(--muted);font-size:13px}.toolbar select,.toolbar button{border:1px solid #c9d2e2;border-radius:10px;background:#fff;color:var(--ink);padding:8px 11px;font:inherit}.toolbar button{cursor:pointer;font-weight:650}.toolbar button.primary{background:var(--ink);color:#fff;border-color:var(--ink)}svg{display:block;width:100%;height:auto;min-height:420px}.grid{stroke:#e8ecf3;stroke-width:1}.axis{stroke:#94a0b6;stroke-width:1.2}.threshold{stroke:var(--hot);stroke-dasharray:6 5;stroke-width:1.4}.curve{fill:none;stroke-width:3;stroke-linejoin:round;stroke-linecap:round}.curve.up{stroke:var(--up)}.curve.down{stroke:var(--down)}.marker{fill:#fff;stroke:var(--ink);stroke-width:3}.axis-label,.tick{fill:#6b7589;font-size:12px}.threshold-label{fill:#b34a38;font-size:11px;font-weight:700}.legend{display:flex;gap:18px;color:var(--muted);font-size:13px;margin-top:4px}.swatch{display:inline-block;width:22px;height:3px;border-radius:5px;vertical-align:middle;margin-right:7px}.control label{display:flex;justify-content:space-between;font-weight:700;margin-bottom:8px}.control input{width:100%;accent-color:var(--up)}.reading{display:grid;grid-template-columns:1fr 1fr;gap:10px}.metric{background:var(--wash);border-radius:14px;padding:12px}.metric span{display:block;color:var(--muted);font-size:12px}.metric strong{font-size:18px}.state{grid-column:1/-1}.state strong{color:var(--up)}.state.high strong{color:var(--down)}.meta{border-top:1px solid var(--line);padding-top:14px}.meta h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 8px}.meta dl{display:grid;grid-template-columns:86px 1fr;gap:6px 10px;margin:0;font-size:13px}.meta dt{color:var(--muted)}.meta dd{margin:0;overflow-wrap:anywhere}.notice{margin-top:18px;padding:14px 17px;border:1px solid #efdca8;background:#fff9e8;border-radius:14px;color:#64552c;font-size:13px}.notice strong{color:#493c1b}@media(max-width:800px){header{align-items:flex-start;flex-direction:column}.layout{grid-template-columns:1fr}svg{min-height:330px}}
  </style>
</head>
<body>
<main>
  <header>
    <div><h1>PhotonAct 本地曲线体验器</h1><p>拖动输入功率，观察上下扫描分支、阈值切换和显式双稳态。所有计算都在本页本地完成。</p></div>
    <div class="badge" id="dataKind">LOCAL CURVE</div>
  </header>
  <section class="layout">
    <div class="card chart-card">
      <div class="toolbar">
        <label for="quantity">纵轴</label><select id="quantity"></select>
        <button class="primary" id="scan">自动扫描一圈</button><button id="reset">重置低态</button>
      </div>
      <svg id="plot" viewBox="0 0 760 470" role="img" aria-label="双稳态响应曲线"></svg>
      <div class="legend"><span><i class="swatch" style="background:var(--up)"></i>上升扫描 / 低态</span><span><i class="swatch" style="background:var(--down)"></i>下降扫描 / 高态</span></div>
    </div>
    <aside class="card side">
      <div class="control"><label for="power"><span>输入功率</span><output id="inputValue"></output></label><input id="power" type="range" step="any"></div>
      <div class="reading">
        <div class="metric"><span id="responseLabel">当前输出功率</span><strong id="outputValue"></strong></div>
        <div class="metric"><span>当前分支</span><strong id="branchValue"></strong></div>
        <div class="metric state" id="stateCard"><span>当前状态</span><strong id="stateValue"></strong></div>
        <div class="metric"><span>下降阈值</span><strong id="lowerValue"></strong></div>
        <div class="metric"><span>上升阈值</span><strong id="upperValue"></strong></div>
      </div>
      <div class="meta"><h2>曲线信息</h2><dl id="metadata"></dl></div>
    </aside>
  </section>
  <div class="notice"><strong>数据边界：</strong>这个 HTML 内嵌了曲线点，分享它等于分享源数据。请遵守页面中显示的数据许可证；关闭页面不会上传任何数据。</div>
</main>
<script id="photonact-data" type="application/json">__PHOTONACT_PAYLOAD__</script>
<script>
const payload=JSON.parse(document.getElementById('photonact-data').textContent);
const meta=payload.metadata, quantities=payload.quantities;
const svg=document.getElementById('plot'), slider=document.getElementById('power');
const quantitySelect=document.getElementById('quantity');
let state=false, timer=null, scanDirection=1;
const margin={left:72,right:24,top:24,bottom:58}, W=760,H=470;
const ns='http://www.w3.org/2000/svg';
function fmt(v){if(!Number.isFinite(v))return '—';const a=Math.abs(v);return (a>=100||a<.001&&a!==0)?v.toExponential(3):Number(v.toPrecision(5)).toString()}
function el(name,attrs={},text=''){const node=document.createElementNS(ns,name);for(const[k,v]of Object.entries(attrs))node.setAttribute(k,v);if(text)node.textContent=text;return node}
function interpolate(points,x){if(x<=points[0][0])return points[0][1];if(x>=points.at(-1)[0])return points.at(-1)[1];let lo=0,hi=points.length-1;while(hi-lo>1){const m=(lo+hi)>>1;if(points[m][0]<=x)lo=m;else hi=m}const[a,b]=[points[lo],points[hi]],t=(x-a[0])/(b[0]-a[0]);return a[1]+t*(b[1]-a[1])}
function scales(quantity){const all=[...quantity.branches.up,...quantity.branches.down],xs=all.map(p=>p[0]),ys=all.map(p=>p[1]);const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(0,...ys),ymax=Math.max(...ys);return{xmin,xmax,ymin,ymax,px:x=>margin.left+(x-xmin)/(xmax-xmin)*(W-margin.left-margin.right),py:y=>H-margin.bottom-(y-ymin)/(ymax-ymin||1)*(H-margin.top-margin.bottom)}}
function path(points,s){return points.map((p,i)=>(i?'L':'M')+s.px(p[0]).toFixed(2)+','+s.py(p[1]).toFixed(2)).join(' ')}
function render(){const key=quantitySelect.value,q=quantities[key],s=scales(q);svg.replaceChildren();for(let i=0;i<=5;i++){const x=s.xmin+(s.xmax-s.xmin)*i/5,y=s.ymin+(s.ymax-s.ymin)*i/5;svg.append(el('line',{class:'grid',x1:s.px(x),x2:s.px(x),y1:margin.top,y2:H-margin.bottom}));svg.append(el('line',{class:'grid',x1:margin.left,x2:W-margin.right,y1:s.py(y),y2:s.py(y)}));svg.append(el('text',{class:'tick','text-anchor':'middle',x:s.px(x),y:H-margin.bottom+23},fmt(x)));svg.append(el('text',{class:'tick','text-anchor':'end',x:margin.left-10,y:s.py(y)+4},fmt(y)))}svg.append(el('line',{class:'axis',x1:margin.left,x2:W-margin.right,y1:H-margin.bottom,y2:H-margin.bottom}));svg.append(el('line',{class:'axis',x1:margin.left,x2:margin.left,y1:margin.top,y2:H-margin.bottom}));for(const[t,label]of[[meta.lower_threshold,'下降阈值'],[meta.upper_threshold,'上升阈值']]){svg.append(el('line',{class:'threshold',x1:s.px(t),x2:s.px(t),y1:margin.top,y2:H-margin.bottom}));svg.append(el('text',{class:'threshold-label','text-anchor':'middle',x:s.px(t),y:margin.top+12},label))}svg.append(el('path',{class:'curve up',d:path(q.branches.up,s)}));svg.append(el('path',{class:'curve down',d:path(q.branches.down,s)}));svg.append(el('text',{class:'axis-label','text-anchor':'middle',x:(margin.left+W-margin.right)/2,y:H-12},'输入功率 ('+meta.input_unit+')'));svg.append(el('text',{class:'axis-label','text-anchor':'middle',transform:'rotate(-90 18 220)',x:18,y:220},(q.label_zh||q.label)+' ('+q.unit+')'));const x=Number(slider.value),branch=state?'down':'up',y=interpolate(q.branches[branch],x);svg.append(el('circle',{class:'marker',cx:s.px(x),cy:s.py(y),r:7}));document.getElementById('inputValue').textContent=fmt(x)+' '+meta.input_unit;document.getElementById('responseLabel').textContent='当前'+(q.label_zh||q.label);document.getElementById('outputValue').textContent=fmt(y)+' '+q.unit;document.getElementById('branchValue').textContent=branch+(state?'（下降）':'（上升）');document.getElementById('stateValue').textContent=state?'高态':'低态';document.getElementById('stateCard').classList.toggle('high',state)}
function updateState(){const x=Number(slider.value);if(x>=meta.upper_threshold)state=true;else if(x<=meta.lower_threshold)state=false;render()}
function stop(){if(timer){clearInterval(timer);timer=null;document.getElementById('scan').textContent='自动扫描一圈'}}
for(const[key,q]of Object.entries(quantities)){const option=document.createElement('option');option.value=key;option.textContent=q.label_zh||q.label;quantitySelect.append(option)}
const base=quantities.output_power.branches.up, xmin=base[0][0],xmax=base.at(-1)[0];slider.min=xmin;slider.max=xmax;slider.step=(xmax-xmin)/1000;slider.value=xmin;
document.getElementById('lowerValue').textContent=fmt(meta.lower_threshold)+' '+meta.input_unit;document.getElementById('upperValue').textContent=fmt(meta.upper_threshold)+' '+meta.input_unit;document.getElementById('dataKind').textContent=(meta.data_kind||'local')+' · '+payload.file_name;
const fields=[['名称',meta.name],['波长',meta.wavelength_nm?meta.wavelength_nm+' nm':'未提供'],['偏振',meta.polarization||'未提供'],['来源',meta.source],['许可证',meta.license]];const dl=document.getElementById('metadata');for(const[k,v]of fields){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=v;dl.append(dt,dd)}
slider.addEventListener('input',()=>{stop();updateState()});quantitySelect.addEventListener('change',render);document.getElementById('reset').addEventListener('click',()=>{stop();state=false;slider.value=xmin;render()});document.getElementById('scan').addEventListener('click',()=>{if(timer){stop();return}state=false;slider.value=xmin;scanDirection=1;document.getElementById('scan').textContent='停止扫描';timer=setInterval(()=>{let value=Number(slider.value)+scanDirection*(xmax-xmin)/180;if(value>=xmax){value=xmax;scanDirection=-1}else if(value<=xmin&&scanDirection<0){value=xmin;slider.value=value;updateState();stop();return}slider.value=value;updateState()},24)});
render();
</script>
</body>
</html>
"""
