# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .analytic import *
from .farm import *


def register():
    Pool.register(
        Account,
        StockMove,
        Group,
        MoveEvent,
        TransformationEvent,
        module='farm_breeding', type_='model')
