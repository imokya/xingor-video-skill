"""真人口播 · poetry-ink. The speaker explains how the 苏轼 ink video (../苏轼简介_诗墨_16x9_v5.mp4) was made.
Source seconds from transcript.json word timestamps. The hook is three clips of that finished video, with its own sound,
because the speaker opens with "你刚才看到的这段苏轼水墨诗词视频".
"""
from components import *
from ink import *

THEME = 'poetry-ink'
import ink
ink.TURN = 'cut'     # the footage already has ink page turns; the presenter edit changes calmly, no extra ink
BROLL = '../苏轼简介_诗墨_16x9_v5.mp4'

KEYWORDS = ['苏轼', '水墨诗词', 'xingor video skill', 'Poetry Ink', 'Skill', 'AI', '画面', '字体', '配色', '水墨氛围',
            '诗词意境', '提示词', '评论区']

HOOK = dict(
    clips=[
        dict(path=BROLL, s0=0.0, s1=2.05, gain=.85, label='成片 · 苏轼简介', fit='cover'),     # 苏轼的一生并不顺利
        dict(path=BROLL, s0=18.98, s1=21.6, gain=.85, label='成片 · 苏轼简介', fit='cover'),   # 但愿人长久，千里共婵娟
        dict(path=BROLL, s0=32.36, s1=35.9, gain=.85, label='成片 · 苏轼简介', fit='cover'),   # 人生可以有风雨…豁达、浪漫
    ],
    kicker='诗墨 · 成片先览',
    outro='制作揭秘',
)


S0 = 5.45   # the footage plays continuously from here: footage time = t - S0


def show(t0, t1, **kw):
    return InkShowcase(t0, t1, broll=BROLL, b0=t0 - S0, s_first=S0, name='阿星 · 口播', smooth_in=True, layout='full', crop=None, **kw)


def build_scenes():
    return [
        # 你刚才看到的这段苏轼水墨诗词视频，其实是我用自己的xingor video skill生成的   (theme text behind the speaker)
        InkBehind(0, 5.45, text='水墨诗词', text_t=1.45, size=210, sub=(3.96, 'xingor-video-skill'), seal=('诗墨', 4.9)),
        # 水墨诗词只是这个Skill里面其中一种风格，名字叫Poetry Ink      (the speaker shrinks into the avatar: the transition)
        show(5.45, 10.3, avatar_in='full', headline=(5.86, '一种风格'), tags=[(7.64, '其中之一'), (9.32, 'Poetry Ink')], seal=(9.9, '诗墨')),
        # 安装好这个Skill以后，你只需要告诉AI，用Poetry Ink风格，帮我生成一段介绍苏轼的口播视频
        show(10.3, 17.4, headline=(10.46, '只需一句'), tags=[(10.6, '安装'), (12.0, '告诉')],
             strip=(13.38, 17.0, '用 Poetry Ink 风格，帮我生成一段介绍苏轼的口播视频。')),
        # 接下来，从画面、字体、配色，到水墨氛围和诗词意境
        show(17.4, 22.4, headline=(17.62, '皆成风格'), tags=[(18.5, '画面'), (19.1, '字体'), (19.74, '配色'),
                                                        (20.52, '水墨'), (21.46, '意境')]),
        # AI都会按照Skill里预设好的风格自动生成，不需要每次重新研究提示词
        show(22.4, 27.7, headline=(24.62, '自动生成'), tags=[(25.68, '不必再研究'), (27.08, '提示词')]),
        # 整个过程其实非常简单
        show(27.7, 29.5, headline=(28.95, '大道至简')),
        # 如果你也喜欢这个Skill的风格，或者想获取这套提示词和使用方法
        show(29.5, 33.95, headline=(29.56, '想要同款'), tags=[(30.3, '风格'), (32.62, '提示词'), (33.2, '用法')]),
        # 欢迎在评论区和我交流     (footage dims, a big card lands, the avatar grows)
        show(33.95, 36.3, cta=(34.44, '评论区见'), seal=(35.0, '交流'), avatar_big=(34.1, (1920 * .78, 1080 * .46, 230))),
    ]
