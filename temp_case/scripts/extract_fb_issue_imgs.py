# -*- coding: utf-8 -*-
"""提取法宝问题.xlsx 内嵌截图并映射锚点行"""
import zipfile, re, os

SRC = r'D:\Downloads\法宝问题.xlsx'
OUT = r'E:\workproject\temp_case\reports\fb_issue_imgs'
os.makedirs(OUT, exist_ok=True)

z = zipfile.ZipFile(SRC)

# 1) 提取所有 media 图片
media = [n for n in z.namelist() if n.startswith('xl/media/') and not n.endswith('/')]
print('media count:', len(media))
for n in media:
    data = z.read(n)
    fn = os.path.basename(n)
    with open(os.path.join(OUT, fn), 'wb') as f:
        f.write(data)
    print('media:', fn, len(data))

# 2) 解析 drawing1.xml 锚点 -> rId -> 文件
for n in z.namelist():
    if re.match(r'xl/drawings/drawing\d+\.xml$', n):
        xml = z.read(n).decode('utf-8', 'ignore')
        anchors = re.findall(
            r'<xdr:from><xdr:col>(\d+)</xdr:col>.*?<xdr:row>(\d+)</xdr:row>.*?<a:blip[^>]*r:embed="(rId\d+)"',
            xml, re.S)
        rel_path = 'xl/drawings/_rels/' + n.split('/')[-1] + '.rels'
        rels = {}
        if rel_path in z.namelist():
            rx = z.read(rel_path).decode('utf-8', 'ignore')
            for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rx):
                rels[m.group(1)] = m.group(2)
        for col, row, rid in anchors:
            tgt = rels.get(rid, '?')
            print(f'anchor row={int(row)+1} col={int(col)+1} {rid} -> {tgt}')
