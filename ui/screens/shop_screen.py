"""
ui/screens/shop_screen.py  (فاز ۵)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from ui.widgets.common import (
    COLOR_BG, COLOR_BAR_BG, COLOR_PRIMARY, COLOR_TEXT, COLOR_MUTED, COLOR_COIN, COLOR_GEM,
    EconomyBar, SolidBox, TopBar,
)
from ui.widgets.persian_widgets import PersianButton, PersianLabel

_CATEGORY_TITLES = {
    'special_shots': 'شلیک‌های ویژه',
    'guns': 'اسلحه‌ها',
    'helpers': 'کمک‌ها',
    'upgrades': 'ارتقاءها',
}

_REASON_TEXT = {
    'insufficient_funds': 'موجودی کافی نیست.',
    'already_owned': 'قبلاً خریداری شده.',
}


class ShopScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('فروشگاه', on_back=self._go_back))
        self.economy_bar = EconomyBar()
        root_bg.add_widget(self.economy_bar)

        self.feedback_label = PersianLabel(text='', font_size='14sp', color=COLOR_MUTED,
                                            size_hint_y=None, height=dp(28))
        root_bg.add_widget(self.feedback_label)

        scroll = ScrollView()
        self.item_list = GridLayout(cols=1, size_hint_y=None, spacing=dp(10), padding=dp(16))
        self.item_list.bind(minimum_height=self.item_list.setter('height'))
        scroll.add_widget(self.item_list)
        root_bg.add_widget(scroll)

        self.add_widget(root_bg)

    def on_pre_enter(self, *args):
        self.economy_bar.update(self.ctx.profile)
        self.feedback_label.set_text('')
        self._refresh_items()

    def _refresh_items(self):
        self.item_list.clear_widgets()
        shop = self.ctx.profile.shop
        for category in ('special_shots', 'guns', 'helpers', 'upgrades'):
            items = shop.get_items_by_category(category)
            if not items:
                continue
            header = PersianLabel(text=_CATEGORY_TITLES.get(category, category),
                                   font_size='18sp', bold=True, color=COLOR_TEXT,
                                   size_hint_y=None, height=dp(36), halign='left', valign='middle')
            header.bind(size=lambda w, s: setattr(w, 'text_size', s))
            self.item_list.add_widget(header)
            for item in items:
                self.item_list.add_widget(self._build_item_row(item))

    def _build_item_row(self, item):
        owned = item['id'] in self.ctx.profile.shop.owned_items
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(90),
                        spacing=dp(10), padding=dp(12))

        info_col = BoxLayout(orientation='vertical')
        name_label = PersianLabel(text=item['name_fa'], font_size='17sp', bold=True,
                                   color=COLOR_TEXT, halign='left', valign='middle')
        name_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(name_label)

        desc_label = PersianLabel(text=item['description_fa'], font_size='13sp',
                                   color=COLOR_MUTED, halign='left', valign='middle')
        desc_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(desc_label)

        price_bits = []
        if item.get('cost_coins'):
            price_bits.append(f"{item['cost_coins']} سکه")
        if item.get('cost_gems'):
            price_bits.append(f"{item['cost_gems']} جواهر")
        price_text = ' + '.join(price_bits) if price_bits else 'رایگان'
        price_label = PersianLabel(text=price_text, font_size='13sp',
                                    color=COLOR_GEM if item.get('cost_gems') else COLOR_COIN,
                                    halign='left', valign='middle')
        price_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(price_label)
        row.add_widget(info_col)

        action_col = BoxLayout(size_hint=(None, 1), width=dp(110))
        if owned:
            owned_label = PersianLabel(text='خریداری‌شده', font_size='13sp', color=COLOR_MUTED)
            action_col.add_widget(owned_label)
        else:
            buy_btn = PersianButton(text='خرید', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            buy_btn.bind(on_release=lambda *_a, iid=item['id']: self._buy(iid))
            action_col.add_widget(buy_btn)
        row.add_widget(action_col)

        return row

    def _buy(self, item_id):
        result = self.ctx.profile.shop.purchase_item(item_id)
        if result['success']:
            self.ctx.profile.missions.report_event('shop_purchases', 1)
            self.ctx.save()
            self.feedback_label.set_text(f"«{result['item']['name_fa']}» خریداری شد.")
            self.economy_bar.update(self.ctx.profile)
            self._refresh_items()
        else:
            reason = _REASON_TEXT.get(result['reason'], result['reason'] or '')
            self.feedback_label.set_text(f"خرید ناموفق: {reason}")

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
