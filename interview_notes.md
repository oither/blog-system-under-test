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

### 问题2: 评论删除路由设计——平铺还是嵌套（决策后被推翻）
- **现象**: 纠结删除评论应该用 `/articles/{aid}/comments/{cid}` 还是 `/comments/{cid}`
- **原因**: 创建评论时必须指定所属文章，但删除时 comment_id 已经能唯一定位资源
- **解决**: 初版创建用嵌套、删除用平铺；Day 4 修复"跨文章删除评论"漏洞时改回嵌套 `DELETE /articles/{aid}/comments/{cid}`——路径中的 `article_id` 参与归属校验（`WHERE id=? AND article_id=?`），既防止拿错文章 ID 误删评论，也让 404 语义覆盖"该评论不属于这篇文章"
- **收获**: 平铺"资源独立可寻址"的前提是单个 ID 足以**安全**定位资源；当权限校验需要第二个 ID 参与时，嵌套才是正确选择。初版决策被后续测试推翻并修正，是正常且必要的过程

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
| 评论删除路径 | /articles/{aid}/comments/{cid} 嵌套（初版平铺，Day 4 改回） | article_id 参与归属校验，堵住跨文章删除漏洞；404 语义覆盖"评论不属于该文章" |
| Token 前端存储 | localStorage | 刷新不丢失；实现简单；靶场项目安全要求低 |

## 面试可讲的点

1. **评论系统数据模型**: Comment 表通过 article_id 外键关联文章、user_id 外键关联用户；级联删除策略（删文章时评论是否跟着删）的权衡
2. **RESTful 路径设计的修正案例**: 最初按"已存在资源独立可寻址"把删除评论设计为平铺路径，复核时发现它让 article_id 沦为摆设、存在跨文章删除风险，最终改回嵌套。面对"为什么这样设计"的追问，能讲清"初版理由 + 推翻理由"比坚持原方案更有说服力
3. **前后端分离的最小实现**: 后端提供 JSON API + 静态页面；前端用 fetch 调 API；Token 通过 localStorage 持久化；这其实就是真实项目前后端交互的缩影
4. **权限校验的一致性**: 文章和评论的权限逻辑完全同构——404（不存在）→ 403（不是你的）→ 204（删除成功）；抽象出通用的"资源归属校验"模式
5. **浏览器 DevTools 调试能力**: Console 看 JS 报错、Network 看请求/响应/状态码/请求头；这是前后端联调的第一技能，面试中体现工程素养

---

# Day 4 - 代码审查修复 + 安全收尾

## 遇到的问题 & 解决方案

### 问题1: 评论删除接口的 article_id 是摆设（跨资源删除）
- **现象**: 删除评论的 SQL 只按 comment_id 查询，路径里的 article_id 没参与过滤，拿别人的文章 ID 也能删评论，且文章不存在也不报 404
- **原因**: 初版按平铺路径实现，改回嵌套时查询条件没同步补上
- **解决**: 查询改为 WHERE id = comment_id AND article_id = article_id，归属不匹配统一返回 404
- **收获**: 路径参数必须参与业务逻辑，否则就是摆设；权限相关的 ID 要在 SQL 层校验，不能依赖调用方自觉

### 问题2: 注册重复邮箱返回 500
- **现象**: email 列有唯一约束，但注册只查重 username，重复邮箱在 commit 时抛 IntegrityError 变成 500
- **原因**: 把 DB 约束当成了接口校验
- **解决**: 查重改为 username OR email 一条查询，统一返回 400
- **收获**: 唯一约束是最后一道防线不是第一道；500 往往意味着"约束兜底"被穿透到了用户面前

### 问题3: is_active 字段建了但没人消费
- **现象**: 字段有、接口返回有，但登录和 get_current_user 都不判断，禁用用户照常拿 Token 照常访问
- **解决**: 三个入口统一补 403 校验——JSON 登录、Form 登录、get_current_user；其中 Form 登录是第一轮修复时漏掉的，说明多入口规则最容易漏
- **收获**: 同一条业务规则必须在所有入口一致落地，漏一个就是绕过通道

### 问题4: SECRET_KEY 硬编码 + .env 是摆设
- **现象**: 装了 python-dotenv 但全项目没有任何读取环境变量的代码，密钥写死在源码里
- **解决**: auth.py 通过 load_dotenv + os.getenv 读取 SECRET_KEY / ACCESS_TOKEN_EXPIRE_MINUTES，缺失时 raise RuntimeError 拒绝启动；.env.example 入库作模板，代码不读取的 DATABASE_URL 从模板中删除
- **收获**: 配置宁可在启动时炸掉，也不要带着默认值悄悄跑；fail-fast 的报错永远比线上被伪造 Token 便宜

## 其他修复
- 删除 users.py 中与 routers/auth.py 重复的 /auth/login 死代码
- UserCreate.email 改用 EmailStr（新增 email-validator 依赖）
- datetime.utcnow() → datetime.now(timezone.utc)（Python 3.12+ 已弃用）
- 前端文章渲染 innerHTML 拼接 → createElement + textContent（存储型 XSS）
- static/ 补 .gitkeep 解决 clone 后目录缺失；ER 图导出 er-diagram.png 入根目录

## 关键技术决策
| 决策 | 选择 | 理由 |
|------|------|------|
| 配置注入 | dotenv + 启动 fail-fast | SECRET_KEY 缺失就不启动，问题最早暴露 |
| 注册重复响应 | 统一 400，不区分撞了哪个字段 | 防止用户名/邮箱枚举攻击 |
| 前端 XSS 修复 | createElement + textContent | 零依赖，不破坏"零构建"原则 |
| 靶场留坑策略 | 修复越权类真漏洞，保留级联删除缺失、登录无速率限制 | 靶场需要已知缺陷供测试，修哪些留哪些本身是设计决策 |

## 面试可讲的点
1. **"路径参数摆设"漏洞的完整故事**: 接口看似规范，复查发现 article_id 从未进 SQL；修复它正是把删除路由从平铺改回嵌套的直接原因
2. **500 → IntegrityError 的排查路径**: 接口层校验与 DB 约束的双保险设计，前者要拦住 99% 的常规冲突
3. **多入口一致性**: JSON 登录、Form 登录、get_current_user 三处都要判 is_active，漏一处就是绕过通道——规则落地要做入口清单盘点
4. **fail-fast 配置 vs 默认值兜底**: os.getenv("SECRET_KEY", "dev") 看似友好，实为带默认密钥长期裸奔的隐患
5. **有意保留的"可测缺陷"**: 删文章不级联评论、登录无速率限制——靶场需要缺陷可测，修与留的取舍体现测试视角