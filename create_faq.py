
# coding: utf-8

# In[1]:


import freshdesk.ubeefresh.ubeefresh as ufd
import freshdesk.ubeefresh.api as ufdapi


# In[2]:


GSID = 'yourGoogleSheetID'


# In[3]:


portal = ufd.UbeeFreshPortal.from_gs(GSID_FR, name='Portal Name')

print(portal)


# In[4]:


portal.fd_suffix = 'France'


# In[5]:


cat = portal.categories[0]


# In[6]:


print(cat)


# # Create Categories Online

# In[7]:


fd = ufdapi.UbeeFreshAPI(portals=[44000126561]) 


# In[13]:


for cat in portal.categories[1:]:
    fd.create_category(category=cat, create_folders=True, create_translations=True)
    cat.update_in_gs()


# In[14]:


for cat in portal.categories:
    print(cat.name, cat.fd_id)


# # Backup Online Contents

# In[8]:


portal = ua.UbeeFreshAPI().read_portal('Ubeeqo Support')


# In[7]:


portal.save('backup.p')


# In[8]:


p1 = uf.UbeeFreshPortal.load('backup.p')


# # GSpread Checks

# In[20]:


import gspread
from gspread.utils import rowcol_to_a1
from oauth2client.service_account import ServiceAccountCredentials

scopes = ['https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/drive']

credentials_file = '/tmp/gapps_credentials.json'

credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scopes)
gc = gspread.authorize(credentials)


# In[29]:


c = portal.categories[0]


# In[30]:


c.gs_id


# In[31]:


wb = gc.open_by_key(c.gs_id)
cat_sheet = wb.worksheet(c.gs_sheet)
cell = cat_sheet.acell(c.gs_range)


# In[32]:


c.gs_range


# In[40]:


fdc = cat_sheet.cell(cell.row, cell.col+1)


# In[42]:


fdc.value = '123-456'


# In[44]:


cat_sheet.update_cell(cell.row, cell.col+1, '123-456')


# In[35]:


cell.value == c.name

