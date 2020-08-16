# SJTU Schedule Exporter Backend

This is the backend of [SJTU Schedule Exporter](https://github.com/PhotonQuantum/sjtu-schedule-exporter).

> Notice:
>
> This project uses the async version of pysjtu, which can be found at [pysjtu:async](https://github.com/PhotonQuantum/pysjtu/tree/async).

## Get Started

To run this backend, you need to have a running redis instance.

``` shell script
$ pip install -r requirements.txt
$ uvicorn --host 0.0.0.0 --port 8000 sjtu_scheduler_exporter_backend:app
```