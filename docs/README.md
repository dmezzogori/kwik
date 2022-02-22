# Handbook Firmville

## Setup

### Development

_setup da sviluppo, con hot-reloading abilitato_

* avviare lo stack utilizzando

  ```sh
  docker-compose up -d
  ```
* per accedere al servizio, puntare a:
  ```sh
  http://localhost:8000
  ```
* per monitorare i log:
  ```sh
  docker-compose logs -f handbook
  ```
  
### Production/Staging

_N.B.: da utilizzare in ambiente con Traefik frontale_

* valorizzare variabile `DOMAIN` nel file `.env`
* avviare lo stack utilizzando

  ```sh
  docker-compose up -d
  ```
* per accedere al servizio, puntare a:
  ```sh
  https://handbook.<<DOMAIN>>
  ```
* per monitorare i log:
  ```sh
  docker-compose logs -f handbook
  ```
