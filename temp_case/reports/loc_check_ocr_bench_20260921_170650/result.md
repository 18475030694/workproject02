# OCR 选型基准（RapidOCR）

引擎：RapidOCR (rapidocr_onnxruntime)

| 样本 | 放大 | 判定 | 识别文本(置信度) | 耗时s |
|---|---|---|---|---|
| mainview_btn01_box.png | 1 | PASS | 秘宝(1.00) | 0.38 |
| mainview_btn01_box.png | 2 | PASS | 秘宝(1.00) | 0.22 |
| mainview_btn01_box_grey.png | 1 | PASS | 秘宝(1.00) | 0.36 |
| mainview_btn01_box_grey.png | 2 | PASS | 秘宝(1.00) | 0.22 |
| battle_btn03_box.png | 1 | PASS | 秘宝(1.00) | 0.42 |
| battle_btn03_box.png | 2 | PASS | 秘宝(1.00) | 0.21 |
| mainview_btn03_bag.png | 1 | PASS | 背包(1.00) | 0.24 |
| mainview_btn03_bag.png | 2 | PASS | 背包(1.00) | 0.2 |
| mainview_btn02_mail.png | 1 | PASS | 邮件(1.00) | 0.44 |
| mainview_btn02_mail.png | 2 | PASS | 邮件(1.00) | 0.27 |
| mainview_btn04_kaifukuanhuan.png | 1 | PASS | （空） | 0.25 |
| mainview_btn04_kaifukuanhuan.png | 2 | PASS | （空） | 0.22 |

## 结论
- 正面样本：6/6 通过（必须命中「秘宝」）
- 负样本误报：6/6 通过（不得出现「秘宝」）
- 原图平均耗时：0.39s；2x 放大平均耗时：0.22s