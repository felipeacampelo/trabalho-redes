# Quick Start Guide - P2P Chat Client

## Início Rápido

### 1. Navegue até o diretório do cliente

```bash
cd /Users/felipecampelo/pyp2p-rdv/src/client
```

### 2. Configure seu peer

Edite `config.json` e altere o nome do peer:

```json
{
  "peer": {
    "namespace": "CIC",
    "name": "SEU_NOME_AQUI",  // Altere aqui!
    "port": 4000
  }
}
```

### 3. Inicie o cliente

```bash
python3 main.py
```

Ou com argumentos:

```bash
python3 main.py --name alice --port 4001
```

### 4. Comandos Básicos

Após iniciar, você verá o prompt. Digite os comandos:

#### Descobrir peers
```
/peers *
```

#### Enviar mensagem direta
```
/msg bob@CIC Olá Bob!
```

#### Broadcast para todos
```
/pub * Mensagem para todos!
```

#### Ver conexões ativas
```
/conn
```

#### Ver estatísticas de RTT
```
/rtt
```

#### Sair
```
/quit
```

## Teste com Múltiplos Peers

### Opção 1: Manualmente

Abra 3 terminais e execute:

**Terminal 1:**
```bash
python3 main.py --name alice --port 4001
```

**Terminal 2:**
```bash
python3 main.py --name bob --port 4002
```

**Terminal 3:**
```bash
python3 main.py --name charlie --port 4003
```

### Opção 2: Script Automático

```bash
./test_client.sh
```

## Cenários de Teste

### Teste 1: Conexão Direta

1. Inicie dois peers (alice e bob)
2. Em alice: `/peers *` - deve ver bob
3. Em alice: `/msg bob@CIC Olá!`
4. Bob deve receber a mensagem

### Teste 2: Broadcast

1. Inicie três peers (alice, bob, charlie)
2. Em alice: `/pub * Mensagem para todos`
3. Bob e charlie devem receber

### Teste 3: Namespace-cast

1. Inicie peers em namespaces diferentes
2. Use `/pub #CIC Mensagem para CIC`
3. Apenas peers do namespace CIC recebem

### Teste 4: Keep-alive

1. Inicie dois peers
2. Aguarde 30 segundos
3. Use `/rtt` para ver estatísticas de PING/PONG

### Teste 5: Reconexão

1. Inicie alice e bob
2. Encerre bob com Ctrl+C
3. Reinicie bob
4. Alice deve reconectar automaticamente

### Teste 6: Encerramento Limpo

1. Inicie dois peers
2. Use `/quit` em um deles
3. O outro deve receber BYE e fechar a conexão

## Troubleshooting

### Porta já em uso

```
Error: Failed to start peer server
```

**Solução:** Use uma porta diferente:
```bash
python3 main.py --port 4005
```

### Não consegue conectar ao Rendezvous

```
Error: Failed to register with Rendezvous server
```

**Solução:** Verifique:
1. Conexão com internet
2. Servidor Rendezvous está online (pyp2p.mfcaetano.cc:8080)
3. Firewall não está bloqueando

### Peers não se conectam

```
Failed to connect to bob@CIC
```

**Solução:**
1. Verifique se ambos estão registrados: `/peers *`
2. Verifique firewall local
3. Se em redes diferentes, pode haver NAT bloqueando

### Ver logs detalhados

```
/log DEBUG
```

Ou edite `config.json`:
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## Estrutura de Arquivos

```
client/
├── main.py                    # Ponto de entrada
├── p2p_client.py             # Cliente principal
├── models.py                 # Modelos de dados
├── state.py                  # Gerenciamento de estado
├── rendezvous_connection.py  # Conexão com Rendezvous
├── peer_connection.py        # Conexões P2P
├── peer_table.py             # Tabela de peers
├── message_router.py         # Roteamento de mensagens
├── keep_alive.py             # Keep-alive (PING/PONG)
├── cli.py                    # Interface CLI
├── config.json               # Configuração
├── README.md                 # Documentação completa
├── QUICKSTART.md             # Este arquivo
└── test_client.sh            # Script de teste
```

## Próximos Passos

1. Leia o README.md completo para entender a arquitetura
2. Revise a especificação em `../docs/RC202502 - PyP2p - Especificacao Trabalho.md`
3. Experimente todos os comandos
4. Teste os cenários de teste mínimos
5. Verifique os logs para entender o funcionamento

## Suporte

Para dúvidas sobre o protocolo, consulte:
- README.md do projeto
- Especificação do trabalho
- Documentação do servidor Rendezvous: https://github.com/mfcaetano/pyp2p-rdv
