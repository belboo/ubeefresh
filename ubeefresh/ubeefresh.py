from __future__ import annotations
import re
import pickle
import gspread
import markdown2
from . import preview_templates as tpls
from bs4 import BeautifulSoup
from .enums import FreshArticleType, FreshStatus, FreshVisibility
from typing import List, Dict, Union
from gspread.utils import rowcol_to_a1
from oauth2client.service_account import ServiceAccountCredentials


def textify(text: str) -> str:
    # return re.sub(r'\s+', ' ', BeautifulSoup(s.replace('><', '> <')).get_text()).replace(' .', '.')
    return BeautifulSoup(markdown2.markdown(text), features="lxml").get_text().strip()


def filter_article_contents(text: str) -> str:
    # text, _ = re.subn(r'(^|\n)\s?-\s?([^\r\n]+)', r'<li>\2</li>', text)
    # text, _ = re.subn(r'\s?(</li>)', r'\1', text)
    # text, _ = re.subn(r'\s{2,}', r'<br>', text)
    # text, _ = re.subn(r'\s+([\!\.])', r'\1', text)
    # text, _ = re.subn(r'</li>\s?<br>', r'</li> ', text)

    return markdown2.markdown(text)


def filter_article_desc_text(text: str) -> str:
    return BeautifulSoup(markdown2.markdown(text), features="lxml").get_text().strip()


def smart_cap(s: str, sep: str = ' ') -> str:
    return s
    # stop_words = ['a', 'the', 'in', 'to', 'on', 'of', 'over']
    # return sep.join([word.capitalize() if word not in stop_words else word for word in s.split(sep)])


class UbeeFreshArticle:
    def __init__(self,
                 title: str = 'Unset',
                 desc: str = 'Unset',
                 desc_text: str = None,
                 lang: str = None,
                 translations: 'UbeeFreshArticleDict' = None,
                 parent: Union['UbeeFreshArticle', 'UbeeFreshFolder'] = None,
                 fd_id: int = None,
                 fd_type: FreshArticleType = FreshArticleType.PERMANENT,
                 fd_status: FreshStatus = FreshStatus.PUBLISHED,
                 gs_id: int = None,
                 gs_sheet: str = None,
                 gs_sheet_id: int = None,
                 gs_range: str = None):

        self.title = title
        self.desc = desc
        self.desc = desc
        if desc_text is None and desc is not None:
            desc_text = textify(desc)
        self.desc_text = desc_text
        self.lang = lang
        self.translations = translations if translations is not None else dict()
        self.parent = parent

        self.fd_id = fd_id
        self.fd_type = fd_type
        self.fd_status = fd_status

        self.gs_id = gs_id
        self.gs_sheet_id = gs_sheet_id
        self.gs_sheet = gs_sheet
        self.gs_range = gs_range

    def __str__(self):
        desc = 'UbeeFreshArticle "{}"'.format(self.title if self.title is not None else 'Unnamed')

        if self.desc is not None:
            desc += '\n desc: {}'.format(re.sub(r'\s+', ' ', self.desc))[:40]

        if len(self.translations) > 0:
            desc += '\n translations:'
            for lang in self.translations.keys():
                desc += '\n - {}'.format(lang.upper())

        return desc

    def __repr__(self):
        desc = '<UbeeFreshArticle[{}'.format(self.title if self.title is not None else 'Unnamed')

        if len(self.translations) > 0:
            desc += ', ({})'.format(','.join([lang.upper() for lang in self.translations.keys()]))
        desc += ']>'

        return desc

    def add_translation(self, lang: str, translation: 'UbeeFreshArticle'):
        if isinstance(self.parent, self.__class__):
            self.parent.add_translation(lang=lang, translation=translation)

        else:
            translation.parent = self
            self.translations[lang] = translation

        return self

    def get_link(self) -> str:
        if self.gs_id is None or self.gs_sheet_id is None or self.gs_range is None:
            return ''

        tpl = 'https://docs.google.com/spreadsheets/d/{id}/edit?#gid={sheet}&range={rng}'
        return tpl.format(id=self.gs_id, sheet=self.gs_sheet_id, rng=self.gs_range)


UbeeFreshArticleList = List[UbeeFreshArticle]
UbeeFreshArticleDict = Dict[str, UbeeFreshArticle]


