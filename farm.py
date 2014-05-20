# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['Group', 'MoveEvent', 'TransformationEvent']
__metaclass__ = PoolMeta


class Group:
    __name__ = 'farm.animal.group'

    is_breeding = fields.Boolean('Is Breeding?', select=True)
    breeding_account = fields.Many2One('analytic_account.account',
        'Breeding Account', readonly=True, domain=[
            ('is_breeding', '=', True),
            ], select=True, ondelete='CASCADE',
        states={
            'required': Eval('is_breeding', False),
            'invisible': ~Eval('is_breeding', False),
            }, depends=['is_breeding'])


class MoveEvent:
    __name__ = 'farm.move.event'

    @classmethod
    def validate_event(cls, events):
        super(MoveEvent, cls).validate_event(events)
        for event in events:
            if event.animal_type != 'group':
                continue
            if not event.to_location.analytic_accounts:
                continue
            for account in event.to_location.analytic_accounts.accounts:
                if event.to_animal_group.breeding_account == account:
                    break
                if account.is_breeding:
                    event.animal_group.breeding_account = account
                    event.animal_group.save()
                    break


class TransformationEvent:
    __name__ = 'farm.transformation.event'

    @classmethod
    def validate_event(cls, events):
        super(TransformationEvent, cls).validate_event(events)
        for event in events:
            if event.to_animal_type != 'group':
                continue
            if not event.to_location.analytic_accounts:
                continue
            for account in event.to_location.analytic_accounts.accounts:
                if event.to_animal_group.breeding_account == account:
                    break
                if account.is_breeding:
                    event.to_animal_group.breeding_account = account
                    event.to_animal_group.save()
                    break
