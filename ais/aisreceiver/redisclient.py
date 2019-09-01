import redis

from ais import settings
from . import app_settings

redis_conf = {**settings.REDIS_CONF, **app_settings.REDIS_CONF}
redis_client = redis.Redis(**redis_conf)
pipeline_client = redis_client.pipeline()