class UbeeFreshFolder:
    def __init__(self,
                 name: str = 'Unset',
                 desc: str = None,
                 lang: str = None,
                 articles: 'UbeeFreshArticleDict' = None,
                 translations: 'UbeeFreshFolderDict' = None,
                 parent: object = None,
                 fd_id: int = None,
                 fd_visible: FreshVisibility = FreshVisibility.ALL_USERS,
                 gs_id: str = None,
                 gs_sheet: str = None,
                 gs_sheet_id: int = None,
                 gs_range: str = None):

        self.name = name
        self.desc = desc
        self.lang = lang
        self.articles = articles if articles is not None else list()
        self.translations = translations if translations is not None else dict()
        self.parent = parent

        self.fd_id = fd_id
        self.fd_visible = fd_visible

        self.gs_id = gs_id
        self.gs_sheet_id = gs_sheet_id
        self.gs_sheet = gs_sheet
        self.gs_range = gs_range

    def __str__(self):
        desc = 'UbeeFreshFolder "{}"'.format(self.name if self.name is not None else 'Unnamed')

        if self.desc is not None:
            desc += '\n desc: {}'.format(re.sub(r'\s+', ' ', self.desc))

        if len(self.translations) > 0:
            desc += '\n translations:'
            for lang in self.translations.keys():
                desc += '\n - {}'.format(lang.upper())

        if len(self.articles) > 0:
            desc += '\n articles:'
            for article in self.articles:
                desc += '\n - {}'.format(article.title if article.title is not None else 'Unnamed')

        return desc

    def __repr__(self):
        desc = '<UbeeFreshFolder[{}'.format(self.name if self.name is not None else 'Unnamed')

        if len(self.translations) > 0:
            desc += ', ({})'.format(','.join([lang.upper() for lang in self.translations.keys()]))

        if len(self.articles) > 0:
            desc += ', {} articles'.format(len(self.articles))

        desc += ']>'

        return desc

    def add_article(self, article: UbeeFreshArticle) -> 'UbeeFreshFolder':
        article.parent = self
        self.articles.append(article)

        return self

    def add_translation(self, lang: str, translation: 'UbeeFreshFolder'):
        if isinstance(self.parent, self.__class__):
            self.parent.add_translation(lang=lang, translation=translation)

        else:
            translation.parent = self
            self.translations[lang] = translation

        return self

    def get_link(self) -> str:
        if self.gs_id is None or self.gs_sheet_id is None or self.gs_range is None:
            return ''

        tpl = 'https://docs.google.com/spreadsheets/d/{id}/edit?#gid={sheet}&range={rng}'
        return tpl.format(id=self.gs_id, sheet=self.gs_sheet_id, rng=self.gs_range)


UbeeFreshFolderList = List[UbeeFreshFolder]
UbeeFreshFolderDict = Dict[str, UbeeFreshFolder]


