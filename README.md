<h1 align="center">
  <a href="https://github.com/confy-security/server" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="https://github.com/confy-security/assets/blob/main/img/confy-app-icon.png?raw=true">
    </picture>
  </a>
  <br>
  Confy Server
</h1>

<p align="center">Servidor de back-end para o sistema Confy de comunicação criptografada.</p>

<div align="center">

[![GitHub License](https://img.shields.io/github/license/confy-security/server?color=blue
)](/LICENSE)
[![Visitors](https://api.visitorbadge.io/api/visitors?path=confy-security%2Fserver&label=repository%20visits&countColor=%231182c3&style=flat)](https://github.com/confy-security/server)
  
</div>

---

Este é um servidor de comunicação em tempo real, desenvolvido com FastAPI e WebSockets,
projetado para possibilitar a troca de mensagens de ponta a ponta entre os clientes que se conetam ao servidor.
Ele atua como m intermediário seguro entre os clientes, gerenciando conexões e encaminhando mensagens
sem acesso ao conteúdo e sem armazenamento local, preservando a privacidade.
Os aplicativos clientes por sua vez enviam as mensagens criptografadas com AES,
e a descriptografia só é feita quando a mensagem no cliente de destino.
Mesmo que alguma comunicação seja interceptada na rede, ela é ilegível.

## Executando o servidor

### Via Docker (recomendado)

A maneira mais rápida e fácil de executar o servidor é com um container [Docker](https://www.docker.com/).

```shell
docker run -d --restart=always -p 8000:8000 --name confy-server henriquesebastiao/confy-server:latest
```

O servidor Confy agora está rodando em [http://0.0.0.0:8000](http://0.0.0.0:8000).

### Localmente

Caso queira executar o servidor sem Docker para fins de debug ou desenvolvimento siga as etapas abaixo.

1. Tenha instalado as seguintes dependências:

    - [Git](https://git-scm.com/downloads)
    - [Poetry](https://python-poetry.org/docs/#installation)
    - [Python 3.13 ou superior](https://www.python.org/downloads/)

2. Clone este repositório e entre na pasta.

    ```shell
    git clone https://github.com/confy-security/server.git && cd server
    ```

3. Instale as dependência do servidor com Poetry.

    ```shell
    poetry install
    ```

4. Ative o ambiente virtual.

5. Execute o servidor.

    ```shell
    task run
    ```

Pronto, agora o servidor Confy agora está rodando em [http://0.0.0.0:8000](http://0.0.0.0:8000).

## License

Este projeto está licenciado sob os termos da licença GNU GPL-3.0.
