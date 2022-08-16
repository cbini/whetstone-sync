# whetstone-sync

## Getting started

1. Ensure you have Python 3.6+ installed
2. Create and activate a virtual environment
3. Fork this repository
4. Install `requirements.txt` with `pip`
5. Create a `.env` file containing the following variables:

```env
WHETSTONE_DISTRICT_ID=my-d157r1c7-1d
WHETSTONE_CLIENT_ID=my-cl13n7-1d
WHETSTONE_CLIENT_SECRET=my-cl13n7-53cr37
WHETSTONE_USERNAME=username@myschool.org
WHETSTONE_PASSWORD=myp455w0rd
GCS_BUCKET_NAME=my-bucket-name
WHETSTONE_IMPORT_FILE=/path/to/whetstone_users.json
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gapps_creds.json
LOCAL_TIMEZONE=MY/Timezone
```
