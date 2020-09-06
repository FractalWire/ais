REDIS_CONF = {
    'db': 1,
}

# Update interval to store the latest position received
POSTGRES_WINDOW = int(2*60)  # in seconds

# Update interval to fetch messages from aishub api
AISHUBAPI_WINDOW = 1*60  # in seconds

# Redis position keys ttl
POSITION_TTL = 6*60*60  # in seconds

# Redis aismessage keys ttl must be: window < ttl < 2*window
AISMESSAGE_TTL = int(1.3*POSTGRES_WINDOW)

# If set to False, shipinfos history won't be saved
KEEP_SHIPINFOS_HISTORY = False
