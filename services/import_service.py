import io
import os

import aiohttp
import pandas
from numpy import ndarray
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.connection import get_wolrus_connection, async_session
from database.entities import GroupLeader, Group
from database.models import GroupModel
from services.data_service import get_or_create_group_leader, get_or_create_group, update_groups_leaders_info

SHEET_ID = os.getenv('WOL_HOME_GROUP_SHEET_ID')
YOUTH_TABLE_ID = os.getenv('WOL_HOME_GROUP_YOUTH_ID')
GENERAL_TABLE_ID = os.getenv('WOL_HOME_GROUP_GENERAL_ID')
URL = 'https://docs.google.com/spreadsheets/d/{}/export?format=csv&gid={}'


async def import_data():
    await parse_data_from_hub()
    await parse_data_from_google(GENERAL_TABLE_ID)
    await parse_data_from_google(YOUTH_TABLE_ID)
    await check_open_groups()


async def parse_data_from_hub():
    connection = await get_wolrus_connection()
    try:
        results = await connection.fetch(
            'SELECT subway, weekday, time_of_hg, type_age, type_of_hg, name_leader '
            'FROM master_data_history_view '
            'WHERE enable_for_site = true'
        )
        group_list: list[GroupModel] = list()
        for result in results:
            group_leader: GroupLeader = await get_or_create_group_leader(name=result.get('name_leader'))
            group_list.append(
                GroupModel(
                    metro=result.get('subway'),
                    day=result.get('weekday'),
                    time=result.get('time_of_hg'),
                    age=result.get('type_age'),
                    type=result.get('type_of_hg'),
                    leader_id=group_leader.id
                )
            )
        await get_or_create_group(group_list)
    finally:
        await connection.close()


async def parse_data_from_google(table_id):
    url: str = URL.format(SHEET_ID, table_id)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data: str = await response.text()
            data_from_google: ndarray = pandas.read_csv(io.StringIO(data)).values
            leader_name_cell: int = 2 if table_id == GENERAL_TABLE_ID else 1
            leader_tg_cell: int = 4 if table_id == GENERAL_TABLE_ID else 6
            for row in data_from_google:
                await update_groups_leaders_info(
                    group_leader_name=row[leader_name_cell].strip(),
                    regional_leader_name=row[0],
                    telegram_login=str(row[leader_tg_cell]).replace('@', '')
                )


async def check_open_groups():
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(Group).options(joinedload(Group.group_leader)))
            groups = result.scalars().all()
            connection = await get_wolrus_connection()
            try:
                for group in groups:
                    group_status = await connection.fetchval(
                        f'SELECT enable_for_site '
                        f'FROM master_data_history_view '
                        f'WHERE name_leader = \'{group.group_leader.name}\' '
                        f'AND weekday = \'{group.day}\' '
                        f'AND time_of_hg = \'{group.time}\' '
                        f'AND subway = \'{group.metro}\' '
                        f'AND type_age = \'{group.age}\' '
                        f'AND type_of_hg = \'{group.type}\''
                    )
                    if group_status is None or group_status is False:
                        group.is_open = False
            finally:
                await connection.close()
