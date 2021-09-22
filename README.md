# DATA GUN

* Create virtualenv and save name to `.python_version` file
* `poetry install --no-dev`
* Install `qgtunnel`:
    ```
    curl https://s3.amazonaws.com/quotaguard/qgtunnel-latest.tar.gz | tar xz
    ```
* Set QuotaGuard URL to QUOTAGUARDSTATIC_URL variable in `secrets.bash`
* Save `.qgtunnel` config file to project folder
* Create `.env`