class UbeeFreshCategory:
    def __init__(self,
                 name: str = 'Unset',
                 desc: str = None,
                 lang: str = None,
                 folders: 'UbeeFreshFolderList' = None,
                 translations: 'UbeeFreshCategoryDict' = None,
                 parent: Union['UbeeFreshPortal', 'UbeeFreshCategory'] = None,
                 fd_id: int = None,
                 fd_portals: list = None,
                 fd_suffix: str = None,
                 gs_id: str = None,
                 gs_sheet: str = None,
                 gs_sheet_id: int = None,
                 gs_range: str = None):

        self.name = name
        self.desc = desc
        self.lang = lang
        self.folders = folders if folders is not None else list()
        self.translations = translations if translations is not None else dict()
        self.parent = parent

        self.fd_id = fd_id
        self.fd_portals = fd_portals if fd_portals is not None else list()
        self.fd_suffix = fd_suffix

        self.gs_id = gs_id
        self.gs_sheet = gs_sheet
        self.gs_sheet_id = gs_sheet_id
        self.gs_range = gs_range

    def __str__(self):
        desc = 'UbeeFreshCategory "{}"'.format(self.name if self.name is not None else 'Unnamed')
        desc += '\n desc: {}'.format(re.sub(r'\s+', ' ', self.desc)) if self.desc is not None else ''

        if len(self.translations) > 0:
            desc += '\n translations:'
            for lang in self.translations.keys():
                desc += '\n - {}'.format(lang.upper())

        if len(self.folders) > 0:
            desc += '\n folders:'
            for folder in self.folders:
                desc += '\n - {}'.format(folder.name if folder.name is not None else 'Unnamed')

        return desc

    def __repr__(self):
        desc = '<UbeeFreshCategory[{}'.format(self.name if self.name is not None else 'Unnamed')

        if len(self.translations) > 0:
            desc += ', ({})'.format(','.join([lang.upper() for lang in self.translations.keys()]))

        if len(self.folders) > 0:
            desc += ', {} folders'.format(len(self.folders))

        desc += ']>'

        return desc

    def add_folder(self, folder: UbeeFreshFolder = None) -> 'UbeeFreshCategory':
        folder.parent = self
        self.folders.append(folder)

        return self

    def add_translation(self, lang: str, translation: 'UbeeFreshCategory'):
        if isinstance(self.parent, self.__class__):
            self.parent.add_translation(lang=lang, translation=translation)

        else:
            translation.parent = self
            self.translations[lang] = translation

        return self

    def get_link(self) -> str:
        if self.gs_id is None or self.gs_sheet_id is None or self.gs_range is None:
            return ''

        tpl = 'https://docs.google.com/spreadsheets/d/{id}/edit?#gid={sheet}&range={rng}'
        return tpl.format(id=self.gs_id, sheet=self.gs_sheet_id, rng=self.gs_range)

    def update_in_gs(self):
        if self.fd_id is None:
            print('Freshdesk ID not set, nothing to update...')
            return

        if self.gs_id is None and self.parent is not None and self.parent.gs_id is None:
            print('Cannot find GS ID...')
            return

        if self.gs_sheet is None and self.gs_sheet_id is None:
            print('GS sheet name/ID not set...')
            return

        if self.gs_range is None:
            print('GS cell range not set...')
            return

        gs_id = self.gs_id if self.gs_id is not None else self.parent.gs_id

        scopes = ['https://spreadsheets.google.com/feeds',
                  'https://www.googleapis.com/auth/drive']

        credentials_file = '/tmp/gapps_credentials.json'

        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scopes)
        gc = gspread.authorize(credentials)

        wb = gc.open_by_key(gs_id)

        cat_sheet = wb.worksheet(self.gs_sheet)

        cat_name_cell = cat_sheet.acell(self.gs_range)

        if cat_name_cell.value.lower() != self.name.lower():
            print('Category name mismatch, won''t write anything...')
            return

        cat_fdid_cell = cat_sheet.cell(cat_name_cell.row, cat_name_cell.col + 1)

        if cat_fdid_cell.value != '':
            print('Overwriting prefious value #{} with #{}...'.format(cat_fdid_cell.value, self.fd_id))

        cat_sheet.update_cell(cat_name_cell.row, cat_name_cell.col + 1, self.fd_id)


UbeeFreshCategoryList = Dict[str, UbeeFreshCategory]
UbeeFreshCategoryDict = Dict[str, UbeeFreshCategory]


