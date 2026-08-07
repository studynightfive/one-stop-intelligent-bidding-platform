"""业务领域包；目录所有权见 PROJECT_MASTER_PROMPT.md 第 5 节。

M4 负责的领域：
- auth: 认证
- users: 用户管理
- files: 文件平台
- jobs: 异步任务
- notifications: 通知
- settings: 系统设置
- audit: 审计日志
- search: 全局搜索
"""

from app.domains.auth import User, AuthService, UserService

__all__ = [
    "User",
    "AuthService",
    "UserService",
]
