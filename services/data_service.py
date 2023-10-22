import logging
import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import select, insert, Result
from sqlalchemy.orm import joinedload

from database.connection import async_session
from database.entities import User, GroupLeader, Group, RegionLeader, JoinRequest
from database.models import UserModel, GroupModel, JoinModel

current_dir = os.getcwd()
creds_file_path = os.path.join(current_dir, 'google_creds.json')

scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_file_path, scope)


async def get_or_create_user(user_model: UserModel) -> None:
    async with async_session() as session:
        async with session.begin():
            result: Result = await session.execute(select(User).where(User.telegram_id == user_model.telegram_id))
            user: User = result.scalar_one_or_none()
            if user is None:
                await session.execute(insert(User), [{
                    'first_name': user_model.first_name,
                    'last_name': user_model.last_name,
                    'telegram_login': user_model.username,
                    'telegram_id': user_model.telegram_id
                }])
            else:
                user.last_login = datetime.now()

            group_leader = (await session.execute(
                select(GroupLeader).where(GroupLeader.telegram_login == user_model.username))).scalars().first()
            if group_leader is not None and group_leader.telegram_id is None:
                group_leader.telegram_id = user_model.telegram_id

            regional_leader = (await session.execute(
                select(RegionLeader).where(RegionLeader.telegram_login == user_model.username))).scalars().first()
            if regional_leader is not None and regional_leader.telegram_id is None:
                regional_leader.telegram_id = user_model.telegram_id


async def get_or_create_group_leader(name: str) -> GroupLeader:
    async with async_session() as session:
        async with session.begin():
            result: Result = await session.execute(select(GroupLeader).where(GroupLeader.name == name))
            group_leader: GroupLeader = result.scalar_one_or_none()
            if group_leader is None:
                group_leader = await session.scalar(insert(GroupLeader).returning(GroupLeader), [{'name': name}])
            return group_leader


async def update_groups_leaders_info(group_leader_name: str, regional_leader_name: str, telegram_login: str) -> None:
    async with async_session() as session:
        async with session.begin():
            regional_leader: RegionLeader = (await session.execute(
                select(RegionLeader).where(RegionLeader.name == regional_leader_name))) \
                .scalar_one_or_none()
            if regional_leader is None:
                regional_leader = await session \
                    .scalar(insert(RegionLeader).returning(RegionLeader), [{'name': regional_leader_name}])
            group_leader: GroupLeader = (await session.execute(
                select(GroupLeader).where(GroupLeader.name == group_leader_name))) \
                .scalar_one_or_none()
            if group_leader is not None:
                group_leader.region_leader_id = regional_leader.id
                group_leader.telegram_login = telegram_login


async def get_or_create_group(groups_list: list[GroupModel]) -> None:
    async with async_session() as session:
        async with session.begin():
            for new_group in groups_list:
                result: Result = await session.execute(
                    select(Group)
                    .where(Group.metro == new_group.metro)
                    .where(Group.day == new_group.day)
                    .where(Group.time == new_group.time)
                    .where(Group.age == new_group.age)
                    .where(Group.type == new_group.type)
                    .where(Group.leader_id == new_group.leader_id)
                )
                group: Group = result.scalar_one_or_none()
                if group is None:
                    await session.execute(insert(Group), [{
                        'metro': new_group.metro,
                        'day': new_group.day,
                        'time': new_group.time,
                        'age': new_group.age,
                        'type': new_group.type,
                        'is_open': True,
                        'leader_id': new_group.leader_id
                    }])
                else:
                    if group.is_open is False:
                        group.is_open = True


async def create_regional_leader(regional_leader_name: str, group_leader: GroupLeader) -> None:
    async with async_session() as session:
        async with session.begin():
            result: Result = await session.execute(
                select(RegionLeader).where(RegionLeader.name == regional_leader_name))
            regional_leader: RegionLeader = result.scalar_one_or_none()
            if regional_leader is None:
                regional_leader = await session.scalar(
                    insert(RegionLeader).returning(RegionLeader), [{'name': regional_leader_name}]
                )
                group_leader.region_leader = regional_leader
                group_leader.region_leader_id = regional_leader.id


async def get_all_opened_groups(metro: str):
    async with async_session() as session:
        result = await session.execute(
            select(Group)
            .where(Group.is_open)
            .filter(Group.metro.ilike(f'%{metro.lower()}%'))
            .options(joinedload(Group.group_leader))
        )
        return result.scalars().fetchall()


async def add_to_group(telegram_id: int, group_leader_name: str, is_youth: bool) -> GroupLeader:
    async with async_session() as session:
        async with session.begin():
            result: Result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user: User = result.scalar_one()
            logging.info(f'Получен пользователь: {user.first_name} {user.last_name}')
            result: Result = await session.execute(
                select(GroupLeader)
                .where(GroupLeader.name == group_leader_name)
                .options(joinedload(GroupLeader.region_leader))
            )
            group_leader: GroupLeader = result.scalar_one_or_none()
            logging.info(f'Определен лидер ДГ: {group_leader.name}')
            region_leader: RegionLeader = group_leader.region_leader
            if region_leader is not None:
                logging.info(f'Определен региональный лидер : {region_leader.name}')
            await session.execute(
                insert(JoinRequest), [{
                    'user_id': user.id,
                    'leader_id': group_leader.id
                }]
            )
            await add_join_request(JoinModel(
                date=datetime.now().strftime("%d.%m.%Y"),
                first_name=user.first_name,
                last_name=user.last_name,
                telegram=user.telegram_login,
                leader_name=group_leader.name,
                district_leader=region_leader.name
                if region_leader is not None and region_leader.name is not None
                else 'Имя не определено',
                is_youth=is_youth
            ))
            return group_leader


async def add_join_request(data: JoinModel):
    client = gspread.authorize(credentials)
    spreadsheet = client.open("Заявки на домашние группы")
    worksheet = spreadsheet.worksheet('Молодежные заявки' if data.is_youth else 'Общие заявки')
    values = worksheet.get_all_values()
    cell_values = data.to_list()
    first_empty_row = len(values) + 1
    for index, value in enumerate(cell_values):
        worksheet.update_cell(first_empty_row, index + 1, value)
    logging.info('Добавлено новое значение в таблицу заявок в ДГ')
