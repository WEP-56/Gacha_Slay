# PyQt5 离线放置抽卡爬塔游戏（原型）
# 烂尾了没空写o(╥﹏╥)o
> 使用 Python + PyQt5 构建的离线放置抽卡 + 爬塔原型。首版专注本地单机与核心循环打磨，后续可扩展到多人在线（WebSocket/HTTP）。

## 核心玩法循环
- **挂机（离线与在线）**：周期性产出钻石与养成材料（离线通过时间差结算）。
- **抽卡**：消耗钻石获得卡牌（稀有度/概率保底/卡池轮换）。
- **养成**：卡牌升级、升星、装备/技能强化、阵容搭配（职业/羁绊/站位）。
- **爬塔战斗**：对撞式快节奏回合/帧驱动，胜利提高挂机效率并掉落资源。
- **循环**：挂机 → 抽卡 → 养成 → 推塔 → 提升挂机 → 再循环。

---

## 可行性分析（重点：PyQt5 卡牌对撞动画）

- **引擎选择**：
  - 采用 `QGraphicsView/QGraphicsScene` 作为2D渲染与场景管理核心；卡牌为 `QGraphicsItem` 派生类。
  - 在 `QGraphicsView` 上启用 OpenGL 视口（`setViewport(QOpenGLWidget())`）获得可观性能提升。

- **动画与碰撞**：
  - 位移动画：`QPropertyAnimation` 绑定 `QGraphicsItem.pos`，配合 `QSequentialAnimationGroup`/`QParallelAnimationGroup` 组织进攻/受击/回位序列。
  - 旋转/缩放：同 `QPropertyAnimation` 绑定自定义 `rotation/scale` 属性或借助 `setRotation/setScale` 封装属性接口。
  - 碰撞检测：`QGraphicsItem.collidesWithItem(...)`；命中瞬间触发受击特效、飘字和抖屏（视图 `setTransform` 轻微抖动）。
  - 受击反馈：`QGraphicsColorizeEffect`/`QGraphicsOpacityEffect` 实现闪白、透明渐变；粒子用精灵图或 `QPainter` 轻量绘制。

- **表现节奏（对撞范式）**：
  - 攻击端卡牌从站位 A → 中线 → 敌方卡牌前沿（或相交点），命中后回位；防御端播放 `hit` 与 `damage number`。
  - Boss/技能：在命中前插入特写（scale up、zValue 提升），或全屏特效层（独立 `QGraphicsItem`）。

- **性能策略**：
  - 视口：`QOpenGLWidget` + `QGraphicsView::FullViewportUpdate`（或 MinimalViewportUpdate，视内容而定）。
  - Item 优化：`ItemIgnoresTransformations`（按需）、`setCacheMode(DeviceCoordinateCache)`、`setFlags(ItemClipsToShape)` 以减少过绘。
  - 资源：纹理打包（雪碧图）、`QPixmapCache`、懒加载；IO 与 AI 图片生成在 `QThread`，避免阻塞 GUI 线程。
  - Tick 驱动：`QTimer`（约 60 FPS）驱动战斗状态机，动画仍交由 `QPropertyAnimation`/Timeline，防止手写插值抖动。
  - 批量战斗/离线结算不渲染：仅模拟逻辑，极大降低 CPU/GPU 开销。

- **可扩展性**：
  - 首版单机，本地存档；后续多人在线可用 FastAPI + WebSocket 做战斗结果上报与排行榜，同步只传“决定性随机种子+结果”，客户端负责回放。

结论：在 PyQt5 下以 `QGraphicsView` 路线实现“卡牌对撞动画”完全可行；结合 OpenGL 视口与缓存策略可支撑移动端水平的 2D 表现与较高并发动画数量。首版建议控制同屏可见单位与特效复杂度，优先保障 60 FPS 稳定性。

---

## 技术栈与运行环境
- 语言：Python 3.10+
- 框架：PyQt5（Widgets、Graphics View Framework、QtConcurrent/Threading）
- 数据：SQLite（持久化）或 JSON（原型期）
- 资源：AI 生成图片（本地文件夹）

---

## 目录结构（建议）
```
project/
  assets/                   # 图片/图集/音效
  data/                     # 卡池/卡牌/关卡配置（json / db）
  game/
    ui/                     # 界面与窗口（主界面、抽卡、编队、战斗）
    core/                   # 核心逻辑（状态机、定时器、数值、掉落）
    battle/                 # 战斗层（场景、卡牌Item、动画器、特效）
    systems/                # 挂机、抽卡、养成、任务、背包
  scripts/                  # 资产处理、图集打包、小工具
  main.py                   # 程序入口
  README.md
```

---

## 关键系统设计草案
- **战斗（Battle）**
  - `BattleScene(QGraphicsScene)`: 管理地面、单位层、特效层、UI层。
  - `CardItem(QGraphicsItem)`: 渲染卡面/血条/状态；暴露 `attack()`, `hit()`, `die()`，内部使用动画组实现对撞与受击。
  - `EffectItem(QGraphicsItem)`: 受击闪白、数字飘字、粒子。
  - `BattleController`: 帧/回合同步、AI 决策、伤害结算、胜负判断。

- **挂机（Idle）**
  - 按服务器/本地时间戳差计算钻石和材料；封顶、收益曲线与增益来源（塔层、科技）。

- **抽卡（Gacha）**
  - 卡池配置、概率/保底、重复转化（碎片/币）。

- **养成（Progression）**
  - 升级（线性/分段曲线）、升星（卡碎片+材料）、羁绊/职业加成与站位策略。

- **存档（Save/Load）**
  - `save.json` 或 SQLite（多存档位、加密可选）。

---

## 数据与配置建议
- `cards.json`：id、名称、稀有度、职业、基础属性、技能、资源路径。
- `gacha_pools.json`：权重、保底规则、UP 配置、有效期。
- `stages.json`：爬塔层数、敌人编成、奖励曲线。
- `balance.json`：经验曲线、金币/材料消耗、挂机产出基准。

---

## 路线图（MVP → 扩展）
- v0.1（MVP）
  - 主界面 + 挂机计时与离线结算
  - 抽卡界面 + 简单概率与保底
  - 编队与基础属性
  - 对撞战斗（近战直线冲锋、受击特效、胜负判定）
  - 本地存档
- v0.2
  - 远程技能/群体技能、Buff/Debuff、暴击与格挡
  - 粒子系统与相机抖动、连击演出
  - 关卡/爬塔曲线与挂机收益联动
- v0.3
  - 图集管线、性能打磨（缓存/批渲染/资源池）、设置菜单（60/120FPS）
  - 皮肤与活动卡池、保底记录
- v0.4（在线雏形）
  - FastAPI + WebSocket 排行/结果上报
  - 仅上传随机种子与摘要，客户端本地回放

---

## 运行方式（占位，代码接入后补充）
```bash
pip install -r requirements.txt
python main.py
```

- 首次运行会在 `assets/` 下读取卡牌图片；无图时可用占位图。
- 若使用 SQLite，请在 `data/` 生成初始数据库或自动迁移。

---

## 性能与美术管线注意
- 使用 OpenGL 视口、缓存与雪碧图以减少过绘与状态切换。
- 资源体量控制：缩放到功耗友好尺寸（如 512px 卡面），压缩为 WebP/PNG。
- 异步加载与资源池：线程加载、主线程上屏，避免卡顿。

---

## 许可证
- 代码可自定义；AI 生成图需确认版权与商用条款，避免侵犯第三方权益。
