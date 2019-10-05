import string
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/drive']

CREDENTIALS_FILE = 'path/to/gapps_credentials.json'

class UbeeSheet:

    def __init__(self,
                 name: str = None,
                 data: list = None,
                 parent: 'UbeeSheetsWorkbook' = None):

        self.name = name
        if isinstance(data, list):
            self.data = data

        self.parent = parent

    def __str__(self):
        desc = 'UbeeSheet "{}"'.format(self.name)
        desc += '\n dims: ' + '{}, {}'.format(self.w, self.h) if self.data is not None else 'empty'
        desc += '\n parent gsid: {}'.format(self.parent.gsid) if self.parent is not None else ''

        return desc

    def __repr__(self):
        desc = '<UbeeSheet "{}"'.format(self.name)
        desc += ' ({}x{})'.format(self.w, self.h) if self.data is not None else' empty'
        desc += ' @ {}'.format(self.parent.gsid) if self.parent is not None else ''
        desc += '>'

        return desc

    @property
    def h(self):
        return len(self.data)

    @property
    def w(self):
        return max([len(r) for r in self.data])

    __aton = {c: i for i, c in enumerate(string.ascii_lowercase)}

    def cell(self, i, j) -> str:
        if self.data is None or j >= len(self.data):
            return None

        if isinstance(i, str):
            i = self.__aton.get(i[0].lower(), None)

        if i is None or i >= len(self.data[j]):
            return None

        return self.data[j][i]


class UbeeSheetsWorkbook:
    def __init__(self,
                 gsid: str = None,
                 sheets: list = None):

        self.gsid = gsid

        if sheets is not None and isinstance(sheets, list):
            self.sheets = sheets
            self.__sheet_name_map = {sheet.name: i for i, sheet in enumerate(sheets)
                                     if isinstance(sheet, UbeeSheet)
                                     and sheet.name is not None}
        else:
            self.sheets = list()
            self.__sheet_name_map = dict()

    def __str__(self):
        desc = 'UbeeSheetsWorkbook'

        if self.gsid is None and len(self.sheets) == 0:
            return desc + ' - Empty'

        desc += '\n gsid: {}'.format(self.gsid) if self.gsid is not None else 'none'

        if len(self.sheets) > 0:
            desc += '\n sheets:'
            for sheet in self.sheets:
                desc += '\n - {}'.format(sheet.name if sheet.name is not None else 'unnamed')

        return desc

    def __repr__(self):
        desc = '<UbeeSheet "{name}"'
        desc += ' ({}x{})'.format(self.w, self.h) if self.data is not None else' empty'
        desc += ' @ {}'.format(self.parent.gsid) if self.parent is not None else ''
        desc += '>'

        return desc

    def add_sheet(self, sheet):
        if not isinstance(sheet, UbeeSheet):
            raise TypeError('Can only add UbeeSheet-s')

        if sheet.name in self.__sheet_name_map:
            raise IndexError('Sheet with this name already exists. Use replace to replace/update')

        self.sheets.append(sheet)
        self.__sheet_name_map[sheet.name] = len(self.sheets)

    def fetch_data(self, gsid: str = None, sheets: list = None, sheet_ids: list = None):

        if self.gsid is None and gsid is None:
            raise ValueError('ID of the workbook must either be set in the object or be supplied here')

        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
        gc = gspread.authorize(credentials)

        ob = gc.open_by_key(gsid)

        sheet_list = ob.worksheets()

        if sheet_ids is None:
            sheet_ids = []

        if sheets is None:
            sheets = []

        self.gsid = gsid

        for i, sheet in enumerate(sheet_list):
            if sheet.title in sheets or i in sheet_ids:
                continue

            self.sheets.append(UbeeSheet(
                name=sheet.title,
                data=sheet.get_all_values(),
                parent=self
            ))

        return self
