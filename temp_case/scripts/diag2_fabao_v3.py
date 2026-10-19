# -*- coding: utf-8 -*-
"""diag2: 验证 value-based 模块查找 + 修复后的各取证片段"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base  # noqa: E402
from e2e_fabao import qa, texts, shot, wait_main_city, open_via_qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1353")
GAME_URL = "http://localhost:7456"

# ---- 修复后的 JS 片段（value-based 模块查找） ----

JS_RES = """() => {
  const out = {};
  try {
    for (const [k, v] of System.entries()) {
      if (!out.srKey && v && v.ShareRes && v.ShareRes.cfg_soul_ring_base) { out.srKey = k; }
      if (!out.utilKey && v && v.Util && v.Util.formatLevel) { out.utilKey = k; }
      if (!out.enumKey && v && v.SysIdEnum && v.SysIdEnum.SOUL_RING !== undefined) { out.enumKey = k; }
      if (out.srKey && out.utilKey && out.enumKey) break;
    }
  } catch (e) { out.err = String(e); }
  try { out.pool_level = window.SystemModules.soulRingMgr.pool_level; } catch (e) { out.poolErr = String(e); }
  return out;
}"""

JS_ATLAS_APPEARANCE = """() => {
  const out = { items: [] };
  try {
    let SR = null;
    for (const [k, v] of System.entries()) { if (v && v.ShareRes && v.ShareRes.cfg_soul_ring_base) { SR = v.ShareRes; break; } }
    if (!SR) return { err: 'ShareRes not found' };
    const ringNames = new Set(Object.values(SR.cfg_soul_ring_base).map(e => e.name));
    const Q = window.__qa;
    const roots = Q.findByName('UISoulRingAtlas');
    if (!roots || !roots.length) return { open: false };
    const hex = (c) => { try { return c.toHEXString ? c.toHEXString() : '#' + c.toHEX(); } catch (e) { return '?'; } };
    const collectLabels = (n, d, acc) => {
      if (d > 6 || acc.length > 40) return;
      for (const c of n.children) {
        const lb = c.getComponent && c.getComponent('cc.Label');
        const rt = c.getComponent && c.getComponent('cc.RichText');
        const t = lb ? String(lb.string) : (rt ? String(rt.string) : null);
        if (t && t.trim()) acc.push({ text: t.trim().slice(0, 24), color: lb ? hex(lb.color) : null });
        collectLabels(c, d + 1, acc);
      }
    };
    const walk = (n) => {
      try {
        const sp = n.getComponent && n.getComponent('cc.Sprite');
        if (sp && sp.spriteFrame && /soul_ring_atlas_panel01_kuang|wupinkuang/.test(sp.spriteFrame.name)) {
          const labels = [];
          collectLabels(n, 0, labels);
          let p = n.parent, depth = 0;
          while (p && depth < 4) { collectLabels(p, 0, labels); p = p.parent; depth++; }
          const seen = new Set(); const hits = [];
          for (const l of labels) {
            const key = l.text + '|' + l.color;
            if (seen.has(key)) continue; seen.add(key);
            for (const rn of ringNames) { if (l.text.includes(rn)) { hits.push({ ring: rn, color: l.color }); break; } }
          }
          out.items.push({ sf: sp.spriteFrame.name, node: n.name, rings: hits.slice(0, 3) });
          if (out.items.length > 90) return;
        }
      } catch (e) { /* skip node */ }
      for (const c of n.children) walk(c);
    };
    walk(roots[0]);
    out.count = out.items.length;
  } catch (e) { out.err = String(e); }
  return out;
}"""

JS_ATLAS_TOGGLES = """() => {
  const out = {};
  try {
    const Q = window.__qa;
    const roots = Q.findByName('UISoulRingAtlas');
    if (!roots || !roots.length) return { open: false };
    const findContent = (n, d) => {
      if (d > 12) return null;
      for (const c of n.children) {
        if (c.name && (c.name.indexOf('TogContent') >= 0 || c.name.indexOf('TypeList') >= 0)) return c;
        const r = findContent(c, d + 1); if (r) return r;
      }
      return null;
    };
    const content = findContent(roots[0], 0);
    if (!content) return { open: true, content: 'not-found' };
    out.content = { name: content.name, children: content.children.length,
                    childNames: content.children.map(c => c.name).slice(0, 15) };
    out.sprites = [];
    const hex = (c) => { try { return c.toHEXString ? c.toHEXString() : '#' + c.toHEX(); } catch (e) { return '?'; } };
    const walk = (n, d) => {
      if (d > 3) return;
      const sp = n.getComponent && n.getComponent('cc.Sprite');
      if (sp && sp.spriteFrame) out.sprites.push(sp.spriteFrame.name);
      for (const c of n.children) walk(c, d + 1);
    };
    for (const c of content.children) walk(c, 0);
    out.sprites = [...new Set(out.sprites)];
  } catch (e) { out.err = String(e); }
  return out;
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        page.add_init_script(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
        page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(4000)
        base.force_select_server(page, 5, "S5")
        page.reload(wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(3000)
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60_000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
        wait_main_city(page)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        diag = {}
        diag["res"] = qa(page, JS_RES, {})
        print("res:", json.dumps(diag["res"], ensure_ascii=False))

        # 图鉴
        opened = open_via_qa(page, "UISoulRingAtlas")
        page.wait_for_timeout(1500)
        diag["atlas_open"] = opened
        diag["toggles"] = qa(page, JS_ATLAS_TOGGLES, {})
        print("toggles:", json.dumps(diag["toggles"], ensure_ascii=False)[:600])
        diag["appearance"] = qa(page, JS_ATLAS_APPEARANCE, {})
        ap = diag["appearance"]
        print("appearance count:", ap.get("count"), "err:", ap.get("err"), "open:", ap.get("open"))
        for it in (ap.get("items") or [])[:6]:
            print("   ", json.dumps(it, ensure_ascii=False))

        # TC046/R2: 点最后一个 toggle（仙品档）→ 提示
        tip = qa(page, """() => {
          const Q = window.__qa; const out = {};
          try {
            const roots = Q.findByName('UISoulRingAtlas');
            if (!roots || !roots.length) return { err: 'no atlas' };
            const findContent = (n, d) => {
              if (d > 12) return null;
              for (const c of n.children) {
                if (c.name && (c.name.indexOf('TogContent') >= 0 || c.name.indexOf('TypeList') >= 0)) return c;
                const r = findContent(c, d + 1); if (r) return r;
              }
              return null;
            };
            const content = findContent(roots[0], 0);
            if (!content) return { err: 'no content' };
            const last = content.children[content.children.length - 1];
            out.clicked = last.name;
            window.__qa.clickNode(last);
            return out;
          } catch (e) { return { err: String(e) }; }
        }""", {})
        page.wait_for_timeout(900)
        tx = [str(e.get("text")) for e in texts(page) if e.get("text")]
        tips = [t for t in tx if "炼宝等级" in t or "可查阅" in t]
        diag["tc046"] = {"click": tip, "tips": tips}
        print("tc046:", json.dumps(diag["tc046"], ensure_ascii=False)[:300])

        # TC014: 点『御剑符』所在 item 祖先 → desc
        clicked = qa(page, """() => {
          const Q = window.__qa;
          const lbls = Q.findLabel('[凡]御剑符');
          if (!lbls || !lbls.length) return { found: false };
          return { found: true, node: lbls[0].name, parent: lbls[0].parent ? lbls[0].parent.name : null };
        }""", {})
        diag["click_lbl"] = clicked
        print("click_lbl:", json.dumps(clicked, ensure_ascii=False))
        # 逐级点击祖先尝试打开 desc
        for up in range(1, 6):
            ok = qa(page, f"""() => {{
              const Q = window.__qa;
              const lbls = Q.findLabel('[凡]御剑符');
              if (!lbls || !lbls.length) return false;
              let n = lbls[0]; for (let i = 0; i < {up} && n.parent; i++) n = n.parent;
              Q.clickNode(n); return n.name;
            }}""", "")
            page.wait_for_timeout(700)
            desc_open = qa(page, "() => (window.__qa.findByName('UISoulRingAtlasDesc') || []).length", 0)
            if desc_open:
                diag["desc_opened_at_up"] = up
                break
        page.wait_for_timeout(800)
        desc_open = qa(page, "() => (window.__qa.findByName('UISoulRingAtlasDesc') || []).length", 0)
        diag["desc_open"] = desc_open
        if desc_open:
            dt = [str(e.get("text")) for e in texts(page) if e.get("text") and ("初始" in str(e.get("text")) or "阶" in str(e.get("text")))]
            diag["desc_texts"] = dt[:8]
            print("desc_texts:", json.dumps(diag["desc_texts"], ensure_ascii=False))
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # 概率弹窗
        lv_ok = open_via_qa(page, "UISoulRingDrawLvDesc")
        page.wait_for_timeout(1200)
        prob = qa(page, """() => {
          const Q = window.__qa; const out = {};
          try {
            const roots = Q.findByName('UISoulRingDrawLvDesc');
            out.root = roots ? roots.length : -1;
            if (!roots || !roots.length) return out;
            out.sprites = [];
            const walk = (n) => {
              const sp = n.getComponent && n.getComponent('cc.Sprite');
              if (sp && sp.spriteFrame) out.sprites.push(sp.spriteFrame.name);
              for (const c of n.children) walk(c);
            };
            walk(roots[0]);
            out.sprites = [...new Set(out.sprites)].filter(s => /hero_panel08|wupinkuang|kuang/.test(s));
          } catch (e) { out.err = String(e); }
          return out;
        }""", {})
        diag["prob"] = prob
        print("prob:", json.dumps(prob, ensure_ascii=False)[:400])
        shot(page, Path(ROOT / "reports" / "e2e_fabao_v3_latest"), "diag2_lvdesc")

        (ROOT / "reports" / "e2e_fabao_v3_latest" / "diag2.json").write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        browser.close()
print("DONE")
