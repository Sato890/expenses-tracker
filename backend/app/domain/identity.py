from dataclasses import dataclass, field


@dataclass(frozen=True)
class Member:
    id: str
    name: str = field(compare=False)


@dataclass(frozen=True)
class User:
    id: str
    name: str = field(compare=False)
