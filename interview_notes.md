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