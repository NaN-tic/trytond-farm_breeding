# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button

__all__ = ['Group', 'MoveEvent', 'TransformationEvent',
    'CreateBreeding', 'CreateBreedingStart', 'Specie']
__metaclass__ = PoolMeta


class Group:
    __name__ = 'farm.animal.group'

    is_breeding = fields.Boolean('Is Breeding?', readonly=True, select=True)
    breeding_account = fields.Many2One('analytic_account.account',
        'Breeding Account', readonly=True, domain=[
            ('is_breeding', '=', True),
            ], select=True, ondelete='CASCADE',
        states={
            'required': Eval('is_breeding', False),
            'invisible': ~Eval('is_breeding', False),
            }, depends=['is_breeding'])

    @classmethod
    def _calc_number(cls, specie_id, farm_id, vals):
        pool = Pool()
        Location = pool.get('stock.location')

        number = super(Group, cls)._calc_number(specie_id, farm_id, vals)
        if number and vals.get('is_breeding'):
            assert vals.get('initial_location')
            location = Location(vals['initial_location'])

            number = ((location.code if location.code else location.name) +
                '/' + number)
        return number


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


class CreateBreeding(Wizard):
    '''Create Breeding'''
    __name__ = 'farm.create_breeding'

    start = StateView('farm.create_breeding.start',
        'farm_breeding.create_breeding_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateAction('farm.act_farm_animal_group')

    @classmethod
    def __setup__(cls):
        super(CreateBreeding, cls).__setup__()
        cls._error_messages.update({
                'animals_in_location': ('There are %(quantity)s animals in '
                    'group(s) in location "%(location)s".\nPlease, empty the '
                    'location before create a new breeding.'),
                'location_silos_not_empty': ('The silos that fed the location '
                    '"%(location)s" are not empty. Bellow are listed the '
                    'silos and the feed quantities remaining in them.\n'
                    'Please, empty them before create the breeding.\n\n'
                    '%(not_empty_silos)s'),
                })

    def do_create_(self, action):
        pool = Pool()
        AnalyticAccount = pool.get('analytic_account.account')
        AnimalGroup = pool.get('farm.animal.group')
        Location = pool.get('stock.location')
        Lot = pool.get('stock.lot')
        Product = pool.get('product.product')

        with Transaction().set_context(locations=[self.start.location.id]):
            group_quantity = self.start.specie.group_product.quantity
        if group_quantity > 0:
            self.raise_user_error('animals_in_location', {
                    'location': self.start.location.rec_name,
                    'quantity': group_quantity,
                    })

        silo_locations = Location.search([
                ('silo', '=', True),
                ('locations_to_fed', 'in', [self.start.location.id]),
                ])
        pbl = Product.products_by_location([l.id for l in silo_locations],
            with_childs=False, grouping=('product', 'lot'))
        not_empty_silos = []
        for (location_id, product_id, lot_id), quantity in pbl.iteritems():
            if (Decimal(str(quantity)).quantize(Decimal('0.01'))
                    > Decimal('0.01')):
                if lot_id is not None:
                    not_empty_silos.append(" - %s: %s (%s)" % (
                            Location(location_id).rec_name,
                            Product(product_id).rec_name,
                            Lot(lot_id).rec_name))
                else:
                    not_empty_silos.append(" - %s: %s" % (
                            Location(location_id).rec_name,
                            Product(product_id).rec_name))
        if not_empty_silos:
            self.raise_user_error('location_silos_not_empty', {
                    'location': self.start.location.rec_name,
                    'not_empty_silos': "\n".join(not_empty_silos),
                    })

        breeding_account = AnalyticAccount()
        breeding_account.name = 'Temp'
        breeding_account.is_breeding = True
        breeding_account.type = 'normal'
        breeding_account.root = (self.start.breeding_account_parent.root
            if self.start.breeding_account_parent.type != 'root'
            else self.start.breeding_account_parent)
        breeding_account.parent = self.start.breeding_account_parent
        breeding_account.state = 'opened'
        breeding_account.save()

        with Transaction().set_context(no_create_stock_move=True):
            breeding_group = AnimalGroup()
            breeding_group.is_breeding = True
            breeding_group.breeding_account = breeding_account
            breeding_group.specie = self.start.specie,
            breeding_group.breed = self.start.breed,
            breeding_group.origin = 'raised'
            breeding_group.initial_location = self.start.location,
            breeding_group.initial_quantity = 0
            breeding_group.save()

        breeding_account.name = breeding_group.number
        breeding_account.animal_groups.append(breeding_group.id)
        breeding_account.save()

        setattr(self.start.location,
            'analytic_account_%s' % breeding_account.root.id,
            breeding_account)
        self.start.location.save()

        action['views'].reverse()
        return action, {'res_id': [breeding_group.id]}


class CreateBreedingStart(ModelView):
    'Create Breeding Start'
    __name__ = 'farm.create_breeding.start'

    specie = fields.Many2One('farm.specie', 'Specie', domain=[
            ('group_enabled', '=', True),
            ], required=True, readonly=True)
    breed = fields.Many2One('farm.specie.breed', 'Breed', domain=[
            ('specie', '=', Eval('specie')),
            ], required=True, depends=['specie'])
    location = fields.Many2One('stock.location', "Location", domain=[
            ('type', '=', 'storage'),
            ('silo', '=', False),
            ], required=True,
        context={
            'animal_type': 'group',
            'restrict_by_specie_animal_type': True,
            })
    breeding_account_parent = fields.Many2One('analytic_account.account',
        'Breeding Account Parent', domain=[
            ('is_breeding', '=', False),
            ], required=True)

    @staticmethod
    def default_specie():
        context = Transaction().context
        if context.get('active_model') == 'ir.ui.menu':
            pool = Pool()
            Menu = pool.get('ir.ui.menu')
            return Menu(context.get('active_id')).specie.id
        return context.get('specie')


class Specie:
    __name__ = 'farm.specie'

    @classmethod
    def _get_menus_by_animal_type(cls):
        pool = Pool()
        Menu = pool.get('ir.ui.menu')
        ModelData = pool.get('ir.model.data')

        menus_by_animal_type = super(Specie, cls)._get_menus_by_animal_type()

        menus_by_animal_type['group']['extra'].append(
            Menu(ModelData.get_id('farm_breeding',
                    'menu_farm_create_breeding')))
        return menus_by_animal_type
