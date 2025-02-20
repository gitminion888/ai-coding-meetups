import os

workers = 4
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
timeout = 120 