# Freshdesk API and Google Sheets Adapter...

Performs most generic knowledge-base related API functions.

Furthermore is able to read [formatted spreadsheets](https://docs.google.com/spreadsheets/d/1HIwOpt__KVdR_9yJbqChMP6UBsUpS9GV3Y6N5D8oUcE/edit?usp=sharing) and parse them into Freshdesk DOM with subsequent upload possibility.

## Read GS and upload Example

```python
import freshdesk.ubeefresh.ubeefresh as ufd
import freshdesk.ubeefresh.api as ufdapi

GSID = 'yourGoogleSheetID'
YOUR_PORTAL_ID = 10293847465

portal = ufd.UbeeFreshPortal.from_gs(GSID, name='Portal Name')

print(portal)

fd = ufdapi.UbeeFreshAPI(portals=[YOUR_PORTAL_ID])

for cat in portal.categories[1:]:
    fd.create_category(category=cat, create_folders=True, create_translations=True)
    cat.update_in_gs()

for cat in portal.categories:
    print(cat.name, cat.fd_id)
```

# Read Freshdesk Knowledge Base and save locally / backup:

```python
import freshdesk.ubeefresh.ubeefresh as ufd
import freshdesk.ubeefresh.api as ufdapi

GSID = 'yourGoogleSheetID'
YOUR_PORTAL_ID = 10293847465

# Read
portal = ua.UbeeFreshAPI().read_portal('Portal Name')

# Save
portal.save('backup.p')

# Load

p1 = uf.UbeeFreshPortal.load('backup.p')
```
