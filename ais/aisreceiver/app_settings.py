REDIS_CONF = {
    'db': 1,
}
# Redis position keys ttl
POSITION_EXPIRE_TTL = 6*60*60  # in seconds

# Update interval to store the latest position received
POSTGRES_UPDATE_WINDOW = 5*60  # in seconds

# Update interval to fetch messages from aishub api
AISHUBAPI_UPDATE_WINDOW = 5*60  # in seconds