class UbeeFreshPortal:
    LANG_LIST = ['en', 'fr', 'de', 'it', 'es', 'ca']

    def __init__(self,
                 name: str = None,
                 categories: 'UbeeFreshCategoryList' = None,
                 gs_id: str = None,
                 fd_id: int = None,
                 fd_suffix: str = None):

        self.name = name
        self.categories = categories if categories is not None else list()
        self.gs_id = gs_id
        self.fd_id = fd_id
        self.fd_suffix = fd_suffix

    def __str__(self):
        desc = 'UbeeFreshPortal "{}"'.format(self.name if self.name is not None else 'Unnamed')
        desc += '\n GS ID: {}'.format(self.gs_id) if self.gs_id is not None else ''
        desc += '\n FD ID: {}'.format(self.fd_id) if self.fd_id is not None else ''
        desc += '\n FD Suffix: {}'.format(self.fd_suffix) if self.fd_suffix is not None else ''
        if len(self.categories) > 0:
            desc += '\n categories:'
            for category in self.categories:
                desc += '\n - {}'.format(category.name if category.name is not None else 'Unnamed')

        return desc

    def __repr__(self):
        desc = '<UbeeFreshPortal[{}'.format(self.name if self.name is not None else 'Unnamed')
        desc += ', GS ID: {}'.format(self.gs_id) if self.gs_id is not None else ''
        desc += ', FD ID: {}'.format(self.fd_id) if self.fd_id is not None else ''
        desc += ', FD Suffix: {}'.format(self.fd_suffix) if self.fd_suffix is not None else ''
        desc += ', {} categories'.format(len(self.categories)) if len(self.categories) > 0 else ''
        desc += ']>'

        return desc

    def add_category(self, category: UbeeFreshCategory = None):
        category.parent = self
        if self.fd_id is not None:
            category.fd_portals.append(self.fd_id)
        if category.fd_suffix is None and self.fd_suffix is not None:
            category.fd_suffix = self.fd_suffix

        self.categories.append(category)

        return self

    @staticmethod
    def find_lang_row(val):
        for row in range(len(val)):
            if val[row][0].lower() in UbeeFreshPortal.LANG_LIST:
                return row

        return None

    @staticmethod
    def init_contents(val):
        origin = None
        translations = {}

        lang_row = UbeeFreshPortal.find_lang_row(val)

        if lang_row is None:
            return None, None

        for col in range(len(val[lang_row])):

            if val[lang_row][col].lower() == 'en':
                origin = (lang_row, col)
            elif val[lang_row][col].lower() in UbeeFreshPortal.LANG_LIST:
                translations[val[lang_row][col].lower()] = (lang_row, col)

        return origin, translations

    @classmethod
    def from_gs(cls, gs_id, name: str = None) -> 'UbeeFreshPortal':
        if gs_id is None:
            raise ValueError('Need GS ID to ge specified')

        scopes = ['https://spreadsheets.google.com/feeds',
                  'https://www.googleapis.com/auth/drive']

        credentials_file = '/tmp/gapps_credentials.json'

        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scopes)
        gc = gspread.authorize(credentials)

        wb = gc.open_by_key(gs_id)

        portal = cls(name=name if name is not None else wb.title.strip(), gs_id=gs_id)

        sheets = wb.worksheets()

        for sheet in sheets:

            print('Parsing sheet "{}"'.format(sheet.title))

            vals = sheet.get_all_values()
            n_rows = len(vals)
            origin, translations = cls.init_contents(vals)

            if origin is None:
                print('\033[FParsing sheet "{}" - No contents found...'.format(sheet.title))
                continue

            category = UbeeFreshCategory(
                name=smart_cap(vals[origin[0] + 1][origin[1]]),
                desc=vals[origin[0] + 2][origin[1]],
                gs_id=gs_id,
                gs_sheet=sheet.title,
                gs_sheet_id=sheet.id,
                gs_range=rowcol_to_a1(origin[0] + 2, origin[1] + 1),
                fd_id=vals[origin[0] + 1][origin[1] + 1] if vals[origin[0] + 1][origin[1] + 1] != '' else None
            )

            portal.add_category(category)

            for lang, lang_origin in translations.items():
                translation_name = smart_cap(vals[lang_origin[0] + 1][lang_origin[1]])
                translation_desc = vals[lang_origin[0] + 2][lang_origin[1]]

                category.add_translation(
                    lang,
                    UbeeFreshCategory(
                        name=translation_name,
                        desc=translation_desc,
                        lang=lang,
                        gs_id=gs_id,
                        gs_sheet=sheet.title,
                        gs_sheet_id=sheet.id,
                        gs_range=rowcol_to_a1(origin[0] + 1, lang_origin[1] + 1)
                    )
                )

            try:
                folder = None
                for row in range(origin[0] + 3, n_rows):
                    if vals[row][origin[1]] != '':
                        folder_name = vals[row][origin[1]].strip()

                        folder = UbeeFreshFolder(
                            name=folder_name,
                            gs_id=gs_id,
                            gs_sheet=sheet.title,
                            gs_sheet_id=sheet.id,
                            gs_range=rowcol_to_a1(row + 1, origin[1] + 1))

                        category.add_folder(folder)

                        for lang, lang_origin in translations.items():

                            folder_name = vals[row][lang_origin[1]].strip()

                            folder.add_translation(
                                lang=lang,
                                translation=UbeeFreshFolder(
                                    name=folder_name,
                                    gs_id=gs_id,
                                    gs_sheet=sheet.title,
                                    gs_sheet_id=sheet.id,
                                    gs_range=rowcol_to_a1(row + 1, lang_origin[1] + 1)
                                )
                            )

                    if vals[row][origin[1] + 1] != '':
                        article_title = vals[row][origin[1] + 1].strip()
                        article_text = vals[row][origin[1] + 2].strip()

                        article = UbeeFreshArticle(
                            title=article_title,
                            desc=filter_article_contents(article_text),
                            desc_text=filter_article_desc_text(article_text),
                            gs_id=gs_id,
                            gs_sheet=sheet.title,
                            gs_sheet_id=sheet.id,
                            gs_range=rowcol_to_a1(row + 1, origin[1] + 2)
                        )

                        folder.add_article(article)

                        for lang, lang_origin in translations.items():
                            article_title = vals[row][lang_origin[1] + 1].strip()
                            article_text = vals[row][lang_origin[1] + 2].strip()

                            article.add_translation(
                                lang=lang,
                                translation=UbeeFreshArticle(
                                    title=article_title,
                                    desc=filter_article_contents(article_text),
                                    desc_text=filter_article_desc_text(article_text),
                                    lang=lang,
                                    gs_id=gs_id,
                                    gs_sheet=sheet.title,
                                    gs_sheet_id=sheet.id,
                                    gs_range=rowcol_to_a1(row + 1, lang_origin[1] + 2)
                                )
                            )

            except IndexError as e:
                print('Failed to parse the sheet: {}'.format(e.args[0]))

        return portal

    def save(self, file: str):
        try:
            out_file = open(file, 'wb')
            pickle.dump(self, out_file)
        except FileNotFoundError:
            print('Cannot create or open {}! Save failed...'.format(file))
        except pickle.PickleError:
            print('Cannot save portal {} to {}...'.format(self.name, file))

    @classmethod
    def load(cls, file):
        try:
            in_file = open(file, 'rb')
            data = pickle.load(in_file)
        except FileNotFoundError:
            print('File {} not found! Load failed...'.format(file))
            return None
        except pickle.UnpicklingError:
            print('Failed to read data from {}! Load failed...'.format(file))
            return None

        if isinstance(data, cls):
            return data
        else:
            print('Data read from {} is not a UbeeFreshPortal! Load failed...'.format(file))
            return None

    def render_preview(self, file: str = 'preview.html'):

        print('Rendering preview of {} to {}...'.format(self.name, file))

        content_html = ''
        n_lang = 1

        for category in self.categories:

            category_contents_html = ''

            category_contents_html += tpls.row_start_category

            category_contents_html += tpls.category_header.format(
                category_name=category.name,
                category_desc=category.desc,
                href=category.get_link())

            n_lang = max(n_lang, len(category.translations) + 1)

            for lang, category_translation in category.translations.items():
                category_contents_html += tpls.category_header.format(
                    category_name=category_translation.name,
                    category_desc=category_translation.desc,
                    href=category.get_link())

            category_contents_html += tpls.row_end

            for folder in category.folders:
                category_contents_html += tpls.row_start_folder

                category_contents_html += tpls.folder.format(
                    folder_name=folder.name,
                    href=folder.get_link())

                n_lang = max(n_lang, len(folder.translations) + 1)

                for lang, folder_translation in folder.translations.items():
                    category_contents_html += tpls.folder.format(
                        folder_name=folder_translation.name,
                        href=folder_translation.get_link())

                category_contents_html += tpls.row_end

                for article in folder.articles:
                    category_contents_html += tpls.row_start_article

                    category_contents_html += tpls.article.format(
                        article_title=article.title,
                        article_desc=article.desc,
                        href=article.get_link())

                    n_lang = max(n_lang, len(article.translations) + 1)

                    for lang, article_translation in article.translations.items():
                        category_contents_html += tpls.article.format(
                            article_title=article_translation.title,
                            article_desc=article_translation.desc,
                            href=article_translation.get_link())

                    category_contents_html += tpls.row_end

            category_id, _ = re.subn(r'\s+', '_', category.name.lower())

            content_html += tpls.category.format(
                category_name=category.name,
                category_contents=category_contents_html,
                category_id=category_id)

        port_html = tpls.portal\
            .replace('{{portal}}', self.name)\
            .replace('{{body}}', content_html)\
            .replace('{{width}}', '{:.0f}'.format(n_lang))

        with open(file, 'w') as of:
            of.write(port_html)
