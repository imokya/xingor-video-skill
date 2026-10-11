"""Example of the designed-look path (no style named), cut on the same 93 s video as scenes.py.
analyze_shot.jpg = any still of the edit to annotate (put one in the work dir).
Brief: AI 自动剪辑科普，科技博主口播，16:9，自信轻快，语速中等偏快，真人出镜。
Character: tech (kit.fit) -> NEON family + neutral blocks only, no ink components; iris turns, electronic sounds.
Theme: tech blue on a clean light page, modern voice, snappy (kit.theme.design).
Numbers on screen are real: 2335 frames / 93 s are this video's own values.
"""
from components import *
from kit.blocks import *
import kit.theme as KT

THEME = KT.design('AI 剪辑', '#2F5DFF', 'light', voice='modern', tempo='snappy', turn='iris')

KEYWORDS = ['Opus 5.5', 'MiniMax', 'HeyGen', 'skill', '数字人', '真人实拍', '大字', '图片', '动画', '音效', 'AI',
            '评论区', '节奏', '文字排版', '人物身后', '提示词', '剪辑', '动效', '重复调用', '自动']

HOOK = dict(clips=[dict(s0=4.25, s1=6.45, text='不是我拍的', text_t=1.0), (9.75, 12.75)], kicker='AI 剪辑 · 精彩预告')


def build_scenes():
    return [
        # 你现在看到的这个人是我，声音也是我的
        TitleCard(0, 3.05, show_person=True, kicker=(0.2, '一条 AI 剪的视频'), title=(0.4, '这个人是我'), sub=(2.0, '声音也是我的')),
        # 但这条视频，其实不是我坐在镜头前拍出来的
        TypeBehind(3.05, 6.5, text='不是我拍的', text_t=4.3),
        # 后面的剪辑和动效，我也基本没有自己动手
        BigStat(6.5, 9.7, show_person=True, title=(6.7, '剪辑 · 动效'), stats=[(8.6, 0, '', '%', '自己动手')]),
        # 我只是把口播内容交给了Opus 5.5
        TypeBehind(9.7, 12.8, text='Opus 5.5', text_t=11.55, size=230),
        # 它先用MiniMax生成我的声音，再用HeyGen驱动数字人，把这段内容讲出来
        ListSteps(12.8, 18.7, show_person=True, label=(12.9, '流程 · 01'), title=(13.0, 'AI 制作流水线'), items=[
            (13.15, 'MiniMax', '生成我的声音'), (15.35, 'HeyGen', '驱动数字人'), (17.3, '口播成片', '把内容讲出来')]),
        # 接下来才是我觉得最有意思的部分
        TitleCard(18.7, 20.86, hud=True, tag='NEXT', kicker=(18.8, '接下来'), title=(19.0, '最有意思的部分')),
        # 我给它看了一些…视频效果，让它分析节奏、文字排版和动画方式，然后自动去安排画面
        Callouts(20.86, 30.4, image='analyze_shot.jpg', title=(21.1, '拆解喜欢的视频'),
                 callouts=[(25.0, (.3, .3), (1460, 330), '节奏'), (25.75, (.45, .55), (1500, 520), '文字排版'),
                           (26.35, (.7, .8), (1460, 710), '动画方式')]),
        # 哪里需要大字，哪里需要图片，哪里适合加动画和音效，它都会自己去判断
        TalkCard(30.4, 36.05, theme='paper', label='口播', hud='// 02 — 判断', path=[(30.4, 'full'), (30.45, 'right')],
                 kicker='哪里需要什么', lines=[(30.8, '[大字] · 图片'), (33.5, '[动画] · 音效')], items=[(34.6, 'AI 自己判断')]),
        # 而且，我没有让这套流程只用一次
        TitleCard(36.05, 38.83, kicker=(36.2, '而且'), title=(36.5, '不止用一次')),
        # 做完之后…整理成了一个可以重复调用的skill。这样以后…不用每次重新设计
        MetalTitle(38.83, 48.6, title=(42.6, '沉淀成 Skill'), sub=(44.0, '可 重 复 调 用')),
        # 只要给它一段新的口播…再把节奏和音效一起补上
        ListSteps(48.6, 57.8, show_person=True, label=(48.7, '流程 · 03'), title=(48.75, '一段口播 → 一条成片'), items=[
            (48.85, '新的口播', '丢进一段口播'), (50.95, '理解内容', '读懂每一句'), (51.9, '拆出画面', '该配什么'),
            (53.8, '文字动画', '一并生成'), (55.5, '节奏音效', '卡点补齐')]),
        # 而且，这套skill不只是数字人能用，真人实拍的视频一样可以处理
        BehindText(57.8, 63.1, text='真人也行', text_t=59.4, tag='REAL FOOTAGE · 真人实拍', tag_t=58.6),
        # 比如我之前拍过一段真人口播，它可以先把人物从背景里分离出来，再把大字放到人物身后
        TypeBehind(63.1, 69.2, text='放到身后', text_t=67.7),
        # 口播里如果出现数字、数据，或者一些重点内容，也可以直接变成更直观的动态画面
        BigStat(69.2, 75.7, show_person=True, title=(69.5, '数字 → 动态画面'),
                stats=[(70.4, 2335, '', '', '本片总帧数'), (72.15, 93, '', '秒', '本片时长')]),
        # 所以…很多原来需要一点点手动剪辑的工作，已经可以开始交给AI处理了
        CompareTable(75.7, 82.4, title=(75.9, '剪辑方式'), cols=[('手动剪辑', 'MANUAL'), ('交给 AI', 'AUTO')], t_cols=76.6,
                     rows=[('方式', ['一帧一帧', '一段口播'], 78.2, 1), ('音效', ['手动对齐', '自动卡点'], 79.5, 1),
                           ('结果', ['反复返工', '直接成片'], 80.9, 1)]),
        # 你现在看到的这整条视频，基本就是按照这套方式完成的
        TitleCard(82.4, 86.6, show_person=True, kicker=(82.6, '这整条视频'), title=(83.0, '就是这样做的')),
        # 如果你想看这套流程具体是怎么搭的…可以在评论区告诉我
        EndCard(86.6, 93.4, show_person=True, big=(91.7, '评论区见'), items=[(87.5, '流程怎么搭'), (89.9, '提示词'), (90.55, 'Skill 做法')]),
    ]
