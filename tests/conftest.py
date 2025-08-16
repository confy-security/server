from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_psutil():
    with patch('server.routers.status.psutil') as mock_psutil:
        # cpu_count()
        mock_psutil.cpu_count.return_value = 4

        # cpu_freq() total
        mock_psutil.cpu_freq.side_effect = [
            MagicMock(_asdict=lambda: {'current': 3200.0, 'min': 800.0, 'max': 4200.0}),  # total
            [  # per core
                MagicMock(_asdict=lambda: {'current': 3100.0, 'min': 800.0, 'max': 4200.0}),
                MagicMock(_asdict=lambda: {'current': 3200.0, 'min': 800.0, 'max': 4200.0}),
                MagicMock(_asdict=lambda: {'current': 3300.0, 'min': 800.0, 'max': 4200.0}),
                MagicMock(_asdict=lambda: {'current': 3400.0, 'min': 800.0, 'max': 4200.0}),
            ],
        ]

        # cpu_percent() total e per core
        mock_psutil.cpu_percent.side_effect = [
            55.0,  # total
            [10.0, 20.0, 30.0, 40.0],  # per core
        ]

        # virtual_memory()
        mock_psutil.virtual_memory.return_value = MagicMock(
            _asdict=lambda: {
                'total': 16_000_000_000,
                'available': 8_000_000_000,
                'percent': 50.0,
                'used': 8_000_000_000,
                'free': 8_000_000_000,
                'active': 4_000_000_000,
                'inactive': 2_000_000_000,
                'buffers': 500_000_000,
                'cached': 1_000_000_000,
                'shared': 250_000_000,
                'slab': 150_000_000,
            }
        )

        yield mock_psutil
