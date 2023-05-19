import multiprocessing
import os

from dotenv import load_dotenv

load_dotenv()

max_requests = 1000
max_requests_jitter = 50
log_file = "-"
bind = "0.0.0.0:50505"

if not os.getenv("RUNNING_IN_PRODUCTION"):
    reload = True

workers = (multiprocessing.cpu_count() * 2) + 1
threads = workers
timeout = 120
