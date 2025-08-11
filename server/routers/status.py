import psutil
from fastapi import APIRouter

from server.schemas.status import CpuFreq, Memory, StatusSchema

router = APIRouter(prefix='/status', tags=['Status'])


@router.get('', response_model=StatusSchema, summary='Retorna informações de status do sistema')
async def get_status():
    """Endpoint que retorna informações sobre uso de CPU e memória do sistema."""
    number_of_cores = psutil.cpu_count()
    cpu_frequency = CpuFreq(**psutil.cpu_freq()._asdict())
    cpu_percent = psutil.cpu_percent()
    memory = Memory(**psutil.virtual_memory()._asdict())

    cpu_frequency_percpu = psutil.cpu_freq(percpu=True)
    cpu_percent_percpu = psutil.cpu_percent(percpu=True)

    status_per_core = []

    for cpu_frequency_item, cpu_percent_item in zip(cpu_frequency_percpu, cpu_percent_percpu):
        status_per_core.append({
            'cpu_frequency': CpuFreq(**cpu_frequency_item._asdict()),
            'cpu_percent': cpu_percent_item,
        })

    data = {
        'number_of_cores': number_of_cores,
        'cpu_frequency': cpu_frequency,
        'cpu_percent': cpu_percent,
        'status_per_core': status_per_core,
        'memory': memory,
    }

    return data
