from dataclasses import dataclass
from datetime import time


@dataclass
class UserModel:
    first_name: str
    last_name: str
    username: str
    telegram_id: int


@dataclass
class GroupModel:
    metro: str
    day: str
    time: time
    age: str
    type: str
    leader_id: int


@dataclass
class JoinModel:
    date: str
    first_name: str
    last_name: str
    phone: str
    telegram: str
    leader_name: str
    district_leader: str
    is_youth: bool

    def to_list(self):
        return [
            self.date,
            self.first_name,
            self.last_name,
            self.phone,
            self.telegram,
            self.leader_name,
            self.district_leader,
        ]
