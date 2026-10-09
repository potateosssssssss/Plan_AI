import os
from dotenv import load_dotenv


# 加载 .env 文件中的环境变量
load_dotenv()


class Settings:
    """应用配置类，从环境变量中读取配置项并赋予默认值。"""

    def __init__(self):
        # 数据库连接地址
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            default="sqlite:///./planai.db",
        )
        # JWT 加密密钥
        self.SECRET_KEY: str = os.getenv(
            "SECRET_KEY",
            default="your-secret-key-change-me",
        )
        # OpenAI API 密钥
        self.OPENAI_API_KEY: str = os.getenv(
            "OPENAI_API_KEY",
            default="",
        )
        # OpenAI 模型名称
        self.OPENAI_MODEL: str = os.getenv(
            "OPENAI_MODEL",
            default="gpt-3.5-turbo",
        )


# 全局单例配置对象，方便其他模块直接导入使用
settings = Settings()
