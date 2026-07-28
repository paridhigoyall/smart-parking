import os
os.environ['API_BASE_URL'] = 'http://127.0.0.1:5000'
from lib import api_client
from lib.api_client import ApiError

try:
    areas = api_client.list_parking_areas()
    print('OK', areas)
except ApiError as e:
    print('ApiError', e.status_code, e.detail)
except Exception as ex:
    print('Exception', str(ex))
