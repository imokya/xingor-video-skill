# xingor-video-skill

一个 Claude Code Skill：把一段**口播 / talking-head 视频**（或一段旁白音频、一个主题）自动做成成片。三种风格：科技感的 **NEON LAB**、中国诗词韵味的 **poetry-ink · 诗墨国风**、不需要真人出镜的 **documentary · 文物纪录片**。

## 支持的效果

**通用**

- **逐字对齐的字幕**：Whisper 转写，关键词高亮
- **钩子（开头精彩片段）**：`hook.py` 按音量、语速、爆点词、提问和数字给片段打分，按视频长度给出钩子时长；可混入成片等 B-roll
- **剪辑**：自动缩短停顿、推拉镜头、按主题切换转场
- **程序合成音效**：跟动画同步；可选 BGM，自动避让人声
- **多画幅**：16:9、3:4、9:16

**NEON LAB（默认）** · 深墨色背景 + 荧光柠檬绿（#C6FF2E）

- **文字在人物背后**：AI 抠像（RobustVideoMatting）后，大字落在人物身后
- **MG / 演示动画**：流程图、步骤列表、数据卡片、数字人 vs 真人点阵对比、Skill 打包动画等 18 个镜头模板
- **口播小窗（TalkCard）**：人物放进竖向圆角 ON AIR 卡片，可从全屏缩成小窗，在右侧 / 左侧 / 圆形气泡之间弹簧变形移动，跟随人脸裁切
- **深色科技场景**：人物抠出缩到右侧，带荧光绿描边光，左侧放演示动画
- **转场与音效**：故障 / 斜切光带转场；whoosh、重击、弹出、上升音

**诗墨国风 · poetry-ink** · 宣纸 · 青黛 · 朱砂

- **纸墨质感**：程序生成的宣纸纹理，宋体 / 楷体 / 行楷排版，朱砂印章、圆点、笔触作唯一暖色
- **水墨晕开翻页**：几滴墨先后落下、先快后慢地扩散，墨丝边缘，新的一页从墨心里显出；翻页时机按内容计算，字读完才翻
- **镜头模板**：封面、人物身后大字、大字撕纸、竖排诗句、山水长卷、路线图、词条撕纸卡片、落款与印章、结尾圆窗
- **口播 + 成片素材**：素材挂轴、提示词信笺逐字书写、素材全屏 + 主播圆形头像 + 右上竖排题款
- **旁白音频也能做**：无人物的纸面版式（3:4 / 9:16 / 16:9 自适应），可用一张水墨画作首页淡底
- **音效**：古琴般的五声音阶拨弦、磬、水滴、风声、毛笔、撕纸、盖印

**文物纪录片 · documentary** · 深青铜色舞台 + 金色

- **流程**：精简文案（一句旁白一个镜头）→ Wikimedia Commons 找图 → rembg 抠出文物 → 分镜确认表（确认后才渲染）→ MiniMax 逐句配音 → 逐帧渲染 → Mixkit 实录音效 + 可选配乐
- **画面**：抠出的文物悬浮在舞台上，金色轮廓光、顶光扫亮、轻微 3D 转动；场景照片做成金边倾斜卡片；磨砂玻璃标签 / 数据卡、金色引线与脉冲光点、旋转刻度环、HUD 四角框、天光与浮尘
- **文字**：金属质感片名带高光扫过；大字逐字打在文物背后（打字机 + 闪烁光标）；字幕永远单行，长句按标点切分
- **声音**：实录音效按画面动作对齐；配乐按「不抢解说」打分挑选，自动削人声频段并在旁白时压低
- **3:4**：`--ratio 3x4` 把内容区缩小居中、上下留白，不硬裁

## 用法

装好后在 Claude Code 里直接说，提示词决定风格：

| 风格 | 怎么说 | 输入 |
|---|---|---|
| NEON LAB（默认） | 帮我把 `口播.mp4` 剪辑一下，加字幕和特效，用 xingor 风格 | 口播视频 |
| 诗墨国风 | 用**水墨诗词**风格剪辑 `口播.mp4` / 用水墨诗词风格把 `旁白.mp3` 做成 3:4 视频 | 口播视频或旁白音频 |
| 文物纪录片 | 做一个关于三星堆的**文物纪录片**（也可以说 纪录片 / 文物 / 历史 / documentary） | 主题或一篇文案 |

Claude 会按 [SKILL.md](SKILL.md) 的流程自动完成：环境安装 → 分析 → 修字幕 → 挑钩子 → 规划镜头 → 静帧检查 → 渲染成片。可以接着说「卡片再大一点」「过渡别用水墨」之类，逐版修改。

各风格的规范与模板说明：[references/style-guide.md](references/style-guide.md)（NEON LAB）、[references/poetry-ink.md](references/poetry-ink.md)（诗墨国风）、[references/documentary.md](references/documentary.md)（文物纪录片）。

## 安装

```bash
git clone https://github.com/imokya/xingor-video-skill.git ~/.claude/skills/xingor-video-skill
```

## 手动使用

```bash
# 1. 一次性环境（venv、ffmpeg、抠像模型）
bash scripts/setup.sh work
cd work

# 2. 分析视频：标准化、转写、找停顿、逐帧抠像、检测人物位置
.venv/bin/python ../scripts/analyze.py ../口播.mp4
#    只有旁白音频 / 其他画幅：
#    .venv/bin/python ../scripts/analyze.py ../旁白.mp3 --size 1080x1440

# 3. 挑钩子片段（打分 + 建议的 HOOK 配置）
.venv/bin/python ../scripts/hook.py

# 4. 修改 captions.txt（一行对应一段，用 | 切分字幕），
#    参照 references/example_project/ 里的示例写 scenes.py
#    （诗墨国风：scenes.py 里写 THEME = 'poetry-ink'）

# 5. 静帧预览（秒为单位，h 开头表示钩子内的时间）→ 完整渲染
.venv/bin/python ../scripts/render.py test h1.0 3.5 12 30
.venv/bin/python ../scripts/render.py full ../成片_v1.mp4 --bgm music.mp3
```

文物纪录片走 `scripts/doc/` 下的独立流程，见 [references/documentary.md](references/documentary.md)。

## 目录

```
SKILL.md                         Skill 主说明（工作流）
references/style-guide.md        NEON LAB 风格规范 + 镜头模板选择表
references/poetry-ink.md         诗墨国风风格规范 + 模板选择表 + 调性说明
references/documentary.md        文物纪录片流程与规范
references/example_project/      示例：scenes.py（NEON）、scenes_poetry_ink*.py（诗墨：口播 / 旁白 3:4 / 画作首页 16:9 / 口播+成片素材）
references/example_documentary/  示例：scenes_sanxingdui.py（《三星堆》27 个镜头，2 分 53 秒）
scripts/setup.sh                 环境安装
scripts/analyze.py               视频分析（ASR / 停顿 / 抠像 / 人物定位）
scripts/hook.py                  钩子候选片段打分与建议
scripts/components.py            18 个可复用镜头模板（含口播小窗）
scripts/ink.py                   诗墨国风：纸墨纹理、水墨晕开、撕纸、印章、山水、模板与音效
scripts/fx.py                    绘图与缓动工具（skia）
scripts/render.py                合成渲染 + 音频（钩子、剪停顿、音效、BGM、主题切换）
scripts/montage.py               静帧拼图
scripts/doc/                     文物纪录片：doc_core.py（渲染核心）、doc_fetch.py、doc_cutout.py、doc_tts.py、doc_storyboard.py、doc_audio.py
```

## 依赖

- Python 3.11、torch、faster-whisper、skia-python、imageio-ffmpeg（`setup.sh` 自动安装）
- macOS 字体：苹方、兰亭黑、Avenir Next Condensed、DIN Condensed、Menlo；诗墨国风另用宋体-简、楷体-简、行楷-简
  （其他系统请修改 `scripts/fx.py` 里的 `FAM` 字体映射）
- 文物纪录片：`pip install pillow numpy imageio-ffmpeg "rembg[cpu]"`；配音需要 `.env`（`MINIMAX_API_KEY`、`MINIMAX_GROUP_ID`、`MINIMAX_REGION`）
- 渲染速度：M1 Pro 约 13 fps，90 秒视频约 3 分钟
