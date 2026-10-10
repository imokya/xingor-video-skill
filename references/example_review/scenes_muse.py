"""flat-review 示例：Muse 实测（纯配音 B 站评测口吻，3:4 小红书 / 6:7 视频号，约 4 分钟）
在项目目录（素材相对路径如下）运行：
  python <SKILL>/scripts/review/rv_render.py scenes_muse.py 成片_小红书.mp4
  python <SKILL>/scripts/review/rv_render.py scenes_muse.py 成片_视频号.mp4 --67
目录约定：配音/lines.txt → 配音/full/（rv_tts + rv_align）；配音/hook.txt → 配音/hook/；截图在 ../截图/
每个场景函数 f(frame, t) 只负责画内容；底色、转场、HUD、字幕、结尾淡出由 render_segments 统一处理。
所有触发时刻都取自配音字级时间：at(句号, '字', 第几次出现)。
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageOps
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../scripts/review'))
sys.path.insert(0, os.path.expanduser('~/.claude/skills/xingor-video-skill/scripts/review'))
from rv_core import *
import rv_core as R

ROOT = '..'                                                     # 项目根（截图、原始素材所在）
setup('配音/full/timeline.json', assets=f'{ROOT}/截图', avatar=f'{ROOT}/a7b9bb87-ec60-4e2e-921b-76eea86201ee.mp4',
      brand='MUSE', label='HANDS-ON — 2026', tasks=5, keywords=[
    'Muse', '替你干活', '不听宣传', '直接上手派活', '五个任务', '简单测一测', '交代个活', '邮箱和日历', '会用电脑的实习生',
    '聊天框', '写清楚', '努力工作中', '搜索参数', '一样不落', '购买建议', '美国官网价', '番茄钟', '日式厨房计时器',
    '能跑的预览', '刻度表盘', '大号数字', '暂停', '挑不出大毛病', '咖啡店官网', '精品店', '模板', '自己画的', '封面',
    '一个字没错', '卡通风格', '写实人像', '随手拍', '盯着那杯咖啡', '花纹', '宋代古风美女', '美女', '邻家姐姐', '美感',
    '生成视频', '参考', '动起来', '打字', '抬头', '挥手', '基本一致', '同一个对话', '不用来回换工具', '最实用',
    '日程和规划', '连上日历', '邮件草稿', '杭州', '提前一天预约', '先别发送', '不要预订', '照做', '吐槽', '古风姐姐',
    '交领加盘扣', '明清以后', '抹胸', '训练数据', '飞书', '微信', '额度', '9%', '10 亿词元', '永不过期', '完全够用',
    '最大的亮点', '一个对话', '短板', '聊聊天', '简单测试', '自己上手', '评论区'])
DUR = R.TL.dur
OUTRO = f'{ROOT}/关注.mp4'
BGM = 'music/130.mp3'; BGM_BED = -14.0
ROBOT = f'{ROOT}/media-generation-muse-robot-wave-16x9-0-b7dda0cf-43fe-4500-b483-8249332a618e.mp4'
WHAT_FILE = '配音/what/C_新游戏解说.mp3'

# ---------- 截图里的原始提问 ----------
P1 = '帮我对比 3 款热门降噪耳机（索尼 WH-1000XM6、Bose QC Ultra、AirPods Max），从价格、降噪、续航、重量四个维度做成表格，最后给一句购买建议。'
P2 = '帮我做一个番茄钟网页，单个 HTML 文件。设计方向：安静、克制、有质感，像一件放在桌上的精致小物件，参考日式厨房计时器和 Braun 的工业设计……'
P3 = '帮我生成一张 16:9 的视频封面：一个米白色、毛茸茸的可爱小机器人坐在笔记本电脑前认真工作，背景是深色科技感工作室，带一点蓝色霓虹光。画面左侧留白，写上大字标题“Muse 实测”。'
P4 = '以上面这张封面为参考，让封面里这个小机器人动起来：生成一段 5 秒左右的 16:9 视频，它先在笔记本上打字，再抬头对镜头挥手。角色长相和场景尽量和封面保持一致。'
P_SONG = '生成一张宋代古风美女的写实人像：身穿宋制汉服（红褙子、抹胸、百迭裙），发髻简洁、簪一支玉簪，坐在江南园林的木窗边，窗外是水面和细雨……'
P_ONE = '把需求写清楚，丢过去就行'
P_CTA = '你最想让 Muse 帮你干点啥？'
COVER = '27-场景6-生图-大图.png'

# ---------- 关键时刻 ----------
SEND4 = le(21) - .1; TYPE4 = (at(21, '生') + .55, le(21) - .25); VID_T0 = at(22, '先') - .05
WHAT_T = le(19) + .3
T1SHOT = ls(9) - .35

# ================= 场景 =================
def s_intro(frame, t):                    # AI 智能体 -> Muse 替你干活.
    d = ImageDraw.Draw(frame); p = eo(P(t, .35, .5))
    d.line([(90, 300), (90 + (W - 180) * p, 300)], fill=BLACK, width=3)
    text(frame, (90, 256), 'N° 01', 'mono', 22, BLACK, alpha=p)
    text(frame, (W - 90, 256), 'META · AI AGENT', 'mono', 22, BLACK, 'ra', alpha=p)
    tm = at(0, 'Muse')
    word(frame, 'AI 智能体', 'heavy', 168, BLACK, 86, 420, t, at(0, 'AI') - .1, t_out=tm - .3)
    text(frame, (92, 680), 'a new AI agent from Meta', 'serif', 56, BLACK, alpha=eo(P(t, at(0, 'AI') + .3, .4)) * (1 - P(t, tm - .3, .2)))
    mend = word(frame, 'Muse', 'black', 250, BLACK, 86, 360, t, tm - .12, sx=1.0, dist=520)
    avatar(frame, min(mend + 90, W - 125), 510, 70 * eob(P(t, tm + .2, .4)), t, ring=BLACK)
    end = word(frame, '替你干活', 'heavy', 190, BLACK, 90, 660, t, at(0, '替') - .1, from_left=True)
    R.DOTPOS['q'] = (end + 40, 838)                              # 下一段从这个圆点扩张
    dot(frame, end + 40, 838, t, at(0, '替') + .5, CORAL)

def s_question(frame, t):                 # 不听宣传，直接派活
    d = ImageDraw.Draw(frame); p = eo(P(t, ls(1) - .1, .4))
    d.line([(90, 300), (90 + (W - 180) * p, 300)], fill=BLACK, width=3)
    text(frame, (90, 256), 'NO HYPE', 'mono', 22, BLACK, alpha=p)
    word(frame, '不听宣传', 'heavy', 200, BLACK, 86, 380, t, at(1, '不') - .1)
    strike(frame, t, at(1, '不') + .5, 80, 940, 490, CREAM, 12)
    end = word(frame, '直接派活', 'heavy', 200, BLACK, 86, 720, t, at(1, '直') - .1, from_left=True)
    dot(frame, end + 36, 906, t, at(1, '直') + .5, CREAM, 24)

TASKS = ['信息整理', '写代码', '做图', '生成视频', '日程和规划']
def s_five(frame, t):                     # 五个任务清单
    title(frame, t, '五个任务', at(2, '五'), CREAM)
    d = ImageDraw.Draw(frame)
    for i, s_ in enumerate(TASKS):
        p = eo(P(t, at(2, '五') + .25 + i * .12, .35))
        if p <= 0: continue
        y = 560 + i * 104
        text(frame, (90 + 40 * (1 - p), y), f'0{i + 1}', 'mono', 40, CORAL, alpha=p)
        text(frame, (200 + 40 * (1 - p), y - 6), s_, 'heavy', 62, CREAM, alpha=p)
        d.line([(90, y + 80), (90 + (W - 180) * p, y + 80)], fill=GREY, width=1)
    chip(frame, 90, 1100, '简单测一测 · 好坏都摆出来', 32, CORAL, CREAM, t, at(2, '简') - .05)

def s_what(frame, t):                     # 你问它答 vs 交代个活
    sec(frame, t, ls(3), CREAM, 'WHAT IS MUSE', '它是啥', 'it does the work')
    title(frame, t, 'Muse 是啥', ls(3) + .15, CREAM, size=170, y=380, t_out=at(3, '普') - .3)
    text(frame, (90, 340), '普通聊天 AI', 'bold', 44, CREAM, alpha=eo(P(t, at(3, '普') - .1, .3)))
    word(frame, '你问它答', 'heavy', 200, CREAM, 86, 420, t, at(3, '问') - .08, sx=1.12)
    tm = at(3, 'Muse')
    if t > tm:
        lay = Image.new('RGBA', frame.size, BLUE + (0,))
        ImageDraw.Draw(lay).rectangle([80, 400, 1000, 680], fill=BLUE + (int(130 * eo(P(t, tm, .3))),)); frame.alpha_composite(lay)
    text(frame, (90, 760), 'Muse', 'bold', 44, CREAM, alpha=eo(P(t, tm - .1, .3)))
    end = word(frame, '交代个活', 'heavy', 200, CREAM, 86, 840, t, at(3, '交') - .08, sx=1.12, from_left=True)
    dot(frame, end + 40, 1026, t, at(3, '交') + .4, CORAL, 26)
    x = 90
    for s_, ch in [('自己去查', '查'), ('自己去写', '写'), ('自己去画', '画')]:
        x += chip(frame, x, 1100, s_, 32, CORAL, CREAM, t, at(3, ch) - .05) + 14

def s_cloud(frame, t):                    # 云端电脑 = 会用电脑的实习生
    sec(frame, t, ls(4) - .2, BLACK, 'WHAT IS MUSE', '云端有自己的电脑', 'an intern with a PC')
    ts = at(4, '实')
    title(frame, t, '云端电脑', at(4, '云'), BLACK, size=150, y=290, t_out=ts - .25)
    title(frame, t, '电脑实习生', ts, BLACK, size=150, y=290)
    p = eob(P(t, at(4, '电') - .2, .5), 1.2)
    if p > 0:
        d = ImageDraw.Draw(frame); cx, cy = W / 2, 760; w, h = 620 * p, 390 * p
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 26, fill=BLACK)
        d.polygon([(cx - 60 * p, cy + h / 2), (cx + 60 * p, cy + h / 2), (cx + 90 * p, cy + h / 2 + 50 * p), (cx - 90 * p, cy + h / 2 + 50 * p)], fill=BLACK)
        if p > .6:
            avatar(frame, cx, cy - 20, 95 * p, t); text(frame, (cx, cy + 120 * p), 'MUSE · CLOUD PC', 'mono', 22, CREAM, 'mm')
    w1 = F('bold', 32).getlength('连上邮箱') + 35; w2 = F('bold', 32).getlength('连上日历') + 35; x0 = (W - (w1 + w2 + 16)) / 2
    chip(frame, x0, 1060, '连上邮箱', 32, CORAL, CREAM, t, at(4, '邮') - .05)
    chip(frame, x0 + w1 + 16, 1060, '连上日历', 32, CORAL, CREAM, t, at(4, '日') - .05)

def s_app(frame, t):                      # 一个聊天框
    sec(frame, t, ls(5) - .2, CREAM, 'HOW TO USE', '用法', 'just type it')
    title(frame, t, '没门槛', ls(5) + .15, CREAM, size=170, y=300, t_out=at(5, '聊') - .25)
    title(frame, t, '一个聊天框', at(5, '聊'), CREAM, size=150, y=300)
    a = eob(P(t, at(5, '聊') - .1, .4))
    if a > 0:
        avatar(frame, W / 2, 660, 80 * a, t, ring=CREAM); text(frame, (W / 2, 770), 'Muse', 'bold', 34, CREAM, 'mm', alpha=min(1, a))
    inputbox(frame, t, 60, 860, 960, P_ONE, (at(5, '写'), le(5) - .2), le(5) + .05, alpha=eo(P(t, at(5, '聊') - .1, .3)))

TABLE_COLS = [('索尼', 'WH-1000XM6'), ('Bose', 'QC Ultra 二代'), ('AirPods', 'Max')]
def s_task1(frame, t):                    # 打字 -> 头像状态 -> 动态对比表（数值取自截图）
    sec(frame, t, ls(6) + .2, CREAM, 'TASK 01', '信息整理', 'compare, then decide')
    title(frame, t, '信息整理', at(6, '信'), CREAM, size=190, y=310)
    send = le(6) + .05
    if t < ls(8) - .3:
        q = P(t, send + .15, .3)
        inputbox(frame, t, 60, 600, 960, P1, (at(6, '信') + .5, le(6) - .1), send, alpha=eo(P(t, at(6, '信') + .2, .3)) * (1 - q), yoff=-80 * eo(q))
        a = eob(P(t, ls(7) - .2, .35))
        if a > 0:
            fd = 1 - P(t, ls(8) - .6, .3)
            avatar(frame, W / 2, 760, 90 * a, t, ring=CREAM)
            s_ = '努力工作中' if t < at(7, '搜') - .05 else '搜索参数'
            if fd > 0 and t > at(7, '努') - .1: chip(frame, W / 2, 900, s_ + '.' * (1 + int(t * 4) % 3), 34, CORAL, CREAM, anchor='c')
            if t > at(7, '戏') - .1 and fd > 0: text(frame, (W / 2, 1040), '（戏还挺足）', 'med', 34, CREAM, 'mm', alpha=eo(P(t, at(7, '戏') - .1, .3)) * fd)
    table(frame, t, CREAM, CORAL, TABLE_COLS, [
        ('价格', ['$459.99', '$449', '$549'], at(8, '价'), 1), ('降噪', ['旗舰级', '最强一档', '专业级'], at(8, '降'), None),
        ('续航', ['30h', '30h', '20h'], at(8, '续'), None), ('重量', ['254g', '264.4g', '386.2g'], at(8, '重'), 0)], ls(8) - .25)

def s_task1_shot(frame, t):               # 原始截图 + 标注
    sec(frame, t, T1SHOT + .2, CREAM, 'TASK 01', '对比表 · 原始截图', 'one table, one tip')
    box = img_card(frame, '04-场景1-结果表格.png', 60, 380, 960, t, T1SHOT + .3)
    if not box: return
    x, y, w, h = box
    chip(frame, x + w - 10, y + h - 36, '附了一句购买建议', 30, CORAL, CREAM, t, at(9, '购') - .05, anchor='r')
    chip(frame, x, y + h + 50, '注意：价格是美国官网价', 30, CREAM, BLACK, t, at(9, '美') - .05)

def s_task2(frame, t):                    # 番茄钟：打字
    sec(frame, t, ls(10) + .1, BLACK, 'TASK 02', '写代码', 'a quiet kitchen timer')
    title(frame, t, '写代码', ls(10) + .2, BLACK, dotc=CREAM, size=200, t_out=at(10, '番') - .25)
    title(frame, t, '番茄钟网页', at(10, '番'), BLACK, dotc=CREAM, size=170)
    send = at(10, '说') - .1
    inputbox(frame, t, 60, 580, 960, P2, (at(10, '我') + .05, send - .2), send, alpha=eo(P(t, at(10, '我') - .2, .3)))
    text(frame, (W / 2, 1105), '（这要求我自己都不一定做得出来）', 'med', 34, BLACK, 'mm', alpha=eo(P(t, at(10, '说') - .1, .4)))

def s_task2_preview(frame, t):            # 预览 + 指线标注
    sec(frame, t, ls(11), BLACK, 'TASK 02', '番茄钟 · App 内预览', 'it just works')
    title(frame, t, '能跑的预览', at(11, '预') - .2, BLACK, size=150)
    box = img_card(frame, '43-场景10-番茄钟重测-运行中-卡片.png', 70, 500, 480, t, ls(11) + .2)
    if not box: return
    x, y, w, h = box
    for s_, ts, (fx, fy), cy in [('刻度表盘', at(11, '刻'), (.80, .30), 560), ('大号数字', at(11, '大'), (.62, .45), 720), ('只亮「暂停」', at(11, '暂'), (.47, .73), 880)]:
        if t < ts - .1: continue
        pointer(frame, t, ts - .1, 620, cy + 30, x + w * fx, y + h * fy, CORAL); chip(frame, 620, cy, s_, 34, BLACK, CREAM, t, ts - .1)
    chip(frame, 620, 1020, '挑不出大毛病', 34, CORAL, CREAM, t, at(11, '挑') - .05)

def s_task2_site(frame, t):               # 浏览器里滚动官网
    sec(frame, t, ls(12), CREAM, 'TASK 02', '咖啡店「山间」官网', 'no template vibes')
    tt = at(12, '精')
    title(frame, t, '咖啡店官网', at(12, '咖'), CREAM, size=150, t_out=tt - .25); title(frame, t, '不像模板', tt, CREAM, size=150)
    browser(frame, t, (60, 520, 960, 640), ['38-场景9-前端审美-首屏.png', '39-场景9-前端审美-门店照片.png', '40-场景9-前端审美-门店故事.png'],
            [(at(12, '雾') - .2, 0), (at(12, '陶') - .2, 1), (at(12, '大') - .2, 2)], 'shanjian · 山间', t_in=at(12, '咖') + .1)
    chip(frame, 1000, 1090, '配图 · 它自己画的', 30, CORAL, CREAM, t, at(13, '配') - .05, anchor='r')

def s_task3(frame, t):                    # 打字 -> 封面 -> 推近标题
    sec(frame, t, ls(14) + .1, CREAM, 'TASK 03', '做图', 'cartoon: nailed it')
    title(frame, t, '做图', ls(14) + .2, CREAM, size=200, t_out=at(14, '封') - .25); title(frame, t, '画封面', at(14, '封'), CREAM, size=170)
    send = le(14) - .15
    if t < send + .5:
        q = P(t, send + .15, .3)
        inputbox(frame, t, 60, 560, 960, P3, (at(14, '我') + .05, send - .2), send, alpha=eo(P(t, at(14, '我') - .2, .3)) * (1 - q), yoff=-60 * eo(q))
    t0 = send + .3; p = eob(P(t, t0, .5), 1.2)
    if p <= 0: return
    z = eio(P(t, at(15, '错') - .6, .7)) * (1 - eio(P(t, at(15, '卡') - .2, .5)))
    w = 960; h = int(w * 1883 / 3356); x, y = 60, 560 + int((1 - p) * 700)
    zoom_card(frame, COVER, x, y, w, h, z, (.015, .03, .495, .5))
    chip(frame, x, y - 58, 'Muse 画的封面', 24, BLACK, CREAM, t, t0 + .2)
    chip(frame, x + w, y + h + 24, '中英文标题 · 0 错字', 36, CORAL, CREAM, t, at(15, '错') - .05, anchor='r')
    chip(frame, x, y + h + 24, '卡通风格：拿手', 36, CREAM, BLACK, t, at(15, '卡') - .05)

def s_task3_portrait(frame, t):           # 先夸
    sec(frame, t, ls(16), BLACK, 'TASK 03', '写实人像', 'shot on film?')
    tz = at(16, '随')
    title(frame, t, '写实人像', at(16, '写'), BLACK, size=170, t_out=tz - .25); title(frame, t, '像随手拍的', tz, BLACK, size=150)
    img_card(frame, '47-场景11-真人生图-大图.png', 60, 520, 960, t, at(16, '咖') - .1)
    x = 90
    for s_, ch in [('皮肤', '皮'), ('碎发', '碎'), ('胶片颗粒', '胶')]: x += chip(frame, x, 1140, s_, 32, CORAL, CREAM, t, at(16, ch) - .05) + 14

def s_task3_flaw(frame, t):               # 再挑刺：推近眼睛 → 书页乱码
    sec(frame, t, ls(17), CREAM, 'TASK 03', '但仔细看', 'look closer')
    title(frame, t, '仔细看', ls(17) + .1, CREAM, size=200)
    te, tb = at(17, '眼'), at(17, '书', 1)          # 注意：「看书」里的「书」先出现，要取第 2 个
    if t < tb - .1:
        zoom_card(frame, '47-场景11-真人生图-大图.png', 60, 520, 960, 640, eio(P(t, te - .3, .6)), (.30, .22, .78, .78))
        if t > te + .3:
            pointer(frame, t, te + .3, 60 + 960 * .55, 520 + 640 * .32, 60 + 960 * .55, 520 + 640 * .78, CORAL)
            chip(frame, 1000, 1080, '说是看书，眼睛在看咖啡', 32, CORAL, CREAM, t, te + .3, anchor='r')
    else:
        box = img_card(frame, '48-场景11-真人生图-手部和书.png', 60, 560, 960, t, tb - .1)
        if box:
            x, y, w, h = box; ring(frame, x + w * .63, y + h * .55, 120, t, tb + .4, CORAL)
            chip(frame, x + w - 20, y + h - 80, '书里的字：长得像字的花纹', 32, CORAL, CREAM, t, at(17, '花') - .1, anchor='r')

def s_task3_song(frame, t):               # 包袱铺垫
    sec(frame, t, ls(18), CREAM, 'TASK 03', '宋代古风美女', 'the setup')
    title(frame, t, '古风美女', at(18, '宋') - .1, CREAM, size=170, t_out=at(18, '重') - .25)
    title(frame, t, '重点：美女', at(18, '重'), CREAM, size=170)
    inputbox(frame, t, 60, 580, 960, P_SONG, (at(18, '宋') + .1, at(18, '重') - .3), at(18, '重') - .15, alpha=eo(P(t, ls(18), .3)) * (1 - P(t, le(19) - .1, .2)))
    if ls(19) - .1 < t < WHAT_T:
        text(frame, (W / 2, 1000), '结果它给了我……', 'heavy', 80, CREAM, 'mm', alpha=eo(P(t, ls(19) - .1, .3)) * (1 - P(t, le(19) + .1, .15)))

def s_task3_reveal(frame, t):             # What? —— 图砸出来 + 抖动（硬切进来）
    p = eob(P(t, WHAT_T, .25), 2.2); sk = max(0, 1 - P(t, WHAT_T, .45)) * 26
    dx, dy = int(math.sin(t * 90) * sk), int(math.cos(t * 77) * sk)
    im = img('51-场景12-宋代古风-大图.png'); w = int(900 * (.6 + .4 * min(p, 1.1))); h = int(im.height * w / im.width)
    x, y = (W - w) // 2 + dx, 520 + dy
    shadow(frame, x, y, w, h); frame.alpha_composite(rounded(im.resize((max(2, w), max(2, h)), Image.LANCZOS), 22), (x, y))
    word(frame, 'What?', 'black', 230, BLACK, 86, 250 + dy, t, WHAT_T - .02, sx=1.0, dist=300, stagger=.03)   # 英文大字只能用 ASCII 问号
    chip(frame, 86, 1140, '一位熬了三个通宵的邻家姐姐', 34, BLACK, CREAM, t, at(20, '一') - .05)
    w1 = chip(frame, (W - 900) // 2 + 24, 544, '写实：真写实', 32, CREAM, BLACK, t, at(20, '写') - .05)
    chip(frame, (W - 900) // 2 + 24 + (w1 or 220) + 14, 544, '美感：0', 32, BLACK, CREAM, t, at(20, '美') - .05)

def playbar(frame, x, y, w, p):
    d = ImageDraw.Draw(frame); d.rectangle([x, y, x + w, y + 4], fill=(205, 198, 186)); d.rectangle([x, y, x + w * p, y + 4], fill=CORAL)
    d.text((x + w, y + 14), f'00:0{int(p * 5)} / 00:05', font=F('monor', 18), fill=BLACK, anchor='ra')

def s_task4(frame, t):                    # 输入框带附件 → 缩略图放大成卡片 → 翻转播放视频 → 和参考图并排
    sec(frame, t, at(21, '生') - .1, BLACK, 'TASK 04', '生成视频', 'from a still to motion')
    end = word(frame, '让它动起来', 'heavy', 150, BLACK, 86, 310, t, at(21, '生') - .05, sx=1.12)
    dot(frame, end + 30, 450, t, at(21, '生') + .45, CORAL, 20)
    CW, CHh = 900, 506; bx, by = (W - CW) // 2, 560
    if t < SEND4 + .05:
        inputbox(frame, t, 60, 560, 960, P4, TYPE4, SEND4, attach=COVER, t_attach=at(21, '封') - .1, alpha=eo(P(t, at(21, '生') + .3, .3))); return
    g = eio(P(t, SEND4 + .05, .4))
    cov = lambda w, h: ImageOps.fit(img(COVER), (w, h))
    if g < 1:
        inputbox(frame, t, 60, 560, 960, P4, TYPE4, SEND4, attach=COVER, t_attach=at(21, '封') - .1, alpha=1 - g)
        cw, chh = int(208 + (CW - 208) * g), int(117 + (CHh - 117) * g); cx, cy = int(104 + (bx - 104) * g), int(584 + (by - 584) * g)
        shadow(frame, cx, cy, cw, chh); frame.alpha_composite(rounded(cov(CW, CHh).resize((cw, chh)), 12 + int(10 * g)), (cx, cy)); return
    split = eio(P(t, at(23, '一') - .35, .6)); flip = P(t, VID_T0 - .35, .35); vt = t - VID_T0
    vf = video_at(ROBOT, CW, CHh, vt)
    if split <= 0:
        sx = abs(math.cos(flip * math.pi)); fw = max(2, int(CW * sx)); x = bx + (CW - fw) // 2
        face = cov(CW, CHh) if flip < .5 else vf
        shadow(frame, x, by, fw, CHh); frame.alpha_composite(rounded(face.resize((fw, CHh))), (x, by))
        if flip < .5: chip(frame, bx, by - 58, '参考图 · Muse 画的封面', 24, BLACK, CREAM, t, SEND4 + .35)
        elif flip >= 1: chip(frame, bx, by - 58, 'Muse 生成 · 5s', 24, CORAL, CREAM); playbar(frame, bx, by + CHh + 14, CW, vt % 5 / 5)
    else:
        sw, sh_ = int(CW + (430 - CW) * split), int(CHh + (242 - CHh) * split)
        lx = int(bx + (90 - bx) * split); rx = int(bx + (560 - bx) * split); ly = int(by + (640 - by) * split)
        frame.alpha_composite(fade(rounded(cov(sw, sh_), 18), split), (lx, ly))
        shadow(frame, rx, ly, sw, sh_); frame.alpha_composite(rounded(vf.resize((sw, sh_)), 18), (rx, ly))
        if split >= 1:
            text(frame, (90, ly + sh_ + 22), '参考图', 'bold', 30, BLACK); text(frame, (560, ly + sh_ + 22), 'Muse 生成的视频', 'bold', 30, BLACK)
            text(frame, (W / 2, ly + sh_ / 2), '=', 'black', 60, CORAL, 'mm')
            chip(frame, W / 2, ly + sh_ + 90, '角色 · 场景 基本一致', 34, CORAL, CREAM, t, at(23, '一') + .3, anchor='c')
    steps = [('打字', at(22, '打')), ('抬头', at(22, '抬')), ('挥手', at(22, '挥'))]
    sy = 1110 if split <= 0 else 1050; x = 90
    for i, (s_, ts) in enumerate(steps):
        if eob(P(t, ts - .08, .3)) <= 0: break
        x += chip(frame, x, sy, f'0{i + 1}  {s_}', 30, CORAL if t >= at(23, '动') else BLACK, CREAM) + 16
        if i < 2 and t >= steps[i + 1][1] - .1: text(frame, (x, sy + 8), '→', 'bold', 34, BLACK); x += 52

def s_onechat(frame, t):                  # 同一个对话里接力
    sec(frame, t, ls(24), BLACK, 'THE BIG ONE', '最实用的地方', 'one chat, whole job')
    title(frame, t, '一个对话', at(24, '同') - .1, BLACK, dotc=CREAM, size=190)
    d = ImageDraw.Draw(frame); p0 = eo(P(t, ls(24) + .1, .4))
    if p0 > 0:
        d.rounded_rectangle([70, 520, W - 70, 520 + int(560 * p0)], 34, outline=BLACK, width=5)
        text(frame, (110, 540), 'MUSE · CHAT', 'mono', 24, BLACK, alpha=p0); avatar(frame, W - 130, 560, 26 * p0, t)
    steps = [('查资料', '查'), ('写网页', '写'), ('画封面', '画'), ('生成视频', '生')]
    for i, (s_, ch) in enumerate(steps):
        ts = at(24, ch) - .05
        if P(t, ts, .35) <= 0: continue
        y = 610 + i * 112; chip(frame, 120, y, f'0{i + 1}  {s_}', 40, BLACK, CREAM, t, ts)
        if i < 3:
            q = eo(P(t, at(24, steps[i + 1][1]) - .25, .25))
            if q > 0: d.line([(150, y + 76), (150, y + 76 + 34 * q)], fill=BLACK, width=5)
    chip(frame, W / 2, 1130, '中间不用来回换工具', 36, BLACK, CREAM, t, at(24, '不') - .05, anchor='c')

def s_task5(frame, t):
    sec(frame, t, ls(25) + .1, CREAM, 'TASK 05', '日程和规划', 'drafts first')
    title(frame, t, '日程和规划', ls(25) + .2, CREAM, size=170, t_out=at(25, '约') - .25); title(frame, t, '约个会议', at(25, '约'), CREAM, size=170)
    box = img_card(frame, '06-场景2-连接日历与邮件草稿.png', 130, 500, 820, t, at(25, '写') - .1)
    if not box: return
    x, y, w, h = box; tc = at(25, '连')
    if t > tc - .1:
        pointer(frame, t, tc - .1, x + w - 40, y + h * .27, x + w * .1, y + h * .27, CORAL)
        chip(frame, x + w + 10, y + h * .27 - 30, '先得连上日历', 30, CORAL, CREAM, t, tc - .1, anchor='r')
    chip(frame, x + w + 10, y + h - 20, '没干等：草稿先写好了', 32, CORAL, CREAM, t, at(25, '草') - .05, anchor='r')
    chip(frame, x, y + h + 60, '（挺会来事）', 30, CREAM, BLACK, t, at(25, '来') - .1)

def s_task5_trip(frame, t):
    sec(frame, t, ls(26), BLACK, 'TASK 05', '周末游规划', 'from Shanghai')
    th = at(26, '杭')
    title(frame, t, '周末去哪', at(26, '周') - .2, BLACK, dotc=CREAM, size=170, t_out=th - .25); title(frame, t, '杭州', th, BLACK, dotc=CREAM, size=200)
    box = img_card(frame, '09-场景3-行程概览.png', 250, 500, 580, t, th - .1, crop=(0, 0, 1, .62))
    if not box: return
    x, y, w, h = box; tl = at(26, '灵')
    if t > tl - .1:
        pointer(frame, t, tl - .1, x + w + 30, y + h * .66, x + w * .62, y + h * .66, BLACK)
        chip(frame, W - 60, y + h * .66 - 90, '灵隐 · 需提前一天预约', 30, BLACK, CREAM, t, tl - .1, anchor='r')

def s_task5_ask(frame, t):
    sec(frame, t, ls(27), BLACK, 'TASK 05', '没自作主张', 'did as told')
    title(frame, t, '照做了', at(27, '照') - .1, BLACK, size=200)
    a1 = chip(frame, 90, 620, '先别发送', 44, BLACK, CREAM, t, at(27, '先') - .05)
    chip(frame, 90 + (a1 or 230) + 20, 620, '不要预订', 44, BLACK, CREAM, t, at(27, '不') - .05)
    p = eob(P(t, at(27, '照') - .1, .4))
    if p > 0:
        d = ImageDraw.Draw(frame); cx, cy, r = W / 2, 900, 120 * p
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CORAL)
        if p > .7: check(d, cx - 55, cy - 50, 110, CREAM, 14)
        text(frame, (cx, cy + 170), 'NO SURPRISE ACTIONS', 'mono', 24, BLACK, 'mm', alpha=min(1, p))

def s_cons_song(frame, t):
    sec(frame, t, ls(28), BLACK, 'CONS · 01', '该吐槽了', 'not quite Song dynasty')
    title(frame, t, '吐槽时间', ls(28) + .15, BLACK, dotc=CREAM, size=200, t_out=at(28, '古') - .25)
    title(frame, t, '古风审美', at(28, '古'), BLACK, dotc=CREAM, size=190)
    tj = at(28, '交')
    if t < tj + .2: img_card(frame, '51-场景12-宋代古风-大图.png', 60, 520, 960, t, at(28, '古') - .1)
    if t >= tj - .1:
        im = img('52-场景12-宋代古风-衣领盘扣.png'); w = 600; h = int(im.height * w / im.width); x, y = 80, 500
        shadow(frame, x, y, w, h); frame.alpha_composite(fade(rounded(im.resize((w, h), Image.LANCZOS), 20), eo(P(t, tj - .1, .35))), (x, y))
        for k, (fx, fy) in enumerate([(.69, .59), (.49, .80)]): ring(frame, x + w * fx, y + h * fy, 38, t, tj + .3 + k * .15, CREAM)
        yy = 520
        for s_, ch in [('交领 + 盘扣', '交'), ('盘扣：明清以后', '明'), ('抹胸：没画', '抹'), ('训练数据不够？', '训')]:
            chip(frame, W - 70, yy, s_, 30, BLACK, CREAM, t, at(28, ch) - .1, anchor='r'); yy += 90

def s_cons_cn(frame, t):
    sec(frame, t, ls(29), CREAM, 'CONS · 02', '连接器', 'connectors')
    title(frame, t, '没有国内应用', ls(29) + .2, CREAM, size=150)
    for i, (s_, ch) in enumerate([('飞书', '飞'), ('微信', '微')]):
        ts = at(29, ch) - .05; p = eob(P(t, ts, .4))
        if p <= 0: continue
        x, y = 90 + i * 470, 640
        ImageDraw.Draw(frame).rounded_rectangle([x, y, x + 430 * p, y + 260 * p], 30, outline=CREAM, width=4)
        if p > .7:
            text(frame, (x + 215, y + 110), s_, 'heavy', 100, CREAM, 'mm'); text(frame, (x + 215, y + 210), 'NOT SUPPORTED', 'mono', 22, CORAL, 'mm')
            strike(frame, t, ts + .35, x + 50, x + 380, y + 115, CORAL, 10)
    chip(frame, W / 2, 1000, '天天用飞书办公的：暂时帮不上', 34, CORAL, CREAM, t, at(29, '天') - .05, anchor='c')

def s_quota(frame, t):                    # 额度：大数字 + 设置页截图
    sec(frame, t, ls(30), BLACK, 'QUOTA', '额度', 'free tier')
    tn = at(31, '9')
    title(frame, t, '额度够吗', ls(30) + .15, BLACK, size=190, t_out=tn - .3)
    if t >= tn - .3:
        big_number(frame, t, tn - .2, 9, '%', 86, 250, 300, BLACK)
        a = min(1, eexp(P(t, tn - .2, .8)))
        text(frame, (640, 330), '每周限额', 'heavy', 64, BLACK, alpha=a); text(frame, (640, 420), '五个任务全算上', 'med', 36, BLACK, alpha=a)
    box = img_card(frame, '53-额度-使用情况-卡片.png', 60, 640, 960, t, at(30, '免') - .1)
    if box:
        x, y, w, h = box
        chip(frame, 60, y + h + 24, '送的 10 亿词元：一个没用', 32, BLACK, CREAM, t, at(31, '亿') - .1)
        chip(frame, W - 60, y + h + 24, '免费够用', 34, CREAM, BLACK, t, at(32, '够') - .1, anchor='r')

def s_verdict(frame, t):
    sec(frame, t, ls(33) + .2, BLACK, 'VERDICT', '总结', 'one chat, whole job')
    title(frame, t, '总结一下', ls(33) + .15, BLACK, size=190, t_out=at(33, '一') - .25); title(frame, t, '一个对话做完', at(33, '一'), BLACK, size=160)
    d = ImageDraw.Draw(frame)
    for i, (s_, ch) in enumerate([('查资料', '查'), ('写小工具', '写'), ('画图', '画'), ('出短视频', '出')]):
        ts = at(33, ch) - .05; p = eo(P(t, ts, .3))
        if p <= 0: continue
        y = 560 + i * 100; q = eob(P(t, ts + .1, .3)); r = 30 * q
        d.ellipse([120 - r, y + 34 - r, 120 + r, y + 34 + r], fill=CORAL)
        if q > .8: check(d, 104, y + 20, 32, CREAM, 5)
        text(frame, (180, y + 4 + 20 * (1 - p)), s_, 'heavy', 56, BLACK, alpha=p)
    chip(frame, 90, 1000, '要求写得越细，结果越靠谱', 34, CORAL, CREAM, t, at(33, '细') - .1)

def s_short(frame, t):
    sec(frame, t, ls(34), CREAM, 'VERDICT', '但是', 'who should wait')
    title(frame, t, '还是短板', ls(34) + .1, CREAM, size=170, t_out=ls(35) - .2)
    x = 90
    for s_, ch in [('中国审美', '中'), ('国内生态', '国')]: x += chip(frame, x, 560, s_, 40, CORAL, CREAM, t, at(34, ch) - .05) + 16
    title(frame, t, '适合谁', ls(35), CREAM, size=170)
    a = eo(P(t, at(35, '飞') - .2, .4)); b = eo(P(t, at(35, '只') - .1, .4))
    text(frame, (90, 700), '主要用飞书、微信办公', 'heavy', 60, CREAM, alpha=a); text(frame, (90, 790), '→ 再等等', 'heavy', 60, CORAL, alpha=a)
    text(frame, (90, 920), '只想聊聊天', 'heavy', 60, CREAM, alpha=b); text(frame, (90, 1010), '→ 普通聊天 AI 就够了', 'heavy', 60, CORAL, alpha=b)

def s_simple(frame, t):
    sec(frame, t, ls(36), BLACK, 'NOTE', '说明一下', 'just a quick test')
    title(frame, t, '简单测试', at(36, '简') - .1, BLACK, dotc=CREAM, size=200)
    text(frame, (90, 620), '五个任务，说明不了全部', 'heavy', 64, BLACK, alpha=eo(P(t, at(36, '五') - .1, .4)))
    text(frame, (90, 740), '它还能干啥？坑在哪？', 'heavy', 64, BLACK, alpha=eo(P(t, at(36, '它') - .1, .4)))
    chip(frame, 90, 880, '更多还得你自己上手去发现', 40, BLACK, CREAM, t, at(36, '自') - .1)

def s_cta(frame, t):
    sec(frame, t, ls(37), BLACK, 'NEXT', '下期实测', 'your turn')
    title(frame, t, '评论区见', at(37, '评'), BLACK, dotc=CREAM, size=200)
    a = eob(P(t, ls(37) - .1, .4))
    if a > 0: avatar(frame, W / 2, 680, 100 * a, t, ring=BLACK)
    inputbox(frame, t, 60, 830, 960, P_CTA, (ls(37) + .1, at(37, '评') - .3), at(37, '下') - .1, alpha=eo(P(t, ls(37), .3)))

# ---------- 段落表：(开始, 底色, 前景色, 右上章节, 任务进度, 场景, 转场起点 c/b/dot/cut) ----------
SEGS = [
    (0.0, BLACK, CREAM, '00 — INTRO', 0, s_dot, 'c'),
    (0.22, CREAM, BLACK, '00 — INTRO', 0, s_intro, 'c'),
    (ls(1) - .35, CORAL, BLACK, '00 — INTRO', 0, s_question, 'dot'),
    (ls(2) - .3, BLACK, CREAM, '00 — INTRO', 0, s_five, 'c'),
    (ls(3) - .35, BLUE, CREAM, '00 — WHAT IS MUSE', 0, s_what, 'b'),
    (ls(4) - .3, CREAM, BLACK, '00 — WHAT IS MUSE', 0, s_cloud, 'c'),
    (ls(5) - .3, BLACK, CREAM, '00 — WHAT IS MUSE', 0, s_app, 'b'),
    (ls(6) - .35, BLACK, CREAM, '01 — RESEARCH', 1, s_task1, 'c'),
    (T1SHOT, BLUE, CREAM, '01 — RESEARCH', 1, s_task1_shot, 'b'),
    (ls(10) - .35, CORAL, BLACK, '02 — CODE', 2, s_task2, 'c'),
    (ls(11) - .3, CREAM, BLACK, '02 — CODE', 2, s_task2_preview, 'b'),
    (ls(12) - .3, BLACK, CREAM, '02 — CODE', 2, s_task2_site, 'c'),
    (ls(14) - .35, BLUE, CREAM, '03 — IMAGE', 3, s_task3, 'c'),
    (ls(16) - .3, CREAM, BLACK, '03 — IMAGE', 3, s_task3_portrait, 'b'),
    (ls(17) - .3, BLACK, CREAM, '03 — IMAGE', 3, s_task3_flaw, 'c'),
    (ls(18) - .3, BLUE, CREAM, '03 — IMAGE', 3, s_task3_song, 'b'),
    (WHAT_T - .02, CORAL, BLACK, '03 — IMAGE', 3, s_task3_reveal, 'cut'),
    (ls(21) - .4, CREAM, BLACK, '04 — VIDEO', 4, s_task4, 'c'),
    (ls(24) - .35, CORAL, BLACK, '04 — VIDEO', 4, s_onechat, 'c'),
    (ls(25) - .35, BLACK, CREAM, '05 — PLANNING', 5, s_task5, 'c'),
    (ls(26) - .3, CORAL, BLACK, '05 — PLANNING', 5, s_task5_trip, 'b'),
    (ls(27) - .3, CREAM, BLACK, '05 — PLANNING', 5, s_task5_ask, 'c'),
    (ls(28) - .4, CORAL, BLACK, '06 — CONS', 5, s_cons_song, 'c'),
    (ls(29) - .3, BLACK, CREAM, '06 — CONS', 5, s_cons_cn, 'b'),
    (ls(30) - .4, CREAM, BLACK, '07 — QUOTA', 5, s_quota, 'c'),
    (ls(33) - .4, CORAL, BLACK, '08 — VERDICT', 5, s_verdict, 'c'),
    (ls(34) - .3, BLUE, CREAM, '08 — VERDICT', 5, s_short, 'b'),
    (ls(36) - .35, CREAM, BLACK, '08 — VERDICT', 5, s_simple, 'c'),
    (ls(37) - .35, CORAL, BLACK, '08 — VERDICT', 5, s_cta, 'c'),
]

# ================= 钩子 =================
def _hook_finale(frame, t, hk):           # 派了五个活 -> 真干活 or 光会画饼
    tz = hk.hk('真'); c = R.CROP // 2
    word(frame, '派了五个活', 'heavy', 150, BLACK, 86, 240 + c, t, hk.seg[-1] - .02, stagger=.04, dist=380, t_out=tz - .25)
    word(frame, '真干活', 'heavy', 190, BLACK, 86, 220 + c, t, tz - .05, stagger=.04, dist=380)
    text(frame, (W / 2, 560 + c), 'or', 'serif', 120, CORAL, 'mm', alpha=eo(P(t, hk.hk('还') - .1, .3)))
    end = word(frame, '光会画饼', 'heavy', 180, BLACK, 86, 660 + c, t, hk.hk('画', 1) - .1, stagger=.04, dist=380, from_left=True)
    dot(frame, end + 34, 828 + c, t, hk.hk('饼') + .1, CORAL, 22)

HOOK = Hook('配音/hook/words.json', '配音/hook/audio/vo_00.wav', beats=[
    dict(key='查', label='查资料', bg=CORAL, fg=BLACK, cards=[('04-场景1-结果表格.png', W / 2, 830, 940, -3, .05)]),
    dict(key='写', label='写代码', bg=BLUE, fg=CREAM, cards=[('38-场景9-前端审美-首屏.png', W / 2 - 60, 830, 860, 3, .05),
                                                           ('43-场景10-番茄钟重测-运行中-卡片.png', W - 230, 950, 300, -5, .22)]),
    dict(key='画', label='画图', bg=CREAM, fg=BLACK, cards=[('47-场景11-真人生图-大图.png', W / 2, 830, 920, -2.5, .05)]),
    dict(key='做', label='做视频', bg=BLACK, fg=CREAM, cards=[(lambda tt: video_at(ROBOT, 900, 506, 2.2 + tt, loop=False), W / 2, 830, 940, 2.5, .05)]),
], finale_key='派', finale=_hook_finale, send_key='饼',
   sting=dict(line1='Muse', line2='实测', serif='a quick, honest hands-on'),
   cues=[(0, '派', '查资料、写代码、画图、做视频'), ('派', '看', '我给这个 AI 智能体派了五个活'), ('看', None, '看看它是真干活，还是光会画饼')])

# ================= 声音 =================
def extra_audio(vo, sr):
    """生成视频第一遍播放时混入原声，压在人声下面"""
    ra = pcm(ROBOT, sr)
    if len(ra):
        ra = ra * 10 ** ((-26 - 20 * np.log10(np.sqrt(np.mean(ra ** 2)) + 1e-9)) / 20)
        k = int(.3 * sr); ra[-k:] *= np.linspace(1, 0, k)
        i = int(VID_T0 * sr); j = min(len(vo), i + len(ra)); vo = vo.copy(); vo[i:j] += ra[:j - i]
    return vo

def sfx(fx):
    for p in [at(0, '替') + .5, at(1, '直') + .5, at(3, '交') + .4, at(15, '错'), at(15, '卡'), at(25, '草'), at(26, '灵'),
              at(27, '照'), at(28, '明'), at(29, '飞'), at(29, '微'), at(31, '亿'), at(32, '够'), at(33, '细'), at(37, '评') + .4]:
        fx.pop(p - .05)
    for p in [at(2, '五') + .25 + i * .12 for i in range(5)] + [at(3, c) for c in '查写画'] + [at(4, c) for c in '邮日'] + \
             [at(16, c) for c in '皮碎胶'] + [at(33, c) for c in '查写画出'] + [at(11, c) for c in '刻大暂'] + \
             [at(24, c) for c in '查写画生'] + [at(28, c) for c in '交明抹训']:
        fx.pop(p - .05)
    for c in '价降续重':
        for i in range(3): fx.key(at(8, c) + .08 + i * .08, .07)
    for a, b in [(at(6, '信') + .5, le(6) - .1), (at(10, '我') + .05, at(10, '说') - .3), (at(14, '我') + .05, le(14) - .35), TYPE4,
                 (at(5, '写'), le(5) - .2), (at(18, '宋') + .1, at(18, '重') - .3), (ls(37) + .1, at(37, '评') - .3)]:
        fx.typing(a, b)
    for s_ in [le(6) + .05, at(10, '说') - .1, le(14) - .15, SEND4, at(18, '重') - .15]: fx.pop(s_, 660, .08, .05)
    fx.clip(WHAT_T, WHAT_FILE, 1.6)                 # "What？" 包袱音效
    fx.hit(WHAT_T, 55, .5, .35)
