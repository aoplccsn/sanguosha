# T19 release report — BLOCKED / NOT RELEASED

日期：2026-10-07。T19未完成，没有签发RC，也没有部署。

- 基线：HEAD 94facbcfd144bf519da4dc9a99556f124777533e，包含49f0bb0；开始时已跟踪文件干净，原有untracked美术和日志全部保留。
- 分支：t19-overpowered-generals。
- roster仍为103，108验收未达到。五将未注册；神司马仍是T18A.11旧技能，未声称完成替换。
- 六将技能、AI、Projection、reconnect、Web/PySide及Worker接入：未实施，受规则锁定前置条件阻塞。详见rules_lock.md。
- 已准备集中抽样模块src/sanguosha/general_draft.py：超标位概率0.25；太史慈/孙策/现有司马ID/郭嘉/荀彧权重10/8/7/6/4；最多一个超标候选；按已占用排除、去重及注入RNG确定性抽取。神鲁肃不在超标名单。**尚未接入Pregame/Room，当前线上选将未变化。** 四名新增ID采用mobile_god_*准备命名。
- 化身：当前实现未改动，91目标未达到。
- 动态：找到工作区dynamic_portrait_sources下神鲁肃、神太史慈、神孙策、神荀彧master；按T15/T18编码参数准备detail 720x1280 CRF20、panel 360x640 CRF18及首帧PNG/WebP。H264/yuv420p、无音轨、faststart、比例与时长、原master SHA256校验。结果为候选资产，未接入生产manifest或UI。
- 神郭嘉god_guojia_idle.mp4未找到；是允许静态fallback的非阻塞项。未生成任何新美术。既有神司马视频及master未修改。
- 资源脚本：scripts/prepare_t19_portraits.py。状态及hash：portrait_preparation.json。候选资产：prepared_portraits/。
- 必要抽样测试：tests/test_t19_draft.py，14 PASS（概率边界、所有权重边界、seed复现、去重、占用排除、最多一名、鲁肃普通池和超标池空时回退）。
- 六将targeted及最终综合验收均未运行；AI40场未运行。没有用基线测试冒充T19通过。
- GitHub：部分进度已提交并成功推送origin/t19-overpowered-generals；这不是完成checkpoint。
- GHCR：未构建T19 image。Sealos：未更新。公网T19 health/smoke：未执行。

唯一阻塞：无法完成用户要求的“当前移动版正式服规则”锁定与可靠交叉核对。官网详情滞后/矛盾，移动版百科被HTTP567拦截，最新解析正文不可读取。已经尝试搜索、公开实现核对及正常浏览器访问。

最短解锁动作：提供一份可读取的当前正式服完整技能资料（文本或截图），重点覆盖rules_lock.md末段未确认细则；不需要重复基线或重新准备master。
