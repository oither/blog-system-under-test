# Day 1 - 环境搭建 + 用户认证模块

## 遇到的问题 & 解决方案

### 问题1: SQLAlchemy 版本兼容性问题
- **现象**: 首次执行 `uvicorn app.main:app --reload` 时报错，DeclarativeBase 等 2.0 新特性无法识别
- **原因**: requirements.txt 中指定的 SQLAlchemy==2.0.23 与当前 Python 环境存在兼容性问题
- **解决**: 升级至 SQLAlchemy==2.0.52 后正常运行
- **收获**: 依赖锁定版本号很重要，但也要关注小版本间的兼容性差异；遇到框架报错时优先检查版本匹配

### 问题2: Login 接口从查询参数改为 JSON Body
- **现象**: 初始实现使用查询参数传递用户名密码，后续改为 JSON Body 时花费额外时间调试
- **原因**: 需要新增 LoginRequest Pydantic Schema，同时修改路由函数签名和请求体解析方式
- **解决**: 在 schemas.py 中添加 LoginRequest 模型，路由函数参数改为接收该模型实例
- **收获**: JSON Body 比查询参数更适合传递敏感信息（不会出现在 URL/日志中），也更符合 RESTful 规范，且便于后续自动化测试构造请求数据

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 密码加密 | passlib[bcrypt] | bcrypt 自带 salt、计算成本可调、抗彩虹表攻击；不选 hashlib/md5 |
| Token 存储字段 | username (sub) | 便于直接从 Token 反查用户，避免额外 ID→username 映射 |
| Login 请求格式 | JSON Body | 敏感信息不入 URL；与注册接口风格统一；自动化测试更易构造 |
| 数据库 | SQLite | 零配置、单文件、适合测试靶场；并发瓶颈恰好可作为性能测试素材 |

## 面试可讲的点

1. **密码安全存储全流程**: 明文 → bcrypt hash(自动加salt) → 存入 hashed_password 字段 → 登录时 verify 比对
2. **FastAPI Depends 依赖注入**: get_db() 通过 yield 管理会话生命周期，确保请求结束自动 close；get_current_user 链式依赖实现鉴权解耦
3. **JWT 设计考量**: sub 存 username 而非 ID 的权衡；Token 过期时间设置；为什么不用 Refresh Token（当前阶段简化，可讨论扩展方案）
4. **Pydantic v2 适配**: from_attributes=True 替代旧版 orm_mode；model_dump(exclude_unset=True) 实现部分更新

---

# Day 2 - 文章 CRUD + 权限控制 + Swagger 鉴权集成

## 遇到的问题 & 解决方案

### 问题1: Swagger Authorize 登录报 422 Unprocessable Entity
- **现象**: 点击 Swagger UI 的 Authorize 按钮输入用户名密码后返回 422
- **原因**: `OAuth2PasswordBearer` 默认发送 `application/x-www-form-urlencoded` 表单格式，而 `/auth/login` 端点只接受 JSON Body（`LoginRequest` Pydantic 模型）
- **解决**: 新增 `/auth/login/form` 端点专门接收 `OAuth2PasswordRequestForm` 表单数据，供 Swagger 使用；原 JSON Body 端点保留给前端和自动化测试
- **收获**: Swagger 的 OAuth2 交互遵循固定协议，不能期望它适配自定义请求格式；双端点策略兼顾了开发体验（Swagger 调试）和工程规范（JSON API）

### 问题2: 新增 /login/form 端点后返回 404 Not Found
- **现象**: 表单端点代码已写好，但 Swagger 仍报 404
- **原因**: `main.py` 中未注册 auth router（`app.include_router(auth.router)` 缺失）
- **解决**: 在 main.py 中补上路由注册
- **收获**: FastAPI 多文件项目中，新建 router 后必须手动注册，否则静默失败；养成新增路由后立即访问 `/openapi.json` 确认路径的习惯

### 问题3: auth.py 拆分后的 ImportError
- **现象**: 将 auth.py 移入 routers/ 目录后启动报错 `cannot import name 'auth' from 'app.routers'`
- **原因**: auth.py 原本在 app/ 根目录作为工具模块，移入 routers/ 后相对导入层级变化，且 main.py 导入路径未同步更新
- **解决**: 最终采用职责拆分方案——`app/auth.py` 保留纯工具函数（hash、JWT、get_current_user），`app/routers/auth.py` 只放 API 端点；同时修正跨层级的相对导入（`.` → `..`）
- **收获**: 当文件从"工具模块"演变为"工具+路由混合体"时，应及时拆分以维持单一职责；移动文件后务必检查所有相对导入路径

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Swagger 鉴权兼容 | 双端点（JSON + Form） | JSON Body 供生产/测试使用，Form 端点专供 Swagger；互不干扰 |
| 文章归属校验 | 先查文章再比对 user_id | 避免 N+1 查询；404 和 403 语义明确区分（不存在 vs 无权限） |
| 部分更新实现 | model_dump(exclude_unset=True) | 只更新请求中传入的字段，未传字段保持原值；符合 PATCH 语义 |
| auth 模块拆分 | 工具层 + 路由层分离 | app/auth.py 被多个 router 依赖，不应耦合具体端点逻辑 |

