import asyncio
import functools
from config import load_config

# 读取全局配置
_config = load_config()
_retry_conf = _config.get("retry", {})
DEFAULT_RETRIES = _retry_conf.get("max_attempts", 3)
BACKOFF_FACTOR = _retry_conf.get("backoff_factor", 1)


def retry_on_exception(exc_types, max_retries: int = None, backoff_factor: float = None):
    """
    异步函数重试装饰器，根据配置或指定参数进行重试和指数级回退。
    :param exc_types: 要捕获并重试的异常类型元组
    :param max_retries: 最大重试次数（默认为配置中的 DEFAULT_RETRIES）
    :param backoff_factor: 回退基数（秒），每次重试间隔 = backoff_factor * attempt
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = max_retries or DEFAULT_RETRIES
            backoff = backoff_factor or BACKOFF_FACTOR
            last_exc = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exc_types as e:
                    last_exc = e
                    if attempt < retries:
                        delay = backoff * attempt
                        # 可根据需要记录日志：logger.warning(...)
                        await asyncio.sleep(delay)
                        continue
            # 最后一次重试仍然失败，抛出最后捕获到的异常
            raise last_exc
        return wrapper
    return decorator