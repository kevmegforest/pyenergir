"""PyEnergir Entrypoint Module."""

import argparse
import sys
import datetime
import asyncio

from pyenergir import EnergirClient, REQUESTS_TIMEOUT, ENERGIR_TIMEZONE
from pyenergir.output import output_text, output_json

VERSION = "2.4.0"


def main():
    """Entrypoint function."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username',
                        help='Energir username')
    parser.add_argument('-p', '--password',
                        help='Password')
    parser.add_argument('-c', '--contract',
                        default=None, help='Contract number')
    parser.add_argument('-j', '--json', action='store_true',
                        default=False, help='Json output')
    parser.add_argument('-l', '--list-contracts', action='store_true',
                        default=False, help='List all your contracts')
    parser.add_argument('-t', '--timeout',
                        default=REQUESTS_TIMEOUT, help='Request timeout')
    parser.add_argument('-V', '--version', action='store_true',
                        default=False, help='Show version')


    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return 0

    if not args.username or not args.password:
        parser.print_usage()
        print("pyenergir: error: the following arguments are required: "
              "-u/--username, -p/--password")
        return 3

    client = EnergirClient(args.username, args.password, args.contract, args.timeout)
    loop = asyncio.get_event_loop()

    async_func = client.fetch_data()

    try:
        fut = asyncio.wait([async_func])
        loop.run_until_complete(fut)
    except BaseException as exp:
        print(exp)
        return 1
    finally:
        close_fut = asyncio.wait([client.close_session()])
        loop.run_until_complete(close_fut)

    if not client.get_data():
        return 2

    if args.list_contracts:
        print("Contracts: {}".format(", ".join(client.get_contracts())))
    elif args.json:
        output_json(client.get_data(args.contract))
    else:
        output_text(args.username, client.get_data(args.contract))
    return 0


if __name__ == '__main__':
    sys.exit(main())
