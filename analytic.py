# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import And, Eval, Greater, Not

__all__ = ['Account', 'StockMove']

_DOMAIN_BREEDING_ACCOUNTS = [
    ('type', '=', 'normal'),
    ['OR',
        ('parent', 'child_of', [Eval('id', -1)]),
        ('parent', '=', None),
        ],
    ]
_STATES_BREEDING_ACCOUNTS = {
    'invisible': Not(Eval('is_breeding', False)),
    'required': And(Eval('is_breeding', False), Greater(Eval('id', 0), 0)),
    }
_DEPENDS_BREEDING_ACCOUNTS = ['id', 'is_breeding', 'active']


class Account(metaclass=PoolMeta):
    __name__ = 'analytic_account.account'

    is_breeding = fields.Boolean('Is Breeding Account?')
    animals_account = fields.Many2One('analytic_account.account',
        'Animals Account', domain=_DOMAIN_BREEDING_ACCOUNTS,
        states=_STATES_BREEDING_ACCOUNTS)
    feed_account = fields.Many2One('analytic_account.account',
        'Feed Account', domain=_DOMAIN_BREEDING_ACCOUNTS,
        states=_STATES_BREEDING_ACCOUNTS)
    medications_account = fields.Many2One('analytic_account.account',
        'Medications Account', domain=_DOMAIN_BREEDING_ACCOUNTS,
        states=_STATES_BREEDING_ACCOUNTS)
    animal_groups = fields.One2Many('farm.animal.group', 'breeding_account',
        'Animal Groups', domain=[
            ('is_breeding', '=', True),
            ], readonly=True,
        states={
            'invisible': Not(Eval('is_breeding', False)),
            })

    @classmethod
    def __setup__(cls):
        super(Account, cls).__setup__()
        cls._breeding_child_account_fields = [
            'animals_account',
            'feed_account',
            'medications_account',
            ]

    @staticmethod
    def default_is_breeding():
        return False

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        breeding_indexes = []
        for i, vals in enumerate(vlist):
            if vals.get('is_breeding'):
                breeding_indexes.append(i)
                vals['is_breeding'] = False
        new_accounts = super(Account, cls).create(vlist)
        for i in breeding_indexes:
            account = new_accounts[i]
            account.is_breeding = True

            accounts = account._get_breeding_childs_accounts()
            for fname, child_acc in accounts.items():
                setattr(account, fname, child_acc)
            account.save()
        return new_accounts

    def _get_breeding_childs_accounts(self):
        Account = self.__class__

        breeding_accounts = {}
        for fname in self._breeding_child_account_fields:
            if getattr(self, fname, False):
                continue
            new_account = Account()
            new_account.name = getattr(Account, fname).string
            new_account.type = 'normal'
            new_account.company = self.company
            new_account.currency = self.currency
            new_account.root = self.root
            new_account.parent = self
            new_account.state = self.state
            breeding_accounts[fname] = new_account
        return breeding_accounts

    @classmethod
    def view_attributes(cls):
        res = super(Account, cls).view_attributes()
        res += [
            ('/form/notebook/page[@id="breeding_accounts"]', 'states', {
                    'invisible': Not(Eval('is_breeding', False)),
                    }),
            ]
        return res


class StockMove(metaclass=PoolMeta):
    __name__ = 'stock.move'

    def _get_analytic_accounts(self, type):
        pool = Pool()
        FeedEvent = pool.get('farm.feed.event')
        MedicationEvent = pool.get('farm.medication.event')
        MoveEvent = pool.get('farm.move.event')
        TransformationEvent = pool.get('farm.transformation.event')

        def replace_account(account_list, old_account, new_account):
            i = account_list.index(old_account)
            account_list.remove(old_account)
            account_list.insert(i, new_account)

        accounts = super(StockMove, self)._get_analytic_accounts(type)
        if type != 'expense' or not self.origin:
            return accounts

        accounts = list(accounts)
        for account in accounts[:]:
            if account.is_breeding:
                if isinstance(self.origin, (MoveEvent, TransformationEvent)):
                    replace_account(accounts, account, account.animals_account)
                elif isinstance(self.origin, FeedEvent):
                    replace_account(accounts, account, account.feed_account)
                elif isinstance(self.origin, MedicationEvent):
                    replace_account(accounts, account,
                        account.medications_account)
        return accounts
