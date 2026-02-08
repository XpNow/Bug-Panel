from .base import EventData, NormalizedBlock, Parser, PayloadLine
from .bank import BankParser
from .offer import OfferParser
from .phone import PhoneParser
from .drop_item import DropItemParser
from .container import ContainerParser
from .connect import ConnectParser
from .admin import AdminParser
from .jewelry import JewelryParser

PARSERS: list[Parser] = [
    BankParser(),
    OfferParser(),
    PhoneParser(),
    DropItemParser(),
    ContainerParser(),
    ConnectParser(),
    AdminParser(),
    JewelryParser(),
]