## 面试可讲的点

1. **Swagger OAuth2 协议适配**: 理解 `OAuth2PasswordBearer` 底层发送的是表单而非 JSON，通过双端点策略在不破坏 API 规范的前提下解决调试体验问题
2. **权限控制三层模型**: 401（未认证）→ 404（资源不存在）→ 403（无权操作）的递进校验顺序，以及为什么 404 要优先于 403（防止信息泄露）
3. **FastAPI 多文件项目组织**: 从单文件到 routers 分包的演进过程；工具模块与业务路由的职责边界；相对导入的层级规则
4. **排错方法论**: 404 → 检查 openapi.json 确认路径是否注册；ImportError → 检查文件位置与相对导入层级；422 → 检查请求格式与 Schema 匹配。形成"现象→定位→验证"的闭环
5. **Day 2 验收清单设计思路**: 12 项测试覆盖正常流程（CRUD）、边界条件（删除后查询）、权限隔离（bob vs alice）、安全兜底（未认证访问），体现测试分层意识

# Day 3 - 评论接口 + 极简前端

## 遇到的问题 & 解决方案

### 问题1: 评论接口缺少删除端点
- **现象**: Day 3 验收时发现 comments 路由只有 POST 和 GET，无法完成"删除自己的评论 204"和"删除别人的评论 403"测试
- **原因**: 初始实现只覆盖了评论的创建和查询，删除功能遗漏
- **解决**: 补充 DELETE /comments/{comment_id} 端点，复用文章的权限校验模式（先查资源是否存在 → 再校验归属权 → 执行删除）
- **收获**: 写代码前先列完整验收清单，按清单逐项实现，避免"凭感觉觉得做完了"；CRUD 四个操作要作为整体规划，不能只想到 C 和 R

### 问题2: 评论删除路由设计——平铺还是嵌套
- **现象**: 纠结删除评论应该用 `/articles/{aid}/comments/{cid}` 还是 `/comments/{cid}`
- **原因**: 创建评论时必须指定所属文章，但删除时 comment_id 已经能唯一定位资源
- **解决**: 创建用嵌套路径 `/articles/{aid}/comments`（需要上下文），删除用平铺路径 `/comments/{cid}`（资源独立可寻址）
- **收获**: RESTful 设计中，嵌套表达"从属关系的创建"，平铺表达"已存在资源的独立操作"；不要为了路径对称而强行嵌套

### 问题3: 前端 Token 管理与页面刷新
- **现象**: 登录成功后发文正常，但刷新页面后状态丢失
- **原因**: Token 只存在 JS 变量中，页面刷新后变量清空
- **解决**: 登录成功后将 Token 存入 localStorage，页面加载时先读取 localStorage 恢复登录状态；每次 fetch 请求从 localStorage 取 Token 附加到 Authorization 头
- **收获**: 前端状态持久化是基本功；localStorage vs sessionStorage vs Cookie 的选择取决于安全需求和生命周期要求

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端技术栈 | 纯 HTML + 原生 fetch | 零依赖、零构建、聚焦后端学习；不引入 React/Vue 增加复杂度 |
| 前端路由 | 后端直接返回 HTML（/ui） | 无需前端路由库；单页够用；模板渲染由 FastAPI 完成 |
| 评论删除路径 | /comments/{id} 平铺 | 资源独立可寻址；避免冗余参数；前端调用更简洁 |
| Token 前端存储 | localStorage | 刷新不丢失；实现简单；靶场项目安全要求低 |
| CORS 策略 | allow_origins=["*"] | 本地开发阶段全放行；生产环境需收紧为白名单 |

## 面试可讲的点

1. **评论系统数据模型**: Comment 表通过 article_id 外键关联文章、author_id 外键关联用户；级联删除策略（删文章时评论是否跟着删）的权衡
2. **RESTful 路径设计原则**: 嵌套路径表达创建时的从属上下文（POST /articles/1/comments），平铺路径表达已存在资源的独立操作（DELETE /comments/5）；面试中常被问"为什么这样设计"
3. **前后端分离的最小实现**: 后端提供 JSON API + 静态页面；前端用 fetch 调 API；Token 通过 localStorage 持久化；这其实就是真实项目前后端交互的缩影
4. **权限校验的一致性**: 文章和评论的权限逻辑完全同构——404（不存在）→ 403（不是你的）→ 204（删除成功）；抽象出通用的"资源归属校验"模式
5. **浏览器 DevTools 调试能力**: Console 看 JS 报错、Network 看请求/响应/状态码/请求头；这是前后端联调的第一技能，面试中体现工程素养