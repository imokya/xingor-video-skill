"""苏轼简介 — poetry-ink, 16:9 (1920x1080), narration audio only (no presenter).
Times are source seconds from transcript.json word timestamps.
Poem lines are exact quotes: 念奴娇·赤壁怀古 (大江东去，浪淘尽), 水调歌头 (但愿人长久，千里共婵娟),
定风波 (一蓑烟雨任平生, shown on screen, not spoken). Biographical years: 1037—1101, 黄州 1080, 惠州 1094, 儋州 1097.
"""
from components import *
from ink import *

THEME = 'poetry-ink'

KEYWORDS = ['苏轼', '黄州', '惠州', '海南', '大江东去', '但愿人长久', '诗意', '豁达', '浪漫']

HOOK = None   # narration plays straight through from the mp3 (no replayed cold open)


def build_scenes():
    return [
        # 苏轼的一生并不顺利，他才华横溢却几度被贬
        PCover(0, 4.4, lines=[(0.05, '苏轼的一生')], sub=(2.5, '才华横溢 · 几度被贬'), note=(3.4, '北宋 · 1037 — 1101'),
               ghost=('苏',), sidebar='人物 · 诗词', corner=('北宋文豪', '东坡居士'), seal=(3.9, '东坡'),
               backdrop='../bg.png', fade=.42, safe=(0, .62)),   # cover only: the painting as a faded background
        # 从繁华京城一路走到黄州、惠州甚至海南
        PRoute(4.4, 8.3, title=(4.5, '一路南迁'), ghost='贬', stops=[
            (4.94, '京城', '汴京'), (6.02, '黄州', '1080'), (6.78, '惠州', '1094'), (7.58, '海南', '儋州 · 1097')]),
        # 可无论身处怎样的困境，他似乎总能找到生活的乐趣
        PTorn(8.3, 12.7, cover=(9.5, '困境'), text='乐趣', text_t=11.85, seal=(12.2, '趣'), kicker=(8.4, '无论身处何境')),
        # 被贬黄州，他写下“大江东去，浪淘尽”
        PPoem(12.7, 16.6, bg='river', kicker=(12.78, '被贬黄州'), ghost='江',
              lines=[(14.44, 15.25, '大江东去'), (15.64, 16.3, '浪淘尽')],
              author=(15.9, '苏轼 · 念奴娇'), seal=(16.25, '东坡')),
        # 夜深思念亲人，他留下“但愿人长久，千里共婵娟”
        PPoem(16.6, 21.7, bg='moon', kicker=(16.68, '夜深 · 思亲'), ghost='月',
              lines=[(19.1, 19.95, '但愿人长久'), (20.48, 21.35, '千里共婵娟')],
              author=(20.9, '苏轼 · 水调歌头'), seal=(21.35, '子瞻')),
        # 别人看到的是诗意，苏轼看到的却是江风、明月、美酒和人生
        PWords(21.7, 27.0, lead=(21.8, '别人看到的是诗意'), head=(23.36, '苏轼看到的却是'),
               words=[(24.7, '江风'), (25.44, '明月'), (26.08, '美酒'), (26.56, '人生')], seal_last='生'),
        # 也正因为如此，千年之后，我们依然喜欢苏轼
        PBig(27.0, 31.1, lines=[(28.75, '千年之后'), (29.68, '依然喜欢')], ghost='苏', seal=(30.3, '苏轼')),
        # 因为他告诉我们，人生可以有风雨，但依然可以活得豁达、浪漫
        PEnd(31.1, 38.4, lead=(32.4, '人生可以有风雨'), rain=(32.95, 34.3), big=[(34.62, '豁达'), (35.25, '浪漫')],
             quote=(33.2, '一蓑烟雨任平生'), source='苏轼《定风波》', seal=(35.9, '东坡')),
    ]
