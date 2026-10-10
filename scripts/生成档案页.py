"""
由藏品库派生档案页（图鉴 + 稀缺度榜 + 可下载海报）。

单一数据源原则：本脚本只读 data/藏品库.json，输出视图，不反向写库。

用法：python 生成档案页.py
输出：视图/藏品档案.html
"""

import sys
import json
import os
import html

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "藏品库.json")
OUT_DIR = os.path.join(ROOT, "视图")
OUT_PATH = os.path.join(OUT_DIR, "藏品档案.html")

STATUS_CLASS = {"在售": "s-on", "预热": "s-soon", "售罄": "s-out", "已结束": "s-end", "未知": "s-end"}
SRC_NAME = {"mcp_calendar": "活动日历", "mcp_mall": "积分商城", "manual": "人工补录"}


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def si_bar(score):
    pct = max(0, min(100, score or 0))
    return f'<div class="sibar" aria-hidden="true"><span style="width:{pct}%"></span></div>'


def cost_text(it):
    c = it.get("acquire_cost")
    u = it.get("acquire_cost_unit")
    if c is None:
        return "待核实"
    return f"{c} 元" if u == "cny" else f"{c} 积分"


# 获取方式 → 官方操作路径（仅作指路，MCP 不提供商品页链接，无法直接跳转）
PATH_BY_METHOD = {
    "加价购": "麦当劳 APP 或门店点餐 → 任意餐品下单 → 加价购加购",
    "积分兑换": "麦当劳 APP → 麦麦商城 → 积分兑换",
    "消费赠送": "麦当劳 APP → 对应活动页面",
    "抽奖": "麦当劳 APP → 活动页面参与抽奖",
    "买赠": "麦当劳 APP 或门店点餐 → 参与活动",
}


def obtain_path(it):
    """仅对在售/预热藏品给出获取路径；已结束/售罄的给路径会误导。"""
    if it.get("status") not in ("在售", "预热"):
        return None
    return it.get("obtain_path") or PATH_BY_METHOD.get(it.get("acquire_method"))


def card(it, idx):
    name = esc(it.get("name"))
    cat = esc(it.get("category"))
    img = it.get("image_local") or it.get("image_url")
    if img:
        thumb = (
            f'<div class="thumb" data-label="{cat}">'
            f'<img src="{esc(img)}" alt="{name}" loading="lazy" '
            f"onerror=\"this.parentNode.classList.add('noimg')\"></div>"
        )
    else:
        thumb = f'<div class="thumb noimg" data-label="{cat}"></div>'
    sc = it.get("si_score") or 0
    st = it.get("status") or "未知"
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in (it.get("tags") or []))
    ip = it.get("ip_collab")
    ip_line = f'<div class="kv"><span>联名</span><b>{esc(ip)}</b></div>' if ip else ""
    path = obtain_path(it)
    path_block = (
        f'<div class="path"><span class="plabel">怎么拿</span>'
        f'<span class="ptext">{esc(path)}</span>'
        f'<button class="copybtn" type="button" aria-label="复制获取路径">复制</button></div>'
    ) if path else ""
    return f'''      <article class="card" tabindex="0" data-idx="{idx}">
        {thumb}
        <div class="body">
          <div class="cardtop">
            <span class="status {STATUS_CLASS.get(st, 's-end')}">{esc(st)}</span>
            <span class="si">SI {sc}</span>
          </div>
          <h3>{name}</h3>
          <div class="kv"><span>发售</span><b>{esc(it.get("release_date"))}</b></div>
          <div class="kv"><span>方式</span><b>{esc(it.get("acquire_method"))} · {cost_text(it)}</b></div>
          {ip_line}
          {path_block}
          {si_bar(sc)}
          <div class="tags">{tags}</div>
          <div class="src">来源：{esc(SRC_NAME.get(it.get("source"), it.get("source")))}</div>
        </div>
      </article>'''


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    items = db.get("藏品", [])
    items_sorted = sorted(items, key=lambda x: -(x.get("si_score") or 0))

    rows = []
    for i, it in enumerate(items_sorted, 1):
        st = it.get("status") or "未知"
        rows.append(
            f'<li><span class="rank">{i:02d}</span>'
            f'<span class="rname">{esc(it.get("name"))}</span>'
            f'<span class="status {STATUS_CLASS.get(st, "s-end")}">{esc(st)}</span>'
            f'<span class="rsi">{it.get("si_score")}</span></li>'
        )
    board = "\n".join(rows)
    cards = "\n".join(card(it, i) for i, it in enumerate(items_sorted))

    # 海报用数据（纯文本，不含外部图片，避免 canvas 跨域污染）
    poster_data = [
        {
            "name": it.get("name"),
            "si": it.get("si_score") or 0,
            "status": it.get("status") or "未知",
            "cost": cost_text(it),
            "date": it.get("release_date"),
            "path": obtain_path(it),
            "limit": it.get("limited_text") or "无明确限量说明",
        }
        for it in items_sorted
    ]

    src_count = {}
    for it in items:
        src_count[it.get("source")] = src_count.get(it.get("source"), 0) + 1
    meta = db.get("_meta", {})
    updated = esc(meta.get("最后更新"))
    total = len(items)

    head = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="麦当劳中国周边藏品档案：发售历史、获取方式与稀缺度记录。">
