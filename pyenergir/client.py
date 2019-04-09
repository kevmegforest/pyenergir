"""PyEnergir Client Module."""
import asyncio
import datetime
import json
import re

import aiohttp
from bs4 import BeautifulSoup
from dateutil import tz

from xlrd import open_workbook

# Always get the time using HydroQuebec Local Time
ENERGIR_TIMEZONE = tz.gettz('America/Montreal')

REQUESTS_TIMEOUT = 30

HOST = "https://cybercompte.energir.com"
HOME_URL = "{}/Cybercompte".format(HOST)
LOGIN_URL = "{}/Cybercompte/login.do".format(HOST)
MAIN_URL = ("{}/Cybercompte/accueil.do".format(HOST))
PROFILE_URL = ("{}/Cybercompte/accueil.do".format(HOST))
DATA_URL = "{}/Cybercompte/historiqueFacture.do".format(HOST)


class PyEnergirError(Exception):
    """Base PyHydroQuebec Error."""


class EnergirClient():
    """PyHydroQuebec HTTP Client."""

    def __init__(self, username, password, contract=None, timeout=REQUESTS_TIMEOUT,
                 session=None):
        """Initialize the client object."""
        self.username = username
        self.password = password
        self._contracts = []
        if contract is not None:
            self._contracts.append(contract)
        self._data = {}
        self._session = session
        self._timeout = timeout

    @asyncio.coroutine
    def _get_httpsession(self):
        """Set http session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

    @asyncio.coroutine
    def _get_login_page(self):
        """Go to the login page."""
        try:
            raw_res = yield from self._session.get(LOGIN_URL,
                                                   timeout=self._timeout)
        except OSError:
            raise PyEnergirError("Can not connect to login page")
        # Get login url
        content = yield from raw_res.text()
        soup = BeautifulSoup(content, 'html.parser')
        form_node = soup.find('form', {'id': 'target'})
        if form_node is None:
            raise PyEnergirError("No login form find")
        login_url = form_node.attrs.get('action')
        if login_url is None:
            raise PyEnergirError("Can not found login url")
        #add the home url to start of string received
        login_url = HOME_URL + "/" + login_url
        return login_url

    @asyncio.coroutine
    def _post_login_page(self, login_url):
        """Login to HydroQuebec website."""
        data = {"j_username": self.username,
                "j_password": self.password}

        try:
            raw_res = yield from self._session.post(login_url,
                                                    data=data,
                                                    timeout=self._timeout,
                                                    allow_redirects=False)
            if raw_res.status != 302:
                raise PyEnergirError("Login error: Bad HTTP status code. "
                                        "Please check your username/password.")
            if raw_res.headers.get('Location') != PROFILE_URL:
                raise PyEnergirError("Login error: Bad HTTP status code. "
                                        "Please check your username/password.")
        except OSError:
            raise PyEnergirError("Can not submit login form")

        return True

    @asyncio.coroutine
    def _get_contract(self):
        """Get id of consumption profile."""
        contracts = {}
        try:
            raw_res = yield from self._session.get(PROFILE_URL,
                                                   timeout=self._timeout)
        except OSError:
            raise PyEnergirError("Can not get profile page")
        # Parse html
        content = yield from raw_res.text()
        soup = BeautifulSoup(content, 'html.parser')
        # Search contracts
        for node in soup.find('table', id='tableComptes').tbody.find_all('tr'):
            #store contract id and link to specific page
            contract_id = node.attrs.get('id')[5:]
            #only add the contract wanted
            if not self._contracts or self._contracts[0] == contract_id:
                contracts[contract_id] = node.find('a', id=f"link-{contract_id}").attrs.get('href')

        return contracts


    def _get_data_from_excel(self, xls):
        """Interpret the data from the billing excel file (it takes binary data)
         and export the consumption data from it"""
        workbook = open_workbook(file_contents=xls)
        sheet = workbook.sheet_by_index(0)
        bills = []

        for idx_row in range(3, sheet.nrows):
            period_string = sheet.cell_value(idx_row, 2)
            gas_m3 = sheet.cell_value(idx_row, 5)

            search_obj = re.search("([0-9]{4}-[0-9]{2}-[0-9]{2}).*([0-9]{4}-[0-9]{2}-[0-9]{2})",
                                    period_string)
            period_start = search_obj.group(1)
            period_end = search_obj.group(2)

            #add everything to the bill array
            bills.append({
                "gas_m3": gas_m3,
                "period_start": period_start,
                "period_end": period_end
            })

        return bills
    @asyncio.coroutine
    def _get_excel_historic_data(self, contract_id):
        """Get all excel data for all bills"""
        try:
            raw_res = yield from self._session.get(f"{DATA_URL}?noCompte={contract_id}")
        except OSError:
            raise PyEnergirError("Can not get Historic Data page")
        # Parse html
        content = yield from raw_res.text()
        soup = BeautifulSoup(content, 'html.parser')
        form_node = soup.find('div', id='dynamicContent').form

        #Get all arguments for request
        args = []
        for node in form_node.find_all('input', {"class":'billCheckBox'}):
            args.append((node.attrs.get('name'), node.attrs.get('value')))

        args.append(("noCompte", contract_id))
        args.append(("method", "telechargerExcel"))
        raw_dld_res = yield from self._session.get(DATA_URL, params=args)
        xls = yield from raw_dld_res.read()
        return xls


    @asyncio.coroutine
    def _load_contract_page(self, contract_url):
        """Load the profile page of a specific contract when we have multiple contracts."""
        try:
            yield from self._session.get(contract_url,
                                         timeout=self._timeout)
        except OSError:
            raise PyEnergirError("Can not get profile page for a "
                                     "specific contract")

    @asyncio.coroutine
    def fetch_data(self):
        """Get the latest data from HydroQuebec."""
        # Get http session
        yield from self._get_httpsession()
        # Get login page
        login_url = yield from self._get_login_page()
        # Post login page
        yield from self._post_login_page(login_url)
        # Get contracts
        contracts = yield from self._get_contract()

        # For all contracts
        for contract, contract_url in contracts.items():
            #Get xls of all bills
            xls = yield from self._get_excel_historic_data(contract)
            #Import consumption data from excel bills
            bills = self._get_data_from_excel(xls)
            # Add contract
            self._data[contract] = bills
        return None

    def get_data(self, contract=None):
        """Return collected data."""
        if contract is None:
            return self._data
        if contract in self._data.keys():
            return {contract: self._data[contract]}
        raise PyEnergirError("Contract {} not found".format(contract))

    def get_contracts(self):
        """Return Contract list."""
        return set(self._data.keys())

    async def close_session(self):
        """Close current session."""
        await self._session.close()
