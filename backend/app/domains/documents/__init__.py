"""M5 文档子能力：版本、哈希、diff、回滚。

M5 bids 域在 Word 生成/版本管理/下载/比较/回滚的子能力。所有服务由 bids 域编排，
documents 不直接挂载 HTTP 路由、不依赖 M4 端口；M5 业务在持久化前用
``DocumentStore`` 维护内存状态，供测试与 Demo 使用。
"""
