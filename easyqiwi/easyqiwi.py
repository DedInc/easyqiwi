import asyncio
import base64
import httpx
import datetime
import json
from httpx_socks import AsyncProxyTransport
from urllib.parse import urlencode

class AuthException(Exception):
    pass

class RecaptchaException(Exception):
    pass

class NonAuthCoreException(Exception):
    pass

class ProxyConnectionException(Exception):
    pass

async def setup_proxy(proxy_type, proxy_ip, proxy_port, username=None, password=None):
    proxy_type = proxy_type.lower()

    transport = None
    proxy_mounts = None

    if username is None or password is None:
        proxy_url = f'{proxy_type}://{proxy_ip}:{proxy_port}'
    else:
        proxy_url = f'{proxy_type}://{username}:{password}@{proxy_ip}:{proxy_port}'

    if 'socks' in proxy_type:
        transport = AsyncProxyTransport.from_url(proxy_url)
    else:
        proxy_mounts = {
            'http://': httpx.AsyncHTTPTransport(proxy=proxy_url),
            'https://': httpx.AsyncHTTPTransport(proxy=proxy_url)
        }

    return proxy_mounts, transport

class EasyQiwiAuthCore:
    def __init__(self, phone, password, proxy_tuple=(None, None)):
        self.phone = phone
        self.password = password
        self.base_url = 'https://qiwi.com'
        self.token_head = None
        self.refresh_token = None
        self.expires_in = None
        self.api_token = None
        proxy_mounts, transport = proxy_tuple
        self.session = httpx.AsyncClient(http2=True, mounts=proxy_mounts, transport=transport, timeout=10, headers={
            'User-Agent': 'okhttp/4.9.1',
            'client-software': 'WEB v4.127.2'
        })
        self.lock = asyncio.Lock()

    def _set_auth_data_and_cookies(self, data, response):
        auth_data = {
            "expires_in": data['expires_in'],
            "token_type": data['token_type'],
            "access_token": data['access_token'],
            "refresh_token": data['refresh_token'],
            "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "client_id": "web-qw"
        }

        self.cookies = []
        for name, value in response.cookies.items():
            self.cookies.append({'name': name, 'value': value, 'domain': '.qiwi.com'})

        self.auth_data = json.dumps(auth_data).replace(' ', '')
        self.token_head = data['access_token']
        self.refresh_token = data['refresh_token']
        self.expires_in = int(data['expires_in']) - 300


    async def _authenticate(self, recaptcha):
        response = await self.session.post(
            f'{self.base_url}/oauth/token', 
            data={'grant_type': 'anonymous', 'client_id': 'anonymous'}
        )
        data = response.json()
        anon_token = data['access_token']
        response_data = {
                'token_type': 'headtail',
                'grant_type': 'password',
                'client_id': 'web-qw',
                'client_secret': 'P0CGsaulvHy9',
                'anonymous_token_head': anon_token,
                'username': self.phone,
                'password': self.password
        }

        if recaptcha is not None:
            response_data.update({'recaptcha': recaptcha})

        response = await self.session.post(
            f'{self.base_url}/oauth/token',
            data=response_data
        )

        data = response.json()

        if 'error' in data:            
            if data['error'] == 'invalid_recaptcha':
                raise RecaptchaException(f'ReCaptcha Error! Call with recaptcha response: easy_authcore.auth(recaptcha=\'response\')')
            else:
                raise AuthException(str(data))
        try:
            self._set_auth_data_and_cookies(data, response)
            await self._fetch_api_token()
        except httpx.ProxyError as proxy_error:
            raise ProxyConnectionException(f"Failed to connect to the proxy: {proxy_error}") from proxy_error
        except httpx.HTTPStatusError as http_status_error:
            raise ProxyConnectionException(f"HTTP status error while authenticating: {http_status_error}") from http_status_error
        except httpx.RequestError as request_error:
            raise ProxyConnectionException(f"Request failed: {request_error}") from request_error
        except KeyError as key_error:
            raise AuthException('Authorization unknown error!') from key_error

    async def _fetch_api_token(self):
        api_key = base64.b64encode(f'web-qw:{self.token_head}'.encode()).decode()
        self.session.headers.update({'Authorization':  f'TokenHeadV2 {api_key}'})


    async def _update_token(self):
        while True:
            await asyncio.sleep(self.expires_in)
            async with self.lock:
                response = await self.session.post(
                    f'{self.base_url}/oauth/token', 
                    data={
                        'token_type': 'headtail',
                        'grant_type': 'refresh_token',
                        'client_id': 'web-qw',
                        'client_secret': 'P0CGsaulvHy9',
                        'token_head': self.token_head,
                        'refresh_token': self.refresh_token,
                    }
                )
                data = response.json()
                self._set_auth_data_and_cookies(data, response)
                await self._fetch_api_token()


    async def auth(self, recaptcha=None):
        await self._authenticate(recaptcha)
        asyncio.create_task(self._update_token())

    async def get_phone(self):
        return self.phone

    async def close(self):
        await self.session.aclose()

