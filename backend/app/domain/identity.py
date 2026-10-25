from dataclasses import dataclass, field


@dataclass(init=False, unsafe_hash=True)
class Member:
    _id: str
    _name: str = field(compare=False)

    def __init__(self, id: str, name: str) -> None:
        self._id = id
        self._name = name

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


@dataclass(frozen=True)
class User:
    id: str
    name: str = field(compare=False)
