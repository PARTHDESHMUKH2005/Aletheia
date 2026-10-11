import os

# Unit tests never call a live model; agent behaviour is tested in test_agent.py with a stub.
os.environ["USE_AGENT"] = "false"
