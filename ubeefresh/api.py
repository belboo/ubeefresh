import json
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError

from . import ubeefresh as uf
from .enums import FreshArticleType, FreshStatus, FreshVisibility, UbeeFreshAPIError
from typing import Tuple


class UbeeFreshAPI:
    __API_KEY = 'your-api-key'
    __DOMAIN = 'your-domain'

    def __init__(self,
                 apikey: str = None,
                 domain: str = None,
                 portals: list = None):

        self.apikey = apikey if apikey is not None else self.__API_KEY
        self.domain = domain if domain is not None else self.__DOMAIN
        self.portals = portals

        self.supported_langs = None
        self.primary_lang = 'en'

        fresh_adapter = HTTPAdapter(max_retries=5)

        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(self.apikey, 'gimmeaccess')

        self._session.mount('https://{domain}.freshdesk.com'.format(domain=self.domain), fresh_adapter)

        ok, settings = self.get_settings()
        if ok:
            if 'primary_language' in settings:
                self.primary_lang = settings.get('primary_language')
            if 'supported_languages' in settings:
                self.supported_langs = settings.get('supported_languages')

    def __str__(self):
        desc = 'UbeeFreshPortal "{}"'.format(self.domain.upper())
        desc += '\n - primary language: {}'.format(self.primary_lang)
        if self.supported_langs is not None:
            desc += '\n - supported languages: {}'.format(', '.join(self.supported_langs))

        return desc

    def __repr__(self):
        desc = '<UbeeFreshPortal[{}'.format(self.domain.upper())
        desc += ', lang={}'.format(self.primary_lang)
        if self.supported_langs is not None:
            desc += ', supported={}'.format(','.join(self.supported_langs))
        desc += ']>'
        return desc

    def get_product(self,
                    product_id: int):

        ok, data = self.get(endpoint='v2/products/{}'.format(product_id))

        if ok:
            return data

    def get_products(self,
                     page: int = None,
                     per_page: int = 100,
                     max_depth: int = 20):

        return self.get_list(endpoint='v2/products',
                             page=page,
                             per_page=per_page,
                             max_depth=max_depth)

    def get_articles(self,
                     folder_id: int,
                     page: int = None,
                     per_page: int = 100,
                     max_depth: int = 20):

        return self.get_list(endpoint='v2/solutions/folders/{}/articles'.format(folder_id),
                             page=page,
                             per_page=per_page,
                             max_depth=max_depth)

    def get_article_translations(self,
                                 article_id: int):

        return self._get_translations('v2/solutions/articles/{}'.format(article_id))

    def _create_article(self,
                        folder_id: int,
                        title: str,
                        desc: str,
                        typ: FreshArticleType = FreshArticleType.PERMANENT,
                        status: FreshStatus = FreshStatus.PUBLISHED,
                        meta_title: str = None,
                        meta_description: str = None,
                        meta_keywords: list = None):

        if folder_id is None:
            return False, None

        data = {
            'title': title,
            'description': desc,
            'type': typ.value if hasattr(typ, 'value') else typ,
            'status': status.value if hasattr(status, 'value') else status
        }

        seo_data = dict()
        if meta_title is not None:
            seo_data['meta_title'] = meta_title
        if meta_description is not None:
            seo_data['meta_description'] = meta_description
        if meta_keywords is not None:
            seo_data['meta_keywords'] = meta_keywords

        if len(seo_data) > 0:
            data['seo_data'] = seo_data

        ok, res = self.post(
            endpoint='v2/solutions/folders/{fid}/articles'.format(fid=folder_id),
            data=data)

        if not ok:
            if res.get('code') == 409:
                if res.get('response').get('errors', []).get('code') == 'duplicate_value':
                    return False, UbeeFreshAPIError.EXISTS

            if res.get('code') == 404:
                return False, UbeeFreshAPIError.NOT_FOUND

        return True, res.get('id')

    def _create_article_translation(self,
                                    article_id: int,
                                    lang: str,
                                    title: str,
                                    desc: str,
                                    status: FreshStatus = FreshStatus.PUBLISHED,
                                    meta_title: str = None,
                                    meta_description: str = None,
                                    meta_keywords: list = None):

        if article_id is None:
            return False, None

        data = {
            'title': title,
            'description': desc,
            'status': status.value if hasattr(status, 'value') else status
        }

        seo_data = dict()
        if meta_title is not None:
            seo_data['meta_title'] = meta_title
        if meta_description is not None:
            seo_data['meta_description'] = meta_description
        if meta_keywords is not None:
            seo_data['meta_keywords'] = meta_keywords

        if len(seo_data) > 0:
            data['seo_data'] = seo_data

        ok, res = self.post(
            endpoint='v2/solutions/articles/{aid}/{lang}'.format(aid=article_id, lang=lang),
            data=data)

        if not ok:
            if res.get('code') == 409:
                if res.get('response').get('errors', []).get('code') == 'duplicate_value':
                    return False, UbeeFreshAPIError.EXISTS

            if res.get('code') == 404:
                return False, UbeeFreshAPIError.NOT_FOUND

    def create_article(self,
                       article: uf.UbeeFreshArticle,
                       folder_id: int = None,
                       create_translations: bool = True,
                       create_parent: bool = False,
                       typ: int = None,
                       status: int = None):

        if article.fd_id is not None:
            print('Article {} already exists. Try using update...'.format(article.title))

        if folder_id is None:
            if isinstance(article.parent, uf.UbeeFreshFolder):
                if article.parent.fd_id is not None:
                    folder_id = article.parent.fd_id
                elif create_parent:
                    print(' - creating parent folder')
                    self.create_folder(
                        folder=article.parent,
                        create_translations=create_translations,
                        create_parent=create_parent,
                        create_articles=False)

                    if article.parent.fd_id is None:
                        print(' - failed to create parent. Can''t continue...')
                        return None

                    folder_id = article.parent.fd_id

        if article.lang is not None and article.lang != self.primary_lang:
            print('Article {} has lang={}, which seems to be a translation...'.format(
                article.title, article.lang))
            return None

        if typ is None:
            if article.fd_type is not None:
                typ = article.fd_type
            else:
                typ = FreshArticleType.PERMANENT

        if status is None:
            if article.fd_status is not None:
                status = article.fd_status
            else:
                status = FreshStatus.PUBLISHED

        ok, data = self._create_article(
            folder_id=folder_id,
            title=article.title,
            desc=article.desc,
            typ=typ,
            status=status)

        if not ok:
            print(' - creation failed')
            return None

        article.fd_id = data

        if create_translations and len(article.translations) > 0:
            for lang, translation in article.translations.items():
                self._create_article_translation(
                    article_id=article.fd_id,
                    lang=lang,
                    title=translation.title,
                    desc=translation.desc,
                    status=status)

    def _delete_article(self,
                        article_id: int):

        if article_id is None:
            return False, None

        ok, res = self.delete(endpoint='v2/solutions/articles/{aid}'.format(aid=article_id))

        if ok:
            return True, None

        if res.get('code') == 404:
            return False, UbeeFreshAPIError.NOT_FOUND

        return False, UbeeFreshAPIError.OTHER

    def delete_article(self,
                       article: uf.UbeeFreshArticle):

        if article.fd_id is None:
            print('Article FD ID is not set.')

        print('Deleting article {}.'.format(article.title))

        ok, _ = self._delete_article(article_id=article.fd_id)

        if ok:
            article.fd_id = None
            return

        print(' - deletion failed')

    def get_folders(self,
                    category_id: int,
                    page: int = None,
                    per_page: int = 100,
                    max_depth: int = 20):

        return self.get_list(endpoint='v2/solutions/categories/{}/folders'.format(category_id),
                             page=page,
                             per_page=per_page,
                             max_depth=max_depth)

    def _create_folder(self,
                       category_id: int,
                       name: str,
                       desc: str = None,
                       visibility: int = FreshVisibility.ALL_USERS):

        if category_id is None:
            return False, None

        data = {
            'name': name,
            'visibility': visibility.value if hasattr(visibility, 'value') else visibility
        }

        if desc is not None:
            data['description'] = desc

        ok, res = self.post(
            endpoint='v2/solutions/categories/{cid}/folders'.format(cid=category_id),
            data=data)

        if not ok:
            if res.get('code') == 409:
                if res.get('response').get('errors', []).get('code') == 'duplicate_value':
                    return False, UbeeFreshAPIError.EXISTS

            if res.get('code') == 404:
                return False, UbeeFreshAPIError.NOT_FOUND

        return True, res.get('id')

    def _create_folder_translation(self,
                                   folder_id: int,
                                   lang: str,
                                   name: str,
                                   desc: str = None):

        if folder_id is None:
            return False, None

        data = {
            'name': name,
        }

        if desc is not None:
            data['description'] = desc

        ok, res = self.post(
            endpoint='v2/solutions/folders/{fid}/{lang}'.format(fid=folder_id, lang=lang),
            data=data)

        if not ok:
            if res.get('code') == 409:
                if res.get('response').get('errors', []).get('code') == 'duplicate_value':
                    return False, UbeeFreshAPIError.EXISTS

            if res.get('code') == 404:
                return False, UbeeFreshAPIError.NOT_FOUND

    def create_folder(self,
                      folder: uf.UbeeFreshFolder,
                      category_id: int = None,
                      create_translations: bool = True,
                      create_parent: bool = False,
                      create_articles: bool = False,
                      visibility: int = FreshVisibility.ALL_USERS):

        if folder.fd_id is not None:
            print('Folder {} already exists. Try using update...'.format(folder.name))

        if category_id is None:
            if isinstance(folder.parent, uf.UbeeFreshCategory):
                if folder.parent.fd_id is not None:
                    category_id = folder.parent.fd_id
                elif create_parent:
                    print(' - creating parent category')
                    self.create_category(
                        category=folder.parent,
                        create_translations=create_translations,
                        create_folders=False)

                    if folder.parent.fd_id is None:
                        print(' - failed to create parent. Can''t continue...')
                        return None

                    category_id = folder.parent.fd_id

        if folder.lang is not None and folder.lang != self.primary_lang:
            print('Folder {} has lang={}, which seems to be a translation...'.format(
                folder.name, folder.lang))

        if visibility is None:
            visibility = folder.fd_visible

        ok, data = self._create_folder(
            category_id=category_id,
            name=folder.name,
            desc=folder.desc,
            visibility=visibility)

        if not ok:
            print(' - creation failed')
            return None

        folder.fd_id = data

        if create_translations and len(folder.translations) > 0:
            for lang, translation in folder.translations.items():
                self._create_folder_translation(
                    folder_id=folder.fd_id,
                    lang=lang,
                    name=translation.name,
                    desc=translation.desc)

        if create_articles and len(folder.articles) > 0:
            for article in folder.articles:
                self.create_article(
                    article=article,
                    create_translations=create_translations,
                    create_parent=False)

    def get_folder_translations(self,
                                folder_id: int):

        return self._get_translations('v2/solutions/folders/{}'.format(folder_id))

    def _delete_folder(self,
                       folder_id: int):

        if folder_id is None:
            return False, None

        ok, res = self.delete(endpoint='v2/solutions/folders/{fid}'.format(fid=folder_id))

        if ok:
            return True, None

        if res.get('code') == 404:
            return False, UbeeFreshAPIError.NOT_FOUND

        return False, UbeeFreshAPIError.OTHER

    def delete_folder(self,
                      folder: uf.UbeeFreshFolder):

        if folder.fd_id is None:
            print('Folder FD ID is not set.')

        print('Deleting folder {}.'.format(folder.name))

        ok, _ = self._delete_folder(folder_id=folder.fd_id)

        if ok:
            folder.fd_id = None
            return

        print(' - deletion failed')

    def get_categories(self,
                       page: int = None,
                       per_page: int = 100,
                       max_depth: int = 20):

        return self.get_list(endpoint='v2/solutions/categories',
                             page=page,
                             per_page=per_page,
                             max_depth=max_depth)

    def _create_category(self,
                         name: str,
                         desc: str = None,
                         portals: list = None):

        data = {
            'name': name,
        }

        if desc is not None:
            data['description'] = desc

        if portals is not None:
            data['visible_in_portals'] = portals
        elif self.portals is not None:
            data['visible_in_portals'] = self.portals

        ok, res = self.post(endpoint='v2/solutions/categories', data=data)

        if res.get('code') != 201:
            if res.get('code') == 409:
                if res.get('response', {}).get('errors', [{}])[0].get('code') == 'duplicate_value':
                    return False, UbeeFreshAPIError.EXISTS

            if res.get('code') == 404:
                return False, UbeeFreshAPIError.NOT_FOUND

        return True, res.get('id')

    def _create_category_translation(self,
                                     category_id: int,
                                     lang: str,
                                     name: str,
                                     desc: str = None):

        if category_id is None or lang is None:
            return False, None

        data = {
            'name': name,
        }

        if desc is not None:
            data['description'] = desc

        ok, res = self.post(
            endpoint='v2/solutions/categories/{cid}/{lang}'.format(cid=category_id, lang=lang),
            data=data)

        if not ok:
            print(ok, res)
            if res.get('code') == 409:
                if res.get('response', {}).get('errors', [{}])[0].get('code') == 'duplicate_value':
                    return False, UbeeFreshAPIError.EXISTS

            if res.get('code') == 404:
                return False, UbeeFreshAPIError.NOT_FOUND

        return True, res.get('id')

    def create_category(self,
                        category: uf.UbeeFreshCategory,
                        create_translations: bool = True,
                        create_folders: bool = False,
                        portals: list = None,
                        suffix: str = ''):

        if category.fd_id is not None:
            print('Category {} already exists. Try using update...'.format(category.name))

        if portals is not None:
            portals = portals
        elif self.portals is not None:
            portals = self.portals
        elif category.fd_portals is not None:
            portals = category.fd_portals

        if category.lang is not None and category.lang != self.primary_lang:
            print('Category {} has lang={}, which seems to be a translation...'.format(
                category.name, category.lang))

        if suffix != '':
            suffix = ' || {}'.format(category.fd_suffix)
        elif category.fd_suffix is not None:
            suffix = ' || {}'.format(category.fd_suffix)
        elif category.parent is not None and category.parent.fd_suffix is not None:
            suffix = ' || {}'.format(category.parent.fd_suffix)

        ok, data = self._create_category(
            name=category.name + suffix,
            desc=category.desc,
            portals=portals)

        if not ok:
            if data == UbeeFreshAPIError.EXISTS:
                print(' - already exists')
            else:
                print(' - creation failed')

            return None

        category.fd_id = data

        if create_translations and len(category.translations) > 0:
            for lang, translation in category.translations.items():
                self._create_category_translation(
                    category_id=category.fd_id,
                    lang=lang,
                    name=translation.name + suffix,
                    desc=translation.desc)

        if create_folders and len(category.folders) > 0:
            for folder in category.folders:
                self.create_folder(
                    folder=folder,
                    create_translations=create_translations,
                    create_parent=False,
                    create_articles=True)

    def _delete_category(self,
                         category_id: int):

        if category_id is None:
            return False, None

        ok, res = self.delete(endpoint='v2/solutions/categories/{cid}'.format(cid=category_id))

        if ok:
            return True, None

        if res.get('code') == 405:
            return True, UbeeFreshAPIError.METHOD_NOT_ALLOWED

        if res.get('code') == 404:
            return False, UbeeFreshAPIError.NOT_FOUND

        return False, UbeeFreshAPIError.OTHER

    def delete_category(self,
                        category: uf.UbeeFreshCategory):

        if category.fd_id is None:
            print('Category FD ID is not set.')

        print('Deleting category {}.'.format(category.name))

        ok, _ = self._delete_category(category_id=category.fd_id)

        if ok:
            category.fd_id = None
            return

        print(' - deletion failed')

    def get_category_translations(self,
                                  category_id: int):

        return self._get_translations('v2/solutions/categories/{}'.format(category_id))

    def _get_translations(self,
                          entity: str):

        translations = {}

        for lang in self.supported_langs:
            ok, data = self.get('{}/{}'.format(entity, lang))

            if ok:
                translations[lang] = data

        return translations

    def get_list(self,
                 endpoint: str,
                 page: int = None,
                 per_page: int = 100,
                 max_depth: int = 20):

        next_page = page if page is not None else 1

        ok, data = self.get(endpoint=endpoint,
                            page=next_page,
                            per_page=per_page)

        if ok and data is not None:
            if page is not None or len(data) < per_page:
                return data

            for i in range(max_depth):
                next_page += 1
                ok, next_page_data = self.get(endpoint=endpoint,
                                              page=next_page,
                                              per_page=per_page)

                if ok and next_page_data is not None:
                    data = data + next_page_data
                    if len(next_page_data) < per_page:
                        break

            return data

        return None

    def get_settings(self):
        return self.get(endpoint='v2/settings/helpdesk')

    def get(self, endpoint: str, page: int = None, per_page: int = None) -> Tuple[bool, dict]:
        url_tpl = 'https://{domain}.freshdesk.com/api/{endpoint}'

        url = url_tpl.format(
            domain=self.domain,
            endpoint=endpoint)

        params = {}

        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = min(per_page, 100)

        try:
            res = self._session.get(
                url=url,
                params=params,
                timeout=10.0)
        except ConnectionError as ce:
            return False, {'code': -1, 'response': {}}

        if res.status_code == 200:
            return True, res.json()

        if res.status_code == 404:
            try:
                res_json = res.json()
            except json.JSONDecodeError:
                res_json = {}

            return False, {'code': res.status_code, 'response': res_json}

        print('Call to Freshdesk API failed:')
        res.raise_for_status()

    def post(self, endpoint: str, data: dict = None) -> Tuple[bool, dict]:
        url_tpl = 'https://{domain}.freshdesk.com/api/{endpoint}'

        url = url_tpl.format(
            domain=self.domain,
            endpoint=endpoint)

        try:
            res = self._session.post(
                url=url,
                json=data,
                timeout=5.0)
        except ConnectionError as ce:
            return False, {'code': -1, 'response': {}}

        if res.status_code == 201:
            return True, res.json()

        if res.status_code in (404, 409):
            return False, {'code': res.status_code, 'response': res.json()}

        print('Call to Freshdesk API failed:')
        res.raise_for_status()

    def delete(self, endpoint: str) -> Tuple[bool, dict]:
        url_tpl = 'https://{domain}.freshdesk.com/api/{endpoint}'

        url = url_tpl.format(
            domain=self.domain,
            endpoint=endpoint)

        try:
            res = self._session.delete(
                url=url,
                timeout=5.0)
        except ConnectionError as ce:
            return False, {'code': -1, 'response': {}}

        if res.status_code == 204:
            return True, {}

        if res.status_code in (404, 405, 409):
            return False, {'code': res.status_code, 'reply': res.json()}

        print('Call to Freshdesk API failed:')
        res.raise_for_status()

    def read_portal(self,
                    name: str,
                    verbosity: int = 1,
                    category_subset: list = None):

        portal = uf.UbeeFreshPortal(name=name)

        fd_categories = self.get_categories()

        if verbosity > 0:
            print('Found {} categories:'.format(len(fd_categories)))

        for ic, fd_category in enumerate(fd_categories):
            if category_subset is not None and ic not in category_subset:
                continue

            if verbosity > 0:
                print('- {}'.format(fd_category.get('name', 'Unknown')))

            category = uf.UbeeFreshCategory(
                name=fd_category.get('name'),
                desc=fd_category.get('description'),
                parent=portal,
                fd_id=fd_category.get('id'),
                fd_portals=fd_category.get('visible_in_portals')
            )

            portal.add_category(category)

            category_translations = self.get_category_translations(category.fd_id)

            if len(category_translations) > 0 and verbosity > 1:
                print('  - trans: {}'.format(', '.join(category_translations.keys())))

            for lang, translation in category_translations.items():
                category.add_translation(
                    lang=lang,
                    translation=uf.UbeeFreshCategory(
                        name=translation.get('name'),
                        desc=translation.get('description'),
                        parent=category,
                        fd_id=translation.get('id'),
                        fd_portals=translation.get('visible_in_portals')
                    )
                )

            # -------------------------------------------------------
            # Folders

            fd_folders = self.get_folders(category.fd_id)

            if len(fd_folders) > 0 and verbosity > 0:
                print('  - fetching {} folders'.format(len(fd_folders)))

            for fd_folder in fd_folders:
                if verbosity > 0:
                    print('    - {}'.format(fd_folder.get('name', 'Unknown')))

                folder = uf.UbeeFreshFolder(
                    name=fd_folder.get('name'),
                    desc=fd_folder.get('description'),
                    parent=category,
                    fd_id=fd_folder.get('id'),
                    fd_visible=fd_folder.get('visible') == 1
                )

                category.add_folder(folder)

                folder_translations = self.get_folder_translations(folder.fd_id)

                if len(folder_translations) > 0 and verbosity > 1:
                    print('      - trans: {}'.format(', '.join(folder_translations.keys())))

                for lang, translation in folder_translations.items():
                    folder.add_translation(
                        lang=lang,
                        translation=uf.UbeeFreshFolder(
                            name=translation.get('name'),
                            desc=translation.get('description'),
                            parent=folder,
                            fd_id=translation.get('id'),
                            fd_visible=translation.get('visible') == 1
                        )
                    )

                # -------------------------------------------------------
                # Articles

                fd_articles = self.get_articles(folder.fd_id)

                if len(fd_articles) > 0 and verbosity > 1:
                    print('      - fetching {} articles'.format(len(fd_articles)))

                for fd_article in fd_articles:
                    if verbosity > 2:
                        print('        - {}'.format(fd_article.get('title', 'Unknown')))

                    status = FreshStatus.PUBLISHED
                    if fd_article.get('status') == FreshStatus.DRAFT:
                        status = FreshStatus.DRAFT

                    typ = FreshArticleType.PERMANENT
                    if fd_article.get('type') == FreshArticleType.WORKAROUND:
                        typ = FreshArticleType.WORKAROUND

                    article = uf.UbeeFreshArticle(
                        title=fd_article.get('title'),
                        desc=fd_article.get('description'),
                        parent=folder,
                        fd_id=fd_article.get('id'),
                        fd_status=status,
                        fd_type=typ
                    )

                    folder.add_article(article)

                    article_translations = self.get_article_translations(article.fd_id)

                    if len(article_translations) > 0 and verbosity > 3:
                        print('          - trans: {}'.format(', '.join(folder_translations.keys())))

                    for lang, translation in article_translations.items():
                        status = FreshStatus.PUBLISHED
                        if translation.get('status') == FreshStatus.DRAFT:
                            status = FreshStatus.DRAFT

                        typ = FreshArticleType.PERMANENT
                        if translation.get('type') == FreshArticleType.WORKAROUND:
                            typ = FreshArticleType.WORKAROUND

                        article.add_translation(
                            lang=lang,
                            translation=uf.UbeeFreshArticle(
                                title=translation.get('title'),
                                desc=translation.get('description'),
                                parent=article,
                                fd_id=translation.get('id'),
                                fd_status=status,
                                fd_type=typ
                            )
                        )

        return portal
