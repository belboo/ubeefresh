import freshdesk.ubeefresh.sheets as ufsheets

LANG_LIST = ['en', 'fr', 'de', 'it', 'es', 'ca']

GSID_FR = '1Ds7qctpBkRgrOaGJojrOuZSYNCoejTuG2ocRuUyjoGs'

sheet_fr = ufsheets.UbeeSheetsWorkbook().fetch_data(GSID_FR)

print(sheet_fr)

for sheet in sheet_fr.sheets:
    print('-' * 50)
    print(sheet)