<title>麦门藏经阁 · 麦当劳中国周边藏品档案</title>
<style>
  :root{
    --bg:#0f0d0c; --panel:#1a1614; --panel2:#221c19; --line:#2e2622;
    --text:#f4efe9; --dim:#a99e95; --faint:#6f6560;
    --red:#da291c; --yellow:#ffc72c;
  }
  *{box-sizing:border-box}
  html{-webkit-text-size-adjust:100%}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:"PingFang SC","Microsoft YaHei",system-ui,-apple-system,sans-serif;
    line-height:1.6;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1120px;margin:0 auto;padding:44px 22px 80px}
  /* 头部 */
  .eyebrow{color:var(--yellow);font-size:12px;letter-spacing:.32em;text-transform:uppercase;margin:0 0 14px}
  h1{margin:0;font-size:clamp(28px,5vw,42px);line-height:1.18;letter-spacing:-.01em;font-weight:800}
  .hook{margin:14px 0 0;font-size:clamp(15px,2.4vw,18px);color:#e9d9c8}
  .hook b{color:var(--yellow)}
  .sub{color:var(--dim);margin:14px 0 0;max-width:680px;font-size:14px}
  .actions{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0 0}
  button{font:inherit;font-size:14px;padding:11px 20px;border-radius:999px;cursor:pointer;
    border:1px solid var(--line);background:var(--panel);color:var(--text);transition:.18s}
  button:hover{border-color:#4a3b33;background:var(--panel2)}
  button.primary{background:linear-gradient(135deg,var(--red),#b51f14);border-color:transparent;font-weight:700}
  button.primary:hover{filter:brightness(1.08)}
  button:focus-visible{outline:2px solid var(--yellow);outline-offset:2px}
  .toast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,16px);opacity:0;pointer-events:none;
    background:#2a221e;border:1px solid var(--line);color:var(--text);padding:10px 18px;border-radius:10px;
    font-size:14px;transition:.24s;z-index:50}
  .toast.on{opacity:1;transform:translate(-50%,0)}
  .stats{display:flex;flex-wrap:wrap;justify-content:space-between;gap:14px;margin:30px 0 0;
    padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
  .stats div{font-size:12px;color:var(--dim);min-width:80px}
  .stats b{display:block;font-size:24px;color:var(--text);font-weight:800;margin-top:2px;
    font-variant-numeric:tabular-nums}
  h2{font-size:13px;letter-spacing:.24em;color:var(--dim);text-transform:uppercase;margin:52px 0 18px;font-weight:700}
  h2 .hint{letter-spacing:0;text-transform:none;color:var(--faint);margin-left:10px;font-weight:400;font-size:12px}
  /* 榜单 */
  ol.board{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
  ol.board li{display:grid;grid-template-columns:54px 1fr auto 58px;gap:16px;align-items:center;
    padding:16px 10px;border-bottom:1px solid var(--line);transition:background .15s}
  ol.board li:hover{background:var(--panel)}
  .rank{font-variant-numeric:tabular-nums;color:var(--faint);font-size:15px}
  ol.board li:nth-child(1) .rank,ol.board li:nth-child(2) .rank,ol.board li:nth-child(3) .rank{color:var(--yellow);font-weight:700}
  .rname{font-size:16px}
  .rsi{font-variant-numeric:tabular-nums;text-align:right;color:var(--yellow);font-weight:800;font-size:17px}
  /* 图鉴 */
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(266px,1fr));gap:18px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:15px;overflow:hidden;
    display:flex;flex-direction:column;cursor:pointer;transition:.18s}
  .card:hover{transform:translateY(-3px);border-color:#453730;box-shadow:0 14px 34px -18px rgba(0,0,0,.9)}
  .card:focus-visible{outline:2px solid var(--yellow);outline-offset:2px}
  .thumb{position:relative;aspect-ratio:16/10;background:#0c0a09;display:flex;align-items:center;justify-content:center;overflow:hidden}
  .thumb img{width:100%;height:100%;object-fit:cover;display:block}
  .thumb.noimg::before{content:attr(data-label);color:#463a33;font-size:30px;font-weight:800;letter-spacing:.22em}
  .body{padding:15px 16px 17px;display:flex;flex-direction:column;gap:8px;flex:1}
  .cardtop{display:flex;justify-content:space-between;align-items:center}
  .status{font-size:12px;padding:2px 9px;border-radius:999px;border:1px solid var(--line);color:var(--dim);white-space:nowrap}
  .s-on{color:#8fd694;border-color:#2f5a36;background:#16241a}
  .s-soon{color:#ffd76a;border-color:#5c4a1c;background:#241f12}
  .s-out{color:#ff8a7a;border-color:#5e2a24;background:#241312}
  .s-end{color:#8f8380;border-color:#332c28;background:#1b1613}
  .si{font-size:12px;color:var(--yellow);font-weight:800;font-variant-numeric:tabular-nums}
  .card h3{margin:2px 0 4px;font-size:16.5px;line-height:1.36}
  .kv{display:flex;justify-content:space-between;font-size:13px;color:var(--dim);gap:12px}
  .kv b{color:var(--text);font-weight:500;text-align:right}
  .sibar{height:4px;background:#2a2320;border-radius:2px;overflow:hidden;margin-top:6px}
  .sibar span{display:block;height:100%;background:linear-gradient(90deg,var(--red),var(--yellow))}
  /* 获取路径 */
  .path{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px;padding:8px 10px;
    background:#1d1714;border:1px solid #332a24;border-left:3px solid var(--red);border-radius:8px}
  .plabel{font-size:11px;color:var(--yellow);white-space:nowrap;font-weight:700}
  .ptext{font-size:12px;color:#d3c7bd;flex:1;min-width:120px;line-height:1.5}
  .copybtn{font-size:11px;padding:3px 10px;border-radius:6px;border:1px solid #453730;
    background:#241d19;color:var(--text);cursor:pointer;transition:.15s;white-space:nowrap}
  .copybtn:hover{background:#312721;border-color:#5a463c}
  .copybtn:focus-visible{outline:2px solid var(--yellow);outline-offset:1px}
  /* 复制降级层（自动复制被浏览器/iframe 权限阻止时使用） */
  .copylayer{position:fixed;inset:0;background:rgba(10,8,7,.88);backdrop-filter:blur(6px);display:none;
    align-items:center;justify-content:center;padding:24px;z-index:70}
  .copylayer.on{display:flex}
  .copybox{max-width:520px;width:100%;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px}
  .copybox p{margin:0 0 12px;font-size:14px;color:var(--dim);line-height:1.75}
  .copybox p b{color:var(--yellow)}
  #copyArea{width:100%;height:118px;resize:vertical;background:#120f0d;color:var(--text);
    border:1px solid var(--line);border-radius:10px;padding:12px;font:inherit;font-size:13px;line-height:1.65}
  #copyArea:focus{outline:2px solid var(--yellow);outline-offset:1px}
  #copyClose{margin-top:14px;width:100%}
  .tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
  .tag{font-size:11px;color:var(--dim);border:1px solid var(--line);border-radius:6px;padding:1px 7px}
  .src{font-size:11px;color:var(--faint);margin-top:auto;padding-top:8px}
  /* 模态 */
  .modal{position:fixed;inset:0;background:rgba(10,8,7,.86);backdrop-filter:blur(6px);display:none;
    align-items:center;justify-content:center;padding:24px;z-index:60}
  .modal.on{display:flex}
  .modal-inner{max-width:440px;width:100%;background:var(--panel);border:1px solid var(--line);
    border-radius:18px;overflow:hidden}
  .modal-inner img{width:100%;aspect-ratio:16/10;object-fit:cover;background:#0c0a09}
  .modal-body{padding:22px}
  .modal-body h3{margin:0 0 12px;font-size:20px;line-height:1.35}
  .modal-body .row{display:flex;justify-content:space-between;font-size:14px;color:var(--dim);padding:5px 0;border-bottom:1px dashed var(--line)}
  .modal-body .row b{color:var(--text);font-weight:500}
  .modal-close{margin-top:18px;width:100%}
  footer{margin-top:60px;padding-top:24px;border-top:1px solid var(--line);color:var(--dim);font-size:13px}
  .note{color:#d7ccc2;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--yellow);
    border-radius:10px;padding:15px 17px;margin-bottom:16px;line-height:1.7}
  .note b{color:var(--yellow)}
  @media (max-width:560px){
    .wrap{padding:30px 15px 64px}
    ol.board li{grid-template-columns:38px 1fr auto;gap:10px}
    ol.board li .status{display:none}
    .stats{gap:14px}
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow">麦门藏经阁 &middot; Merch Archive</p>
    <h1>麦门藏经阁</h1>
    <p class="hook">抢不到会遗憾，<b>不知道才最遗憾</b>。</p>
    <p class="sub">麦当劳中国周边 / 联名藏品档案 —— 一档可查、可比、可追溯的藏品记录。数据来自麦当劳官方活动日历与积分商城（MCP 实测采集），历史条目为人工补录并单独标注来源。</p>
    <div class="actions">
      <button class="primary" id="btnPoster">生成榜单海报</button>
      <button id="btnCopy">复制榜单文字</button>
    </div>
  </header>
"""

    foot = f'''  <footer>
    <div class="note">
      <b>关于「稀缺度指数 SI」</b><br>
      SI 衡量的是「稀缺信号强度」（限量程度 / 获取门槛 / 发售窗口 / 售罄状态 / 联名强度五项加权），
      <b>不代表价格，也不代表升值潜力</b>。权重为初版假设，后续将用社区讨论热度反向校准。
    </div>
    <div>数据来源：麦当劳官方活动日历、积分商城（MCP 实测采集）｜ 人工补录条目已单独标注 ｜ 最后更新：{updated}</div>
    <div>本页为资料整理，仅供收藏参考；不构成任何商业建议。</div>
  </footer>
</div>

<div class="modal" id="modal" role="dialog" aria-modal="true" aria-label="藏品详情">
  <div class="modal-inner">
    <img id="mImg" alt="">
    <div class="modal-body">
      <h3 id="mName"></h3>
      <div class="row"><span>发售日期</span><b id="mDate"></b></div>
      <div class="row"><span>获取方式</span><b id="mCost"></b></div>
      <div class="row"><span>当前状态</span><b id="mStatus"></b></div>
      <div class="row"><span>稀缺度 SI</span><b id="mSi"></b></div>
      <div class="row"><span>限额</span><b id="mLimit"></b></div>
      <div class="row" id="mPathRow"><span>怎么拿</span><b id="mPath"></b></div>
      <button class="modal-close" id="mClose">关闭</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="copylayer" id="copyLayer" role="dialog" aria-modal="true" aria-label="手动复制">
  <div class="copybox">
    <p>浏览器阻止了自动复制。<br>请在下面按 <b>Ctrl / ⌘ + C</b> 复制：</p>
    <textarea id="copyArea" readonly aria-label="待复制内容"></textarea>
    <button id="copyClose" class="primary">关闭</button>
  </div>
</div>

<script id="board-data" type="application/json">{json.dumps(poster_data, ensure_ascii=False)}</script>
<script>
(function(){{
  var DATA = JSON.parse(document.getElementById('board-data').textContent);
  var FONT = '"PingFang SC","Microsoft YaHei",system-ui,sans-serif';

  function toast(msg){{
    var t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('on');
    clearTimeout(t._h); t._h = setTimeout(function(){{ t.classList.remove('on'); }}, 2200);
  }}

  function rrect(ctx,x,y,w,h,r){{
    ctx.beginPath();
    ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r);
    ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath();
  }}

  function drawPoster(){{
    var W=1080,H=1440;
    var c=document.createElement('canvas'); c.width=W; c.height=H;
    var ctx=c.getContext('2d');

    // 背景
    var g=ctx.createLinearGradient(0,0,W,H);
    g.addColorStop(0,'#16120f'); g.addColorStop(1,'#0b0908');
    ctx.fillStyle=g; ctx.fillRect(0,0,W,H);
    // 顶部色带
    var g2=ctx.createLinearGradient(0,0,W,0);
    g2.addColorStop(0,'#da291c'); g2.addColorStop(1,'#ffc72c');
    ctx.fillStyle=g2; ctx.fillRect(0,0,W,10);

    var PAD=76;
    ctx.fillStyle='#ffc72c'; ctx.font='600 24px '+FONT;
    ctx.fillText('麦门藏经阁 · MERCH ARCHIVE', PAD, 108);

    ctx.fillStyle='#f4efe9'; ctx.font='800 66px '+FONT;
    ctx.fillText('麦当劳周边稀缺度榜', PAD, 194);

    ctx.fillStyle='#a99e95'; ctx.font='400 24px '+FONT;
    ctx.fillText('按稀缺度指数 SI 排序 · 共 '+DATA.length+' 件 · 数据截至 2026-10-10', PAD, 240);

    ctx.strokeStyle='#2e2622'; ctx.beginPath(); ctx.moveTo(PAD,282); ctx.lineTo(W-PAD,282); ctx.stroke();

    // 榜单 Top 10
    var top = DATA.slice(0,10);
    var y0=352, gap=88;
    top.forEach(function(it,i){{
      var y=y0+i*gap;
      // 序号
      ctx.fillStyle = i<3 ? '#ffc72c' : '#6f6560';
      ctx.font='800 30px '+FONT;
      ctx.fillText(('0'+(i+1)).slice(-2), PAD, y);
      // 名称
      ctx.fillStyle='#f4efe9'; ctx.font='500 30px '+FONT;
      var nm=it.name; if(nm.length>17) nm=nm.slice(0,17)+'…';
      ctx.fillText(nm, PAD+62, y);
      // 状态
      ctx.fillStyle='#a99e95'; ctx.font='400 22px '+FONT;
      ctx.fillText(it.status+' · '+it.cost, PAD+62, y+30);
      // SI 数值
      ctx.fillStyle='#ffc72c'; ctx.font='800 34px '+FONT; ctx.textAlign='right';
      ctx.fillText(String(it.si), W-PAD, y);
      ctx.textAlign='left';
      // SI 条
      var bw=W-PAD*2, bh=5, by=y+40;
      ctx.fillStyle='#2a2320'; rrect(ctx,PAD,by,bw,bh,2.5); ctx.fill();
      ctx.fillStyle=(i<3?'#ffc72c':'#8a4a3c');
      rrect(ctx,PAD,by,bw*(it.si/100),bh,2.5); ctx.fill();
    }});

    // 声明
    var dy=H-176;
    ctx.fillStyle='#1f1917'; rrect(ctx,PAD,dy-34,W-PAD*2,104,14); ctx.fill();
    ctx.strokeStyle='#2e2622'; rrect(ctx,PAD,dy-34,W-PAD*2,104,14); ctx.stroke();
    ctx.fillStyle='#d7ccc2'; ctx.font='500 23px '+FONT;
    ctx.fillText('SI 为「稀缺信号强度」，不代表价格、不代表升值潜力。', PAD+26, dy+4);
    ctx.fillStyle='#6f6560'; ctx.font='400 21px '+FONT;
    ctx.fillText('数据来源：麦当劳官方活动日历 / 积分商城（MCP 采集）+ 人工补录', PAD+26, dy+40);

    ctx.fillStyle='#ffc72c'; ctx.font='600 22px '+FONT;
    ctx.fillText('麦门藏经阁', PAD, H-46);

    return c;
  }}

  document.getElementById('btnPoster').addEventListener('click', function(){{
    try{{
      var c=drawPoster();
      var a=document.createElement('a');
      a.download='麦门藏经阁_稀缺度榜_2026-10-10.png';
      a.href=c.toDataURL('image/png');
      a.click();
      toast('海报已生成（1080×1440）');
    }}catch(e){{ toast('生成失败：'+e.message); }}
  }});

  // 复制：优先 Clipboard API；被拒绝（如 iframe 权限）时降级 execCommand；
  // 仍失败则弹出可选中的文本框，让用户手动 Ctrl/⌘+C。三级兜底，不直接报错。
  function manualCopy(txt){{
    var layer=document.getElementById('copyLayer');
    var ta=document.getElementById('copyArea');
    ta.value=txt;
    layer.classList.add('on');
    setTimeout(function(){{ ta.focus(); ta.select(); ta.setSelectionRange(0, txt.length); }}, 30);
  }}

  function legacyCopy(txt){{
    var ta=document.createElement('textarea');
    ta.value=txt;
    ta.setAttribute('readonly','');
    ta.style.cssText='position:fixed;top:-1000px;left:0;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, txt.length);
    var ok=false;
    try{{ ok=document.execCommand('copy'); }}catch(e){{ ok=false; }}
    document.body.removeChild(ta);
    return ok;
  }}

  function copyText(txt, okMsg){{
    function fallback(){{
      if(legacyCopy(txt)){{ toast(okMsg); }} else {{ manualCopy(txt); }}
    }}
    if(navigator.clipboard && navigator.clipboard.writeText){{
      navigator.clipboard.writeText(txt).then(function(){{ toast(okMsg); }}, fallback);
    }}else{{
      fallback();
    }}
  }}

  document.getElementById('copyClose').addEventListener('click', function(){{
    document.getElementById('copyLayer').classList.remove('on');
  }});
  document.getElementById('copyLayer').addEventListener('click', function(e){{
    if(e.target===this) this.classList.remove('on');
  }});

  document.getElementById('btnCopy').addEventListener('click', function(){{
    var lines=['麦门藏经阁 · 麦当劳周边稀缺度榜（截至 2026-10-10）',''];
    DATA.slice(0,10).forEach(function(it,i){{
      lines.push((i+1)+'. '+it.name+' ｜ SI '+it.si+' ｜ '+it.status+' ｜ '+it.cost);
    }});
    lines.push('','注：SI 为稀缺信号强度，不代表价格。');
    copyText(lines.join('\\n'), '榜单文字已复制');
  }});

  // 单卡详情模态
  var modal=document.getElementById('modal');
  function closeModal(){{ modal.classList.remove('on'); }}
  document.querySelectorAll('.card').forEach(function(el){{
    var d=DATA[parseInt(el.dataset.idx,10)];
    function open(){{
      document.getElementById('mName').textContent=d.name;
      document.getElementById('mDate').textContent=d.date||'—';
      document.getElementById('mCost').textContent=d.cost;
      document.getElementById('mStatus').textContent=d.status;
      document.getElementById('mSi').textContent=d.si;
      document.getElementById('mLimit').textContent=d.limit||'—';
      var pr=document.getElementById('mPathRow');
      if(d.path){{ pr.style.display='flex'; document.getElementById('mPath').textContent=d.path; }}
      else{{ pr.style.display='none'; }}
      var img=el.querySelector('.thumb img');
      var mi=document.getElementById('mImg');
      if(img){{ mi.src=img.src; mi.style.display='block'; }}else{{ mi.style.display='none'; }}
      modal.classList.add('on');
    }}
    el.addEventListener('click', open);
    el.addEventListener('keydown', function(e){{
      if(e.target!==el) return;  // 卡片内的复制按钮自行处理键盘事件
      if(e.key==='Enter'||e.key===' '){{ e.preventDefault(); open(); }}
    }});
    var cb=el.querySelector('.copybtn');
    if(cb){{ cb.addEventListener('click', function(e){{
      e.stopPropagation();
      copyText(d.name+' ｜ 怎么拿：'+d.path, '获取路径已复制');
    }}); }}
  }});
  document.getElementById('mClose').addEventListener('click', closeModal);
  modal.addEventListener('click', function(e){{ if(e.target===modal) closeModal(); }});
  document.addEventListener('keydown', function(e){{ if(e.key==='Escape') closeModal(); }});
}})();
</script>
</body>
</html>
'''

    body = f'''  <div class="stats">
    <div>藏品总数<b>{total}</b></div>
    <div>在册品类<b>{len(set(i.get("category") for i in items))}</b></div>
    <div>自动采集<b>{src_count.get("mcp_calendar",0)+src_count.get("mcp_mall",0)}</b></div>
    <div>人工补录<b>{src_count.get("manual",0)}</b></div>
  </div>

  <h2>稀缺度榜<span class="hint">点击卡片可看详情；SI 不代表价格</span></h2>
  <ol class="board">
{board}
  </ol>

  <h2>藏品图鉴</h2>
  <div class="grid">
{cards}
  </div>
'''

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(head + body + foot)
    print(f"已生成：{OUT_PATH}")
    print(f"藏品 {len(items)} 条；含海报导出与文字复制能力，均由单一数据源派生。")


if __name__ == "__main__":
    main()
