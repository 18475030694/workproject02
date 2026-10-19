import re, textwrap

p = r'E:/workproject/harness/e2e_privilege_v3.py'
src = open(p, encoding='utf-8').read()

helper = textwrap.dedent(r'''
def inspect_uiprivcard(page):
    """不依赖 window.Global，从 Cocos 场景树直接读取 UIPrivCard 节点状态。"""
    return page.evaluate("""() => {
        const scene = cc.director.getScene();
        if (!scene) return null;
        let uiNode = null;
        function walk(n) {
            if (uiNode) return;
            if (n.name === 'UIPrivCard' && n.activeInHierarchy) { uiNode = n; return; }
            if (n.children) for (const c of n.children) walk(c);
        }
        walk(scene);
        if (!uiNode) return null;
        function find(root, name) {
            if (root.name === name) return root;
            if (!root.children) return null;
            for (const c of root.children) { const r = find(c, name); if (r) return r; }
            return null;
        }
        function count(root) { return root && root.children ? root.children.length : 0; }
        function getText(node) {
            if (!node) return null;
            const lb = node.getComponent(cc.Label); if (lb) return lb.string;
            const rt = node.getComponent(cc.RichText); if (rt) return rt.string;
            return null;
        }
        const firstGroup = find(uiNode, 'FirstGroup');
        const firstDesc = find(uiNode, 'FirstDescLb');
        const firstReward = find(uiNode, 'FirstRewardList');
        const firstContent = find(uiNode, 'FirstContent');
        const activedLb = find(uiNode, 'ActivedLb');
        const rechargeBtb = find(uiNode, 'RechargeBtb');
        const rtTime = find(uiNode, 'RtTime');
        const title = find(uiNode, 'Title_txt');
        const titleLb = find(uiNode, 'TitleLb_txt');
        const price = find(uiNode, 'RechargeLb_txt');
        const dailyScroll = find(uiNode, 'DailyScroll');
        const dailyLayout = find(uiNode, 'DailyLayoutReward');
        return {
            FirstGroup_active: firstGroup ? firstGroup.activeInHierarchy : null,
            FirstDescLb_active: firstDesc ? firstDesc.activeInHierarchy : null,
            FirstDescLb_text: firstDesc ? getText(firstDesc) : null,
            FirstRewardList_active: firstReward ? firstReward.activeInHierarchy : null,
            FirstContent_children: firstContent ? count(firstContent) : 0,
            ActivedLb_active: activedLb ? activedLb.activeInHierarchy : null,
            RechargeBtb_active: rechargeBtb ? rechargeBtb.activeInHierarchy : null,
            RtTime_active: rtTime ? rtTime.activeInHierarchy : null,
            RtTime_string: rtTime ? getText(rtTime) : null,
            Title_text: title ? getText(title) : null,
            TitleLb_text: titleLb ? getText(titleLb) : null,
            RechargeLb_text: price ? getText(price) : null,
            DailyScroll_active: dailyScroll ? dailyScroll.activeInHierarchy : null,
            DailyLayoutReward_children: dailyLayout ? count(dailyLayout) : 0,
        };
    }""")
''').lstrip()

# Insert helper after dump_text function
marker = 'def dump_text(page):'
idx = src.find(marker)
end = src.find('\n\n', idx)
src = src[:end+2] + helper + src[end+2:]

# Replace all blocks that query UIPrivCard nodes via window.Global.uiMgr
old_block = '''nodes = page.evaluate("""() => {
        try {
            const ui = window.Global.uiMgr.getUI('UIPrivCard');
            if (!ui) return null;
            const o = ui.uiObjects || {};'''
src = src.replace(old_block, 'nodes = inspect_uiprivcard(page)\n    snap(page, "nodes_query")')

# Remove trailing catch blocks that belonged to the old evaluate
# Simpler: just replace the catch tail after each occurrence; do a broad replacement of the catch line back to }""")
# Actually, after replacement, each old block still has:
#         } catch(e) { return 'err:' + e.message; }
#     }""")
# We need to delete these.
src = src.replace('''        } catch(e) { return 'err:' + e.message; }
    }""")''', '')

# Also fix TC-021 nodes query (uses different variable names inside f-string)
# It already got replaced partially? Let's just ensure no window.Global.uiMgr.getUI remains
if "window.Global.uiMgr.getUI('UIPrivCard')" in src:
    print('WARNING: still has window.Global.uiMgr.getUI references')
else:
    print('all window.Global.uiMgr.getUI references removed')

open(p, 'w', encoding='utf-8').write(src)
print('patched', p)
