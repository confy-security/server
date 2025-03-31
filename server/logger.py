import logging
import sys
from logging.config import dictConfig

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'default',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'app.log',
            'maxBytes': 1_000_000,
            'backupCount': 3,
            'encoding': 'utf-8',
            'formatter': 'default',
        },
    },
    'loggers': {
        'app': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
    },
}

dictConfig(LOGGING_CONFIG)

# Criar um logger para a aplicação
logger = logging.getLogger('app')
