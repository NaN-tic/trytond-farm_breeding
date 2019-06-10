# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import analytic
from . import farm

def register():
    Pool.register(
        analytic.Account,
        analytic.StockMove,
        farm.Group,
        farm.MoveEvent,
        farm.TransformationEvent,
        farm.CreateBreedingStart,
        farm.Specie,
        module='farm_breeding', type_='model')
    Pool.register(
        farm.CreateBreeding,
        module='farm', type_='wizard')
