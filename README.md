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

A maneira mais rápida e fácil de executar o servidor é via docker compose.

1. Clone este repositório e entre na pasta do projeto.

    ```shell
    git clone https://github.com/confy-security/server.git && cd server
    ```

2. Execute o docker compose.

    ```shell
    docker compose up -d
    ```

O servidor Confy agora está rodando em [http://0.0.0.0:9000](http://0.0.0.0:9000).

## Licença

Este projeto está licenciado sob os termos da licença GNU GPL-3.0.
