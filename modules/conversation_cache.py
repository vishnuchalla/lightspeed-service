import redis
import threading
from tools.ols_logger import OLSLogger

class RedisCache:
    _instance = None
    _lock = threading.Lock()
    logger = None

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(RedisCache, cls).__new__(cls)
                # Initialize Redis client and logger
                cls._instance.initialize_redis(args, kwargs)
        return cls._instance

    def initialize_redis(self, *args, **kwargs):
        """Initialize the Redis client and logger."""
        self.redis_client = redis.StrictRedis(
            host="redis-master.ols.svc",
            port=6379,
            decode_responses=True,
        )
        # Set custom configuration parameters
        maxmemory = kwargs.get("maxmemory", "500mb")
        maxmemory_policy = kwargs.get("maxmemory_policy", "allkeys-lfu")
        self.redis_client.config_set("maxmemory", maxmemory)
        self.redis_client.config_set("maxmemory-policy", maxmemory_policy)

        # Configure the logger for the class
        self.logger = OLSLogger("conversational_cache").logger

    def get(self, key):
        """Get the value associated with the given key."""
        return self.redis_client.get(key)

    def put(self, key, value):
        """Set the value associated with the given key."""
        oldValue = self.get(key)
        with self._lock:
            if oldValue:
                self.redis_client.set(key, oldValue+"\n"+value)
            else:
                self.redis_client.set(key, value)
    
    def stats(self):
        # TODO To publish these metrics to our monitoring stack
        """Get stats on cache performance"""
        info_output = self.redis_client.info()
        # Extract relevant metrics
        hits = info_output['keyspace_hits']
        misses = info_output['keyspace_misses']

        # Use the logger to output metrics
        self.logger.info(f"Cache Hits: {hits}")
        self.logger.info(f"Cache Misses: {misses}")