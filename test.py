import requests

r = requests.post('http://127.0.0.1:5000/api/genqr', json={
    'data': 'https://trblox.com',
    'filename': 'example_qr'
})