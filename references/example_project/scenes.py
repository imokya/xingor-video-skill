"""Example project: the 93s Chinese talking-head video this skill was distilled from
("你现在看到的这个人是我…" — an AI avatar explaining how Opus 5.5 edited the video).
Times are source seconds, taken from transcript.json word timestamps.
Copy this to the work dir as scenes.py and rewrite it for the new script.
"""
from components import *

KEYWORDS = ['Opus 5.5', 'MiniMax', 'HeyGen', 'skill', '数字人', '真人实拍', '大字', '图片', '动画', '音效', 'AI',
            '评论区', '节奏', '文字排版', '人物身后', '提示词', '剪辑', '动效', '重复调用', '自动', '数据', '重点内容', '最有意思', '直观']

# Cold open (see SKILL.md 4b): the strongest lines first, then the edit starts. Source seconds (approximate here;
# take real ones from hook.py / transcript.json).
HOOK = dict(
    clips=[
        dict(s0=4.25, s1=6.45, text='不是我拍的', text_t=1.0),   # 但这条视频，其实不是我坐在镜头前拍出来的
        (9.75, 12.75),                                         # 我只是把口播内容交给了Opus 5.5
    ],
    kicker='HIGHLIGHT · 精彩预告',
    outro='正片开始',
)


def build_scenes():
    return [
        # 你现在看到的这个人是我，声音也是我的
        Intro(0, 3.05, label='这个人 = 我', voice_t=2.0, voice_title='也是我的'),
        # 但这条视频，其实不是我坐在镜头前拍出来的
        BehindText(3.05, 6.5, text='不是我拍的', text_t=4.3, zoom=1.1, tag='NOT FILMED · 非实拍', tag_t=3.4),
        # 后面的剪辑和动效，我也基本没有自己动手
        Checklist(6.5, 9.7, label='POST-PRODUCTION', items=[(7.05, '剪辑', '手动'), (7.45, '动效', '手动')],
                  strike_t=8.6, verdict='0% 手工 · 全交给 AI', verdict_t=9.0),
        # 我只是把口播内容交给了Opus 5.5
        SplitWord(9.7, 12.8, left='OPUS', right='5.5', text_t=11.6, tag='MODEL'),
        # 它先用MiniMax生成我的声音，再用HeyGen驱动数字人，把这段内容讲出来
        Pipeline(12.8, 18.7, label='PIPELINE · 01', title='AI 制作流水线', nodes=[
            (13.15, '01 · VOICE', 'MiniMax', '生成我的声音', 'wave'),
            (15.35, '02 · AVATAR', 'HeyGen', '驱动数字人', 'face'),
            (17.3, '03 · OUTPUT', '口播成片', '把内容讲出来', 'play')]),
        # 接下来才是我觉得最有意思的部分
        PunchHeadline(18.7, 20.86, label='NEXT · 重点来了', lines=[(19.0, '最有意思'), (19.55, '的部分')], mark=(0, '有意思', 19.95)),
        # 我给它看了一些…视频效果，让它自己去分析…节奏、文字排版和动画方式，然后…自动去安排画面
        Analyze(20.86, 30.4, label='ANALYZE · 02', title='拆解喜欢的视频', enter_from=dark_xf(1.0, CP_X()),
                cards_t=21.6, scan_t=23.6, timeline_t=27.3,
                rows=[(25.0, '节奏', 'RHYTHM', 'rhythm'), (25.75, '文字排版', 'TYPOGRAPHY', 'type'), (26.35, '动画方式', 'MOTION', 'motion')]),
        # 哪里需要大字，哪里需要图片，哪里适合加动画和音效，它都会自己去判断
        FloatTags(30.4, 36.05, big=('大字', 30.8), props=[(31.95, 'image', '图片 IMAGE'), (33.5, 'motion', '动画 MOTION'), (33.95, 'sound', '音效')],
                  verdict=('AI 自己判断', 34.6)),
        # 而且，我没有让这套流程只用一次
        SwapSymbol(36.05, 38.83, old='×1', new='∞', old_t=36.3, strike_t=37.95, new_t=38.2, tag='REUSE · 不止用一次'),
        # 做完之后…整理成了一个可以重复调用的skill。这样以后再做类似的视频，就不用每次重新设计
        SkillCore(38.83, 48.6, label='PACKAGE · 03', title='沉淀成一个 Skill',
                  modules=['节奏分析', '文字排版', '动画模板', '字幕系统', '音效匹配', '人像分割'],
                  mods_t=41.2, converge_t=42.6, core_t=43.3, core_sub='video-fx.skill', core_chip='可重复调用',
                  emit_t=45.2, emit_title='以后直接复用', emit_label='同一个 Skill 反复出片', stamp=('不用每次重新设计', 47.5)),
        # 只要给它一段新的口播…再把节奏和音效一起补上
        Steps(48.6, 57.8, label='WORKFLOW · 04', title='一段口播 → 一条成片', enter_from=dark_xf(.72, 1560), steps=[
            (48.85, '新的口播', 'INPUT', '丢进一段口播.mp4', 'file', '口播.mp4'),
            (50.95, '理解内容', 'UNDERSTAND', '读懂每一句在讲什么', 'lines'),
            (51.9, '拆出画面', 'STORYBOARD', '决定每句话配什么画面', 'frames'),
            (53.8, '文字 + 动画', 'MOTION', '生成对应的字和动效', 'letters'),
            (55.5, '节奏 + 音效', 'RHYTHM · SFX', '卡点、音效一起补上', 'wave')]),
        # 而且，这套skill不只是数字人能用，真人实拍的视频一样可以处理
        SplitHalftone(57.8, 63.1, t_in=59.4, right_t=60.7, verdict='同一套 Skill 都能用', verdict_t=61.85),
        # 比如我之前拍过一段真人口播，它可以先把人物从背景里分离出来，再把大字放到人物身后
        MatteReveal(63.1, 69.2, reveal_t=65.7, text='放到身后', text_t=67.7),
        # 口播里如果出现数字、数据或者一些重点内容，也可以直接变成更直观的动态画面
        DataCards(69.2, 75.7, label='DATA · 05', title='数字 → 动态画面', cards=[
            (70.4, 'counter', {'label': 'FRAMES · 本片总帧数', 'unit': '帧'}),
            (71.15, 'bars', {'label': 'CHART · 数据', 'values': [.35, .55, .42, .7, .62, .95]}),
            (72.15, 'highlight', {'label': 'KEY POINT · 重点', 'text': '重点放大'}),
            (73.8, 'ring', {'label': 'MOTION · 动态', 'title': '直观', 'sub': '一眼看懂'})]),
        # 所以…很多原来需要一点点手动剪辑的工作，已经可以开始交给AI处理了
        Compare(75.7, 82.4, title='COMPARE · 剪辑方式', panel_t=76.6, slow=(78.2, '手动剪辑', '一帧一帧'), fast=(80.9, '交给 AI')),
        # 你现在看到的这整条视频，基本就是按照这套方式完成的
        ThisVideo(82.4, 86.6, timeline_t=83.0, stats_t=84.7),
        # 如果你想看这套流程具体是怎么搭的，或者想要相关的提示词和skill做法，可以在评论区告诉我
        CTA(86.6, 93.4, items=[(87.5, '① 流程怎么搭'), (89.9, '② 相关提示词'), (90.55, '③ Skill 做法')],
            big=('评论区见', 91.7), arrow=('留言告诉我', 92.1)),
    ]


def CP_X():
    return PERSON['head_x']
