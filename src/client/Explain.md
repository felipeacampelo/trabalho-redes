# P2P Chat Client

Cliente de chat peer-to-peer implementado em Python conforme especificação do trabalho de Redes de Computadores.

## Características

- **Registro no Rendezvous**: Registra-se automaticamente no servidor Rendezvous
- **Descoberta de Peers**: Descobre outros peers de forma automática e periódica
- **Conexões TCP Persistentes**: Mantém conexões diretas com outros peers
- **Protocolo P2P Completo**: Implementa HELLO, PING/PONG, SEND/ACK, PUB, BYE/BYE_OK
- **Keep-alive**: Mantém conexões ativas com PING/PONG periódicos
- **Reconexão Automática**: Tenta reconectar com peers desconectados usando backoff exponencial
- **Interface CLI**: Interface de linha de comando interativa

## Requisitos

- Python 3.7+
- Nenhuma dependência externa (usa apenas biblioteca padrão)

## Instalação

```bash
cd src/client
```

## Configuração

Edite o arquivo `config.json` para configurar:

```json
{
  "rendezvous": {
    "host": "pyp2p.mfcaetano.cc",
    "port": 8080
  },
  "peer": {
    "namespace": "CIC",
    "name": "peer1",
    "port": 4000
  },
  "connection": {
    "max_reconnect_attempts": 5,
    "reconnect_backoff_base": 2,
    "reconnect_backoff_max": 60,
    "ping_interval": 30,
    "ack_timeout": 5,
    "discovery_interval": 60
  },
  "logging": {
    "level": "INFO",
    "file": "p2p_client.log"
  }
}
```

## Uso

### Iniciar o cliente

```bash
python3 main.py
```

### Com argumentos de linha de comando

```bash
python3 main.py --namespace UnB --name alice --port 4001
```

### Comandos disponíveis

| Comando | Descrição |
|---------|-----------|
| `/peers [* \| #namespace]` | Descobrir e listar peers |
| `/msg <peer_id> <mensagem>` | Enviar mensagem direta |
| `/pub * <mensagem>` | Broadcast para todos os peers |
| `/pub #<namespace> <mensagem>` | Enviar para todos do namespace |
| `/conn` | Mostrar conexões ativas |
| `/rtt` | Exibir estatísticas de RTT |
| `/reconnect` | Forçar reconexão com peers desconectados |
| `/log <LEVEL>` | Ajustar nível de log (DEBUG, INFO, WARNING, ERROR) |
| `/quit` | Encerrar aplicação |
| `/help` | Mostrar ajuda |

## Exemplos de Uso

### Descobrir peers

```
/peers *
/peers #CIC
```

### Enviar mensagem direta

```
/msg alice@CIC Olá, como vai?
```

### Broadcast

```
/pub * Mensagem para todos!
/pub #CIC Mensagem para o namespace CIC
```

### Ver conexões ativas

```
/conn
```

### Ver estatísticas de RTT

```
/rtt
```

## Arquitetura

O cliente é organizado em módulos:

- **`main.py`** - Ponto de entrada da aplicação
- **`p2p_client.py`** - Lógica principal do cliente P2P
- **`models.py`** - Modelos de dados (PeerInfo, Message, etc.)
- **`state.py`** - Gerenciamento de estado thread-safe
- **`rendezvous_connection.py`** - Comunicação com servidor Rendezvous
- **`peer_connection.py`** - Gerenciamento de conexões TCP com peers
- **`peer_table.py`** - Tabela de peers e lógica de reconexão
- **`message_router.py`** - Roteamento de mensagens (SEND, PUB)
- **`keep_alive.py`** - Mecanismo de keep-alive (PING/PONG)
- **`cli.py`** - Interface de linha de comando

## Protocolo

### Handshake (HELLO/HELLO_OK)

Ao conectar com um peer, o cliente envia HELLO e aguarda HELLO_OK:

```json
{"type": "HELLO", "peer_id": "alice@CIC", "version": "1.0", "features": ["ack", "metrics"], "ttl": 1}
{"type": "HELLO_OK", "peer_id": "bob@CIC", "version": "1.0", "features": ["ack", "metrics"], "ttl": 1}
```

### Keep-alive (PING/PONG)

Envia PING periodicamente e aguarda PONG:

```json
{"type": "PING", "msg_id": "uuid", "timestamp": "2025-10-27T10:00:00Z", "ttl": 1}
{"type": "PONG", "msg_id": "uuid", "timestamp": "2025-10-27T10:00:00Z", "ttl": 1}
```

### Mensagem Direta (SEND/ACK)

```json
{"type": "SEND", "msg_id": "uuid", "src": "alice@CIC", "dst": "bob@CIC", "payload": "Olá!", "require_ack": true, "ttl": 1}
{"type": "ACK", "msg_id": "uuid", "timestamp": "2025-10-27T10:00:01Z", "ttl": 1}
```

### Broadcast (PUB)

```json
{"type": "PUB", "msg_id": "uuid", "src": "alice@CIC", "dst": "*", "payload": "Mensagem global", "require_ack": false, "ttl": 1}
```

### Encerramento (BYE/BYE_OK)

```json
{"type": "BYE", "msg_id": "uuid", "src": "alice@CIC", "dst": "bob@CIC", "reason": "Encerrando", "ttl": 1}
{"type": "BYE_OK", "msg_id": "uuid", "src": "bob@CIC", "dst": "alice@CIC", "ttl": 1}
```

## Logs

Os logs são salvos em `p2p_client.log` (configurável) e incluem:

- Eventos de conexão/desconexão
- Mensagens enviadas/recebidas
- Estatísticas de RTT
- Erros e avisos

## Testes

Para testar, inicie múltiplas instâncias do cliente em portas diferentes:

```bash
# Terminal 1
python3 main.py --name alice --port 4001

# Terminal 2
python3 main.py --name bob --port 4002

# Terminal 3
python3 main.py --name charlie --port 4003
```

## Observabilidade

O cliente implementa logging detalhado de todos os eventos:

```
[PeerServer] Inbound connected: alice@CIC
[Router] SEND bob@CIC: oi!
[KeepAlive] PONG from bob@CIC, RTT: 43.2 ms
[Discovery] Found 3 peers
```

## Limitações

- Conexões diretas apenas (sem relay)
- TTL fixo em 1 (não decrementa)
- Mensagens limitadas a 32 KiB
- Não implementa criptografia

## Autor

Desenvolvido para a disciplina CIC0124 - Redes de Computadores, UnB.