class EasyQiwiAPI:
    def __init__(self, auth_core):
        if type(auth_core) is EasyQiwiAuthCore:
            self.auth_core = auth_core
            self.base_url = 'https://edge.qiwi.com'
        else:
            raise NonAuthCoreException('It is not a EasyQiwiAuthCore instance!')

    async def get_current_profile(self):
        response = await self.auth_core.session.get(f'{self.base_url}/person-profile/v2/profile/current')        
        return response.json()

    async def get_sources(self, person_id):
        response = await self.auth_core.session.get(f'{self.base_url}/funding-sources/v2/persons/{person_id}/accounts')
        return response.json()

    async def get_identification(self, person_id):
        response = await self.auth_core.session.get(f'{self.base_url}/identification/v4/persons/{person_id}/identifications')
        return response.json()

    async def get_checkouts(self, status=None):
        req_url = f'{self.base_url}/checkout-api/api/bill/count'

        if status is not None:
            req_url += f'?statuses={status}'

        response = await self.auth_core.session.get(req_url)
        return response.json()

    async def get_cards(self):
        response = await self.auth_core.session.get(f'{self.base_url}/cards/v1/cards')
        return response.json()

    async def get_payments(self, person_id, rows=5, next_txn_id=None, next_txn_date=None):
        base_params = {
            'rows': rows
        }

        if next_txn_id is not None and next_txn_date is not None:
            extra_params = {
                'nextTxnId': next_txn_id,
                'nextTxnDate': next_txn_date
            }

            base_params.update(extra_params)

        encoded_params = urlencode(base_params)
        req_url = f'{self.base_url}/payment-history/v2/persons/{person_id}/payments?{encoded_params}'

        response = await self.auth_core.session.get(req_url)        
        return response.json()

    async def get_total_payments(self, person_id, start_date, end_date):
        base_params = {
            'startDate': start_date,
            'endDate': end_date
        }

        encoded_params = urlencode(base_params)
        req_url = f'{self.base_url}/payment-history/v2/persons/{person_id}/payments/total?{encoded_params}'

        response = await self.auth_core.session.get(req_url)
        return response.json()

    async def get_transactions(self, transaction_id, transaction_type=None):
        req_url = f'{self.base_url}/payment-history/v2/transactions/{transaction_id}'

        if transaction_type is not None:
            req_url += f'?type={transaction_type}'

        response = await self.auth_core.session.get(req_url)
        return response.json()

    async def generate_p2p_public(self):
        response = await self.auth_core.session.post(f'{self.base_url}/widgets-api/api/p2p/protected/generate-public-key')
        return response.json()

    async def create_invoice(self, p2p_key, widget_code, price, comment='', currency='rub'):
        json_data = {
            'amount': price,
            'currency': currency,
            'extras': [{
                'code': "themeCode",
                'value': widget_code
            }, {
                'code': 'apiClient',
                'value': 'p2p-admin'
            }, {
                'code': 'apiClientVersion',
                'value': '0.17.0'
            }, {
                "code": 'paySourcesFilter',
                "value": 'card,qw,mobile'
            }],

            'comment': comment,
            'customers': [],
            'public_key': p2p_key
        }

        response = await self.auth_core.session.post(f'{self.base_url}/checkout-api/invoice/create', json=json_data)        
        return response.json()