from enum import Enum


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class GenderALL(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    ALL = "ALL"
