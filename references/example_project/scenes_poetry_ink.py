"""Example project in the poetry-ink · 诗墨国风 style, cut on the same 93s talking-head video as scenes.py
("你现在看到的这个人是我…"). Times are source seconds from transcript.json word timestamps.
Headlines, mottos and the verses in PoemColumn are written for this edit (they paraphrase the speaker) and are
attributed to the speaker, not to a real poet. Copy this to the work dir as scenes.py and rewrite it.
See references/poetry-ink.md.
"""
from components import *
from ink import *

THEME = 'poetry-ink'

KEYWORDS = ['Opus 5.5', 'MiniMax', 'HeyGen', 'skill', '数字人', '大字', '动画', '音效', '评论区', '节奏']

HOOK = dict(
    clips=[
        dict(s0=4.25, s1=6.45, text='非我所拍', text_t=1.0),   # 但这条视频，其实不是我坐在镜头前拍出来的
        (9.75, 12.75),                                         # 我只是把口播内容交给了Opus 5.5
    ],
    outro='正片开始',
)


def build_scenes():
    return [
        # 你现在看到的这个人是我，声音也是我的 / 但这条视频…
        InkCover(0, 6.5, lines=[(0.5, '一段口播'), (1.1, '一卷水墨'), (1.7, '一首诗')], sub=(2.6, '诗墨国风 / AI 视觉剪辑'),
                 ghost=('诗', '韵'), vertical=('让想法被看见', '让表达更有诗意'), seal='雅', corner=('AI 赋能表达', '水墨传递诗意')),
        # 后面的剪辑和动效，我也基本没有自己动手
        InkBehind(6.5, 9.7, text='不亲手', text_t=7.1, seal=('墨', 8.4), sub=(8.6, '剪辑 · 动效')),
        # 我只是把口播内容交给了Opus 5.5 / 它先用MiniMax生成我的声音，再用HeyGen驱动数字人…
        PoemColumn(9.7, 18.7, lines=[(10.0, 12.0, '口播交予它'), (13.2, 15.0, '借声于万象'), (15.6, 17.6, '数字人言之')],
                   author=(17.0, '阿星 · 作'), seal=(17.9, '诗墨'), label='诗 · 意'),
        # 接下来才是我觉得最有意思的部分
        InkBehind(18.7, 21.0, text='妙处', text_t=19.4, font='xing', size=260),
        # 我给它看了一些…让它自己去分析…节奏、文字排版和动画方式，然后…自动去安排画面
        InkLandscape(21.0, 30.4, lines=[(21.6, '万般画面'), (22.6, '自成山水')], sub=(25.0, '节奏 · 排版 · 动画')),
        # 哪里需要大字，哪里需要图片，哪里适合加动画和音效，它都会自己去判断 / 而且…只用一次
        TalkCard(30.4, 38.8, theme='ink', label='阿星 · 口播', hud='卷二 · 判断',
                 path=[(30.4, 'full'), (30.45, 'right'), (34.6, 'left')],
                 kicker='何处需要什么', lines=[(30.8, '大字 · [图片]'), (33.4, '[动画]与音效')],
                 items=[(35.0, '自行判断'), (35.8, '不必再问')]),
        # 做完之后，我又让Opus 5.5把前面的制作方法，整理成了一个可以重复调用的skill。这样以后…就不用每次重新设计
        InkBehind(38.8, 48.6, text='反复可用', text_t=43.4, seal=('技', 44.6), sub=(46.6, '不必每次重新设计')),
        # 只要给它一段新的口播，它就可以自己理解内容，拆出需要展示的画面，生成对应的文字和动画，再把节奏和音效一起补上
        InkList(48.6, 57.8, label='方法 · 五步', title='一段口播 · 一条成片', items=[
            (48.85, '新的口播', '丢进一段口播'), (50.95, '理解内容', '读懂每一句'), (51.9, '拆出画面', '该配什么'),
            (53.8, '文字动画', '一并生成'), (55.5, '节奏音效', '卡点补齐')]),
        # 而且，这套skill不只是数字人能用，真人实拍的视频一样可以处理
        TornText(57.8, 63.1, text='真人亦可', text_t=59.6, seal=('真', 61.9), sub=(60.8, '实拍一样处理')),
        # 比如我之前拍过一段真人口播，它可以先把人物从背景里分离出来，再把大字放到人物身后
        InkLandscape(63.1, 69.2, lines=[(63.5, '人在画中'), (65.7, '字在身后')], sub=(67.7, '分离 · 叠层')),
        # 口播里如果出现数字、数据，或者一些重点内容，也可以直接变成更直观的动态画面
        TalkCard(69.2, 75.7, theme='ink', label='阿星 · 口播', hud='卷三 · 数据',
                 path=[(69.2, 'full'), (69.25, 'right')], kicker='数字 · 重点',
                 lines=[(70.4, '化作[画面]'), (72.2, '[一目]了然')], items=[(73.8, '直观'), (74.4, '生动')]),
        # 所以，现在做这种口播视频，很多原来需要一点点手动剪辑的工作，已经可以开始交给AI处理了
        TornText(75.7, 82.4, text='交给AI', text_t=80.5, style='scraps'),
        # 你现在看到的这整条视频，基本就是按照这套方式完成的
        InkBehind(82.4, 86.6, text='此片即是', text_t=82.9, font='xing', size=240),
        # 如果你想看这套流程具体是怎么搭的…可以在评论区告诉我
        InkEnd(86.6, 93.4, big=(91.7, '评论区见'), items=[(87.5, '流程'), (89.9, '提示词'), (90.55, 'skill')],
               seal=(92.4, '关注'), farewell=(88.0, '山水有相逢')),
    ]
