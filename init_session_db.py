"""单独初始化 AgentScope 会话存储所需的数据库表。"""

import asyncio

from agentscope.app.storage import AsyncSQLAlchemyStorage

from mcp_agent import database_url_from_env


async def main():
    # 与聊天入口共用数据库配置，不在初始化脚本中另存密码。
    database_url = database_url_from_env()
    # 只创建缺少的框架表；不创建数据库、账号，也不执行表结构迁移。
    storage = AsyncSQLAlchemyStorage(
        url=database_url,
        create_tables=True,
        auto_migrate=False,
    )
    # 进入作用域时连接数据库并建表，离开时关闭存储资源。
    async with storage:
        print("AgentScope 数据库表初始化完成，已有表不会重复创建。")


if __name__ == "__main__":
    # 单独运行脚本时才执行初始化，导入模块不会操作数据库。
    asyncio.run(main())
