from collections import namedtuple
from asynctest import TestCase as AsyncTestCase, mock
import asyncio
from ..routes import unpack_pds_settings_to_user_facing_schema


class TestRoutesFunctions(AsyncTestCase):
    async def test_unpack_pds_settings_to_user_facing_schema(self):
        pds_settings = {
            "scope": "admin",
            "grant_type": "client_credentials",
            "client_secret": "string",
            "client_id": "string",
        }
        test_against = [
            {
                "instance_name": "string",
                "client_id": "string",
                "client_secret": "string",
                "driver": {
                    "name": "own_your_data_data_vault",
                    "own_your_data_data_vault": {
                        "grant_type": "client_credentials",
                        "scope": "admin",
                    },
                },
            }
        ]

        list_of_pds = []
        pds_1 = namedtuple("PDS", "settings type name")
        pds_1.type = test_against[0]["driver"]["name"]
        pds_1.settings = pds_settings
        pds_1.name = test_against[0]["instance_name"]
        list_of_pds.append(pds_1)
        list_of_pds.append(pds_1)

        result = unpack_pds_settings_to_user_facing_schema(list_of_pds)
        assert len(result) == 2
        assert result[0] == test_against[0]
