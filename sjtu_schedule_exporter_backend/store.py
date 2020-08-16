import pickle
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from aredis import StrictRedis
from pydantic import BaseModel


class User(BaseModel):
    username: str
    state: dict


class AbstractRateLimitStore(ABC):
    @abstractmethod
    async def is_limit(self, key: str) -> bool:
        return NotImplemented

    @abstractmethod
    async def limit(self, key: str, time: int = 60):
        return NotImplemented


class AbstractSessionStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> User:
        return NotImplemented

    @abstractmethod
    async def put(self, value: User, key: Optional[str] = None) -> str:
        return NotImplemented

    @abstractmethod
    async def delete(self, key: str):
        return NotImplemented


class RedisRateLimitStore(AbstractRateLimitStore):
    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0):
        self.client = StrictRedis(host=host, port=port, db=db)

    async def is_limit(self, key: str) -> bool:
        return await self.client.get(key) is not None

    async def limit(self, key: str, time: int = 60):
        async with await self.client.pipeline() as pipe:
            await pipe.set(key, "1")
            await pipe.expire(key, time)
            await pipe.execute()


class RedisSessionStore(AbstractSessionStore):
    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0):
        self.client = StrictRedis(host=host, port=port, db=db)

    async def get(self, key: str) -> Optional[User]:
        if not (_user_bytes := await self.client.get(key)):
            return None
        _user = pickle.loads(_user_bytes)
        return User(**_user)

    async def put(self, value: User, key: Optional[str] = None) -> str:
        if not key:
            key = uuid.uuid4().hex
        _user = pickle.dumps(value.dict())
        async with await self.client.pipeline() as pipe:
            await pipe.set(key, _user)
            await pipe.expire(key, 1200)
            await pipe.execute()
        return key

    async def delete(self, key: str):
        await self.client.delete(key)
