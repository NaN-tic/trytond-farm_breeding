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
        CreateBreedingStart,
        Specie,
        module='farm_breeding', type_='model')
    Pool.register(
        CreateBreeding,
        module='farm', type_='wizard')
