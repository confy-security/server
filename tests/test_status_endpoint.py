def test_get_status(mock_psutil, client):
    response = client.get('/status')
    assert response.status_code == 200

    data = response.json()

    # Campos principais
    assert data['number_of_cores'] == 4
    assert data['cpu_frequency'] == {'current': 3200.0, 'min': 800.0, 'max': 4200.0}
    assert data['cpu_percent'] == 55.0

    # Lista por core
    assert len(data['status_per_core']) == 4
    assert data['status_per_core'][0] == {
        'cpu_frequency': {'current': 3100.0, 'min': 800.0, 'max': 4200.0},
        'cpu_percent': 10.0,
    }
    assert data['status_per_core'][3]['cpu_frequency']['current'] == 3400.0

    # Memória
    assert data['memory']['total'] == 16_000_000_000
    assert data['memory']['active'] == 4_000_000_000
    assert data['memory']['slab'] == 150_000_000
