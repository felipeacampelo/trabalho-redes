# Trabalho de Programação — **Chat P2P**

# Sumário

- [Trabalho de Programação — **Chat P2P**](#trabalho-de-programação--chat-p2p)
- [Sumário](#sumário)
  - [Resumo](#resumo)
  - [Arquitetura P2P: Conceitos, Características e Atuadores](#arquitetura-p2p-conceitos-características-e-atuadores)
    - [Características Principais](#características-principais)
    - [Atores em Uma Redes P2P](#atores-em-uma-redes-p2p)
    - [Considerações Finais](#considerações-finais)
  - [1) Objetivos](#1-objetivos)
  - [2) Identidade, nomes e escopo](#2-identidade-nomes-e-escopo)
  - [3) Transporte, codificação e limites](#3-transporte-codificação-e-limites)
  - [4) Integração com o Servidor Rendezvous](#4-integração-com-o-servidor-rendezvous)
    - [4.1 `REGISTER` (peer → rendezvous)](#41-register-peer--rendezvous)
    - [4.2 `DISCOVER` (peer → rendezvous)](#42-discover-peer--rendezvous)
    - [4.3 `UNREGISTER` (peer → rendezvous)](#43-unregister-peer--rendezvous)
  - [5) Conexões entre peers](#5-conexões-entre-peers)
    - [Ideia geral do protocolo](#ideia-geral-do-protocolo)
    - [Mensagens de Handshake (`HELLO` / `HELLO_OK`)](#mensagens-de-handshake-hello--hello_ok)
    - [Mensagens de Keep-alive (`PING` / `PONG`)](#mensagens-de-keep-alive-ping--pong)
    - [Encerramento de sessão com `BYE`](#encerramento-de-sessão-com-bye)
  - [6) Mensagens e roteamento (relay P2P)](#6-mensagens-e-roteamento-relay-p2p)
    - [Mensagens unicast (`SEND`)](#mensagens-unicast-send)
      - [Confirmação de entrega com `ACK`](#confirmação-de-entrega-com-ack)
      - [Geração de `msg_id`](#geração-de-msg_id)
    - [Mensagens de publicação (`PUB`)](#mensagens-de-publicação-pub)
    - [Descoberta de rotas com `WHO_HAS` / `WHO_HAS_HIT`](#descoberta-de-rotas-com-who_has--who_has_hit)
    - [Encaminhamento com `relay`](#encaminhamento-com-relay)
    - [Métricas com `metrics`](#métricas-com-metrics)
  - [7) Tratamento de erros](#7-tratamento-de-erros)
  - [8) Interface de usuário (CLI)](#8-interface-de-usuário-cli)
  - [9) Arquitetura (sugestão de módulos)](#9-arquitetura-sugestão-de-módulos)
  - [10) Observabilidade (mínimo)](#10-observabilidade-mínimo)
  - [11) Critérios de correção (funcional)](#11-critérios-de-correção-funcional)
  - [12) Cenários mínimos de teste](#12-cenários-mínimos-de-teste)
  - [13) Checklist de funcionalidades (para o aluno)](#13-checklist-de-funcionalidades-para-o-aluno)
    - [Apêndice — Protocolo de Aplicação do Servidor Rendezvous](#apêndice--protocolo-de-aplicação-do-servidor-rendezvous)
      - [Visão Geral](#visão-geral)
      - [Formato das mensagens](#formato-das-mensagens)
      - [Comandos aceitos](#comandos-aceitos)
        - [1. `REGISTER`](#1-register)
        - [2. `DISCOVER`](#2-discover)
        - [3. `UNREGISTER`](#3-unregister)
        - [4. Mensagens de Erro Genéricas](#4-mensagens-de-erro-genéricas)
      - [Resumo do Ciclo de Uso](#resumo-do-ciclo-de-uso)

---

## Resumo

> Este trabalho tem como objetivo proporcionar ao aluno o desenvolvimento de conceitos relacionados à arquitetura distribuída de comunicação P2P. Para isso, o aluno deverá implementar uma aplicação cliente de **Chat P2P** que se registra em um **Servidor Rendezvous**, descobre peers, mantém **conexões TCP persistentes (keep-alive)** com peers acessíveis e, quando não houver caminho direto (por exemplo, devido a NAT), **encaminha mensagens por meio de outros peers** (relay P2P).  
> O professor disponibilizou um servidor Rendezvous operacional, acessível online, que implementa o protocolo de aplicação para interação com rendezvous descrito neste documento. Esse servidor deve ser utilizado para registrar peers e obter informações sobre as redes P2P existentes. Ressalta-se que o servidor Rendezvous **não exerce papéis especiais**: sua função é exclusivamente registrar e listar peers. **Qualquer peer acessível pode atuar como relay**.


## Arquitetura P2P: Conceitos, Características e Atuadores

A **arquitetura peer-to-peer (P2P)** constitui um modelo de comunicação distribuída no qual cada nó da rede, denominado *peer*, exerce simultaneamente as funções de cliente e servidor. Diferentemente do paradigma cliente-servidor, em que existe uma entidade central responsável por fornecer serviços, no modelo P2P a interação ocorre de forma descentralizada, com múltiplos pontos de origem e destino. Esse modelo tornou-se amplamente utilizado em aplicações de compartilhamento de arquivos, redes de sobreposição (*overlay networks*), sistemas de mensageria e ambientes colaborativos.

### Características Principais

1. **Descentralização**  
   A inexistência de uma autoridade central reduz o risco de ponto único de falha e distribui a responsabilidade entre os peers. Essa característica aumenta a autonomia da rede e dificulta a censura ou controle centralizado.

2. **Escalabilidade**  
   O aumento no número de participantes contribui positivamente para a capacidade global da rede. Cada peer adicional introduz novos recursos de conectividade e processamento, tornando o sistema naturalmente escalável.

3. **Resiliência**  
   A arquitetura P2P é intrinsecamente tolerante a falhas. A saída de um peer não compromete o funcionamento da rede, uma vez que outros peers podem assumir o encaminhamento ou a redistribuição dos recursos.

4. **Distribuição de Recursos**  
   Dados e serviços são fragmentados e replicados entre diferentes peers. Esse mecanismo evita sobrecarga em um único ponto e promove redundância, o que contribui para maior disponibilidade e desempenho.

5. **Heterogeneidade**  
   Os peers podem apresentar capacidades heterogêneas em termos de largura de banda, poder de processamento e tempo de disponibilidade. Apesar disso, todos podem colaborar de acordo com suas possibilidades, reforçando a flexibilidade do modelo.

6. **Dinamicidade**  
   A rede P2P é marcada por intensa variação na participação dos peers (*churn*). Protocolos e aplicações P2P devem, portanto, lidar com a entrada e saída frequente de nós, preservando a consistência e a utilidade da rede.

### Atores em Uma Redes P2P

No contexto da arquitetura P2P, os atuadores correspondem aos papéis ou funções desempenhadas pelos peers para sustentar o funcionamento da rede:

1. **Peers de Origem e Destino**  
   Responsáveis pela emissão e recepção final de mensagens ou dados. Em um sistema de chat, por exemplo, representam os usuários que trocam mensagens diretamente.

2. **Peers de Encaminhamento (*Relay Peers*)**  
   Fundamentais quando não existe rota direta entre origem e destino, especialmente em cenários com NAT ou firewalls. Esses peers atuam como nós de encaminhamento na camada de aplicação, propagando mensagens até o destino.

3. **Peers de Descoberta**  
   Participam dos mecanismos de identificação e localização de outros nós. No trabalho proposto, **servidor Rendezvous** é o "ponto de encontro" inicial dos peers, responsável por registrar e listar peers ativos. Posteriormente, a descoberta passa a ser descentralizada via mensagens de controle do tipo `WHO_HAS`.

4. **Peers de Observabilidade**  
   Monitoram o estado da rede, incluindo métricas como tempo de resposta (RTT), disponibilidade de rotas e falhas de encaminhamento. Essas informações auxiliam na tomada de decisão sobre o roteamento de mensagens.

### Considerações Finais

A arquitetura P2P representa um paradigma **colaborativo, escalável e resiliente**, no qual cada peer pode assumir diferentes papéis de acordo com sua posição e conectividade na rede. Para que esse modelo funcione de maneira eficiente, é necessário o suporte a mecanismos de **descoberta de peers, encaminhamento de mensagens, tolerância a falhas e atualização dinâmica da topologia**.  

No contexto deste trabalho de programação, a implementação de um cliente P2P permitirá ao estudante vivenciar esses conceitos na prática, ao interagir com o servidor Rendezvous, estabelecer conexões diretas, desempenhar o papel de relay quando necessário e encaminhar mensagens respeitando restrições de tempo de vida (*time-to-live*, TTL) e deduplicação.



---

## 1) Objetivos

O objetivo geral deste trabalho é exercitar conceitos de **arquitetura P2P**, **protocolos de aplicação** e **roteamento na camada de aplicação**.  Sendo assim, a implementação do **cliente P2P** deverá oferecer, no mínimo, as seguintes funcionalidades:

1. **Interface de interação (CLI, TUI ou GUI simples)**  
   - Permitir a entrada de comandos e a visualização de eventos (mensagens recebidas, status da rede, métricas).

2. **Integração com o servidor Rendezvous**  
   - Implementar os comandos de **REGISTER**, **DISCOVER** e **UNREGISTER**, de acordo com o protocolo definido.  
   - Manter a consistência do registro durante a execução do cliente.

3. **Gerenciamento de conexões entre peers**  
   - Estabelecer e manter **túneis TCP persistentes** com peers descobertos e acessíveis.  
   - Detectar falhas de conexão (timeout, peer inativo) e realizar tentativa de recuperação.

4. **Comunicação entre peers**  
   - **Unicast**: envio/recebimento de mensagens ponto a ponto.  
   - **Namespace-cast**: envio/recebimento de mensagens a todos os peers de um mesmo namespace.  
   - **Broadcast global**: envio/recebimento de mensagens para todos os peers registrados.

5. **Encaminhamento (Relay P2P)**  
   - Atuar como nó intermediário quando um peer não for acessível diretamente, mas mantiver conexão ativa com você.  
   - Encaminhar mensagens de forma transparente, respeitando TTL e deduplicação.

6. **Observabilidade e diagnósticos**  
   - Exibir informações básicas de operação:  
     - Peers conectados (vizinhos).  
     - Rotas conhecidas (diretas e indiretas).  
     - Métricas de latência (RTT) e erros de comunicação.  
   - Oferecer comandos mínimos de depuração (ex.: `show peers`, `show routes`, `ping <peer>`).

---

## 2) Identidade, nomes e escopo

- **namespace**: agrupador lógico (ex.: `UnB`, `CIC`).
- **name**: identificador único dentro do namespace.
- **peer_id** = `name@namespace` (ex.: `alice@UnB`).  
  > Nota: o Rendezvous **não retorna peer_id diretamente**; o cliente deve compor a string usando `name@namespace`.
- **Escopos de envio**:
  - **Unicast**: para um `peer_id` específico.
  - **Namespace-cast**: para todos do `#namespace`.
  - **Broadcast global**: para `*` (todos os peers conhecidos).

---

## 3) Transporte, codificação e limites

- **Transporte entre peers**: TCP (TLS recomendado).
- **Codificação**: **JSON UTF-8**, **delimitado por `\n`** (uma mensagem por linha).
- **Tamanho máximo por mensagem**: **32 KiB** (32768 bytes).
  - Excedeu → responder `ERROR` com `error:"line_too_long"` e `limit:32768`.
- **Keep-alive**: `PING` a cada **30 s**; desconectar se **3 PINGs** sem `PONG`.
- **TTL obrigatório em todas as mensagens**: fixo em **1**.
  - Mensagens com `ttl <= 0` → descartar e responder `ERROR` com `error:"ttl_expired"`.
  
> **Atenção**: Este `ttl` refere-se ao campo obrigatório em todas as mensagens P2P. Não dever ser confundido com o `ttl` usado pelo servidor Rendezvous, que indica o tempo de vida do registro.

---

## 4) Integração com o Servidor Rendezvous

O Rendezvous apenas registra e lista peers (sem papéis especiais).  

### 4.1 `REGISTER` (peer → rendezvous)

**Exemplo de requisição:**
```json
{
  "type": "REGISTER",
  "namespace": "UnB",
  "name": "alice",
  "port": 7070,
  "ttl": 7200
}
```
> Campo `port` é obrigatório. 
 
> Campo `ttl` é opcional; se omitido, o servidor assume **7200 s** (2 horas).
> O campo `ttl` neste contexto refere-se ao tempo de vida do registro no servidor Rendezvous (em segundos), e não ao campo `ttl` das mensagens P2P, que é **fixo em 1** (salto).

**Exemplo de resposta:**
```json
{
  "status": "OK",
  "ttl": 7200,
  "observed_ip": "203.0.113.7",
  "observed_port": 45678
}
```
> O campo `peer_id` **não é retornado** pelo servidor, mas pode ser reconstruído pelo cliente como `name@namespace`.

### 4.2 `DISCOVER` (peer → rendezvous)

**Exemplo de requisição:**
```json
{ "type": "DISCOVER", "namespace": "UnB" }
```

**Exemplo de resposta:**
```json
{
  "status": "OK",
  "peers": [
    {
      "ip": "203.0.113.7",
      "port": 7070,
      "name": "alice",
      "namespace": "UnB",
      "ttl": 7200,
      "expires_in": 7199,
      "observed_ip": "203.0.113.7",
      "observed_port": 45678
    }
  ]
}
```

**Erros (`DISCOVER`)**  
> O servidor atual só retorna erros genéricos (`bad_namespace`, `invalid_json`, etc.).  
> Não há suporte a `rate_limited` ou `server_busy`.

### 4.3 `UNREGISTER` (peer → rendezvous)

**Exemplo de requisição:**
```json
{ "type": "UNREGISTER", "namespace": "UnB", "name": "alice", "port": 7070 }
```

**Exemplo de Resposta:**
```json
{ "status": "OK" }
```

---

## 5) Conexões entre peers

Além da interação com o **Servidor Rendezvous**, cada cliente deve implementar um **protocolo de aplicação P2P** para se comunicar diretamente com outros peers. Esse protocolo define como as conexões são estabelecidas, mantidas e utilizadas para troca de mensagens.

### Ideia geral do protocolo

- **Formato**: toda mensagem é um objeto **JSON UTF-8**, enviado em **uma linha** terminada por `\n`.  
- **Transporte**: utiliza conexões **TCP persistentes** (com possibilidade de TLS).  
- **Identificação**: cada peer é identificado por seu `peer_id` (`name@namespace`).  
- **Mensagens de controle**: permitem negociar a conexão (`HELLO`, `HELLO_OK`), manter o estado (`PING`/`PONG`) e encerrar sessões (`BYE`).  
- **Mensagens de dados**: utilizadas para envio de conteúdo (`SEND`, `PUB`) ou descoberta de rotas (`WHO_HAS`, `WHO_HAS_HIT`).  
- **Mensagens de erro**: padronizadas, sempre no formato `{"status":"ERROR", ...}`.  
- **TTL e deduplicação**: toda mensagem deve carregar explicitamente o campo `ttl: 1`, usado para deduplicação e permitindo no máximo um relay intermediário.

---

### Mensagens de Handshake (`HELLO` / `HELLO_OK`)

As mensagens **HELLO/HELLO_OK** são utilizadas na fase inicial da conexão entre dois peers. Seu objetivo é realizar o *handshake* de abertura, confirmando a identidade de cada participante, a versão do protocolo em uso e eventuais recursos opcionais disponíveis (como suporte a relay, ACKs ou TLS). Dessa forma, garantem que ambos os lados estão alinhados antes de iniciar a troca regular de mensagens.  


**Definição**

- **HELLO** (peer → peer): inicia a conexão.  
  - `type`: `"HELLO"`  
  - `peer_id`: identificador do peer (`name@namespace`)  
  - `version`: versão do protocolo P2P suportada  
  - `features`: lista de recursos opcionais (ex.: `relay`, `ack`, `who_has`, `metrics`)  

- **HELLO_OK** (peer → peer): resposta de aceitação.  
  - `type`: `"HELLO_OK"`  
  - `peer_id`: identificador de quem respondeu  
  - `version`: versão confirmada (a mesma ou compatível)  
  - `features`: recursos efetivamente habilitados  

**Exemplo de Requisição:**

```json
{ 
  "type": "HELLO", 
  "peer_id": "alice@UnB", 
  "version": "1.0", 
  "features": ["relay", "ack", "who_has", "metrics"],
  "ttl": 1
}
```

**Exemplo de resposta:**

```json
{ 
  "type": "HELLO_OK", 
  "peer_id": "bob@UnB", 
  "version": "1.0", 
  "features": ["relay", "metrics"],
  "ttl": 1
}
```

Um peer deve anunciar recursos no campo `features` da mensagem **HELLO**, que são confirmados ou ajustados na resposta **HELLO_OK**. **É obrigatória a implementação** dos seguintes recursos:

- **relay** → indica suporte a atuar como nó de encaminhamento (relay) para peers inacessíveis diretamente.  
- **ack** → indica suporte a confirmação de recebimento de mensagens unicast (`ACK`).  
- **who_has** → indica suporte à descoberta de rotas usando `WHO_HAS` / `WHO_HAS_HIT`.  
- **metrics** → indica suporte ao envio de métricas adicionais (ex.: RTT detalhado, taxa de entrega).  

> O campo `version` permite futuras evoluções do protocolo, garantindo compatibilidade entre diferentes implementações.

> A ausência de `features` ou uma lista vazia indica que o peer não oferece recursos adicionais além do básico.
 
> O handshake deve ser concluído antes do envio de qualquer outra mensagem. Se o peer remoto não responder com `HELLO_OK` em um prazo razoável (10 segundos), a conexão deve ser encerrada.

> Após o handshake, a conexão permanece aberta para troca de mensagens de controle e dados, conforme definido nas seções seguintes.


### Mensagens de Keep-alive (`PING` / `PONG`)

As mensagens **PING/PONG** são empregadas de forma periódica durante toda a duração da conexão. Elas atuam como mecanismo de *keep-alive*, assegurando que o peer remoto continua ativo e acessível, além de permitir a medição do tempo de resposta (RTT) e a detecção de falhas silenciosas (por exemplo, desconexões inesperadas por NAT ou queda de rede). Assim, enquanto o HELLO/HELLO_OK serve para iniciar a sessão, o PING/PONG mantém a sessão viva e monitorada.  


**Definição**

- **PING** (peer → peer): enviado periodicamente.  
  - `type`: `"PING"`  
  - `msg_id`: identificador único da mensagem  
  - `timestamp`: hora em que o PING foi enviado  

- **PONG** (peer → peer): resposta ao PING.  
  - `type`: `"PONG"`  
  - `msg_id`: mesmo identificador do PING recebido  
  - `timestamp`: hora em que o PONG foi gerado  

**Exemplo de requisição:**

```json
{ 
  "type": "PING", 
  "msg_id": "m12345", 
  "timestamp": "2025-09-21T10:30:00Z",
  "ttl": 1
}
```
**Exemplo de resposta:**

```json

{ 
  "type": "PONG", 
  "msg_id": "m12345", 
  "timestamp": "2025-09-21T10:30:01Z",
  "ttl": 1
}
```

### Encerramento de sessão com `BYE`

A mensagem **`BYE`** é utilizada para finalizar de forma explícita uma conexão P2P entre dois peers.  
Seu envio garante que o encerramento da sessão seja **limpo e controlado**, evitando timeouts desnecessários.

**Funcionamento:**

1. **Envio do BYE**  
   - Quando um peer deseja encerrar a conexão, ele envia uma mensagem do tipo `BYE` para o vizinho conectado.  
   - Essa mensagem informa o encerramento iminente e pode conter um motivo opcional.

2. **Recepção do BYE**  
   - Ao receber o `BYE`, o peer deve:  
     - Registrar nos logs o encerramento solicitado.  
     - Responder com uma mensagem de confirmação `BYE_OK`.  
     - Encerrar a conexão TCP e liberar os recursos associados a essa sessão.  

3. **Campos (`BYE`)**  
   - `type`: `"BYE"`  
   - `msg_id`: identificador único da mensagem  
   - `src`: peer que está encerrando a sessão  
   - `dst`: peer alvo do encerramento  
   - `reason`: (opcional) texto curto com o motivo do encerramento  
   - `ttl`: sempre **1**  

**Exemplo `BYE`**:

```json
{
  "type": "BYE",
  "msg_id": "m999",
  "src": "alice@UnB",
  "dst": "bob@UnB",
  "reason": "Encerrando sessão",
  "ttl": 1
}
```

**Exemplo `BYE_OK`**:
```json
{
  "type": "BYE_OK",
  "msg_id": "m999",
  "src": "bob@UnB",
  "dst": "alice@UnB",
  "ttl": 1
}
```

Cada conexão TCP deve aceitar múltiplas mensagens sequenciais, até que seja encerrada pelo usuário ou por falha de keep-alive.

---

## 6) Mensagens e roteamento (relay P2P)

Com objetivo de simplificar a implementação do trabalho, não iremos trabalhar com multiplos saltos. Ou seja, o campo **TTL será fixado em 1**, permitindo apenas **um relay intermediário**. O cliente deve implementar um **roteamento em nível de aplicação**, com as seguintes operações:  

- **Unicast (`SEND`)**: envio direto de uma mensagem a um `peer_id`. Exige confirmação (`ACK`).  
- **Namespace-cast (`PUB #namespace`)**: mensagem enviada a todos os peers de um namespace, com **TTL** e deduplicação.  
- **Broadcast global (`PUB *`)**: difusão a todos os peers conhecidos.  
- **Descoberta de rotas (`WHO_HAS` / `WHO_HAS_HIT`)**: mecanismo para identificar por qual vizinho uma rota até um destino é possível.  
- **Relay:** se o destino não for acessível diretamente, a mensagem pode ser encaminhada **por no máximo um peer intermediário (TTL = 1)**.
- **Deduplicação**: cada mensagem deve carregar um identificador único (`msg_id`), evitando loops ou duplicação.  

### Mensagens unicast (`SEND`)

As mensagens do tipo **`SEND`** são utilizadas para comunicação direta entre dois peers. Elas são a base para a **conversa na aplicação de chat**, permitindo que usuários troquem mensagens de texto em tempo real. Diferente do `PUB`, o envio unicast é sempre **um-para-um** e **exige confirmação de entrega**.

**Confirmação (`require_ack`)**

- Para `SEND`, o campo `"require_ack"` deve estar sempre presente e definido como `true`.  
- O destinatário é obrigado a responder com um `ACK` contendo o mesmo `msg_id`.  
- Caso o `ACK` não seja recebido dentro de um tempo limite, o emissor deve considerar a mensagem como não entregue.  

**Campos**  
- `type`: `"SEND"`
- `msg_id`: identificador único da mensagem  
- `src`: peer emissor  
- `dst`: peer destinatário (formato `name@namespace`)  
- `payload`: conteúdo da mensagem  
- `require_ack`: sempre `true`  
- `ttl`: sempre **1**, posicionado como último campo  

**Exemplo SEND**:

```json
{
  "type": "SEND",
  "msg_id": "m456",
  "src": "alice@UnB",
  "dst": "bob@UnB",
  "payload": "Olá Bob!",
  "require_ack": true,
  "ttl": 1
}
```

**Exemplo ACK**:

```json
{
  "type": "ACK",
  "msg_id": "m456",
  "from": "bob@UnB",
  "ttl": 1
}
```

#### Confirmação de entrega com `ACK`

A feature **`ack`** habilita a confirmação de entrega em mensagens **unicast**. Quando dois peers negociam suporte a `ack` no `HELLO/HELLO_OK`, cada mensagem enviada de forma direta (`SEND`) deve ser confirmada pelo destinatário com um `ACK`.  

**Funcionamento:**

1. O peer de origem envia uma mensagem `SEND` com um campo `msg_id` único.  
2. O peer de destino, ao receber e processar corretamente a mensagem, responde com um `ACK` que contém o mesmo `msg_id`.  
3. Se o peer de origem não receber o `ACK` dentro de um tempo limite, ele pode considerar a mensagem como **não entregue** e tentar retransmissão (dependendo da política adotada).  

**Exemplo `SEND` (com `ack` habilitado)**:

```json
{
  "type": "SEND",
  "msg_id": "m456",
  "src": "alice@UnB",
  "dst": "bob@UnB",
  "payload": "Olá Bob!",
  "require_ack": true,
  "ttl": 1
}
```

**Exemplo `ACK`**:

```json
{
  "type": "ACK",
  "msg_id": "m456",
  "from": "bob@UnB",
  "ttl": 1
}
```

#### Geração de `msg_id`

O campo **`msg_id`** deve ser um identificador **único por mensagem** dentro da rede P2P, de modo que peers possam:  

- Detectar duplicações (deduplicação).  
- Associar respostas (`ACK`, `WHO_HAS_HIT`) à requisição correspondente.  
- Evitar loops no roteamento com relay.

**Boas práticas para geração de `msg_id`:**

1. **UUIDv4** (recomendado)  
   - Gerar um UUID aleatório de 128 bits.  
   - Exemplo: `"msg_id": "550e8400-e29b-41d4-a716-446655440000"`  

2. **Timestamp + Random**  
   - Concatenar o carimbo de tempo UTC em microssegundos com alguns bytes aleatórios.  
   - Exemplo: `"msg_id": "20250921T103001Z-8f3a9c"`  

3. **Contador local + Prefixo de peer**  
   - Cada peer mantém um contador incremental e prefixa com o próprio `peer_id`.  
   - Exemplo: `"msg_id": "alice@UnB-1024"`  

> **Recomendação:** para este trabalho, os alunos podem adotar a opção (2) ou (3), por serem mais simples de implementar em Python. O importante é garantir que cada `msg_id` seja **único no tempo e entre peers diferentes**, evitando colisões.  



### Mensagens de publicação (`PUB`)

As mensagens do tipo **`PUB`** permitem a difusão de conteúdo para múltiplos peers simultaneamente. Elas são usadas para enviar mensagens de **namespace-cast** (para todos os peers de um namespace) ou **broadcast global** (para todos os peers conhecidos).

**Funcionamento:**

1. **Namespace-cast**  
   - O peer envia uma mensagem `PUB` direcionada a um namespace específico (`#namespace`).  
   - Todos os peers conectados nesse namespace recebem a mensagem, respeitando deduplicação.

2. **Broadcast global**  
   - O peer envia uma mensagem `PUB` com destino `"*"` (todos os peers conhecidos).
   - A mensagem é entregue a todos os peers ativos, exceto o próprio emissor.

3. **Encaminhamento e deduplicação**  
   - Toda mensagem `PUB` deve carregar um identificador único `msg_id` e `ttl`.  
     - veja a seção **Geração de `msg_id`** para detalhes sobre como criar identificadores únicos.
   - Como o TTL foi fixado em **1**, a difusão ocorre apenas para os vizinhos diretos do emissor.  
   - Cada peer deve armazenar os `msg_id` já recebidos e descartar duplicatas.

**Campos**  
- `type`: `"PUB"`  
- `msg_id`: identificador único da mensagem  
- `src`: peer emissor  
- `dst`: alvo da publicação (`#namespace` ou `"*"`)  
- `payload`: conteúdo da mensagem
- `require_ack`: sempre `false`  
- `ttl`: sempre **1**, posicionado como último campo  

**Exemplo PUB (namespace-cast)**:

```json
{
  "type": "PUB",
  "msg_id": "m777",
  "src": "alice@UnB",
  "dst": "#UnB",
  "payload": "Mensagem para todos do namespace UnB",
  "require_ack": false,
  "ttl": 1
}
```

> O peer `alice@UnB` envia uma mensagem para todos os peers do namespace `UnB`.

> Cada peer que receber essa mensagem deve verificar o `msg_id` para evitar processar duplicatas. Cada peer deve manter um cache dos `msg_id` recebidos para garantir que mensagens duplicadas sejam descartadas.

> Se `alice@UnB` tiver conexão direta com `bob@UnB` e `carol@UnB`, ambos receberão a mensagem. Se `alice@UnB` não tiver conexão direta com `carol@UnB`, mas `bob@UnB` tiver, então `bob@UnB` pode atuar como relay e encaminhar a mensagem para `carol@UnB`. Como o TTL é 1, a propagação termina em `carol@UnB`.

**Exemplo PUB (broadcast global)**:

```json
{
  "type": "PUB",
  "msg_id": "m778",
  "src": "alice@UnB",
  "dst": "*",
  "payload": "Mensagem para todos os peers conhecidos",
  "require_ack": false,
  "ttl": 1
}
```

> O peer `alice@UnB` envia uma mensagem para todos os peers conhecidos na rede P2P.

### Descoberta de rotas com `WHO_HAS` / `WHO_HAS_HIT`

O recurso **`who_has`** é utilizado para descobrir rotas quando um peer não possui conexão direta com o destino desejado. Seu funcionamento ocorre em duas etapas:

1. **Emissão do `WHO_HAS`**  
   - Um peer que deseja enviar mensagem a um destino desconhecido (ex.: `carol@UnB`) transmite a todos os seus vizinhos imediatos um pacote de controle do tipo `WHO_HAS`.  
   - Esse pacote contém o identificador do destino (`peer_id`) e um **TTL fixo igual a 1**, permitindo apenas a consulta direta aos vizinhos imediatos.  
   - Se o vizinho não conhece o destino, ele descarta o `WHO_HAS`, já que múltiplos saltos não são suportados (TTL = 1).

2. **Resposta com `WHO_HAS_HIT`**  
   - Quando um peer que **possui conexão direta** com o destino recebe o `WHO_HAS`, ele responde com uma mensagem do tipo `WHO_HAS_HIT`.  
   - Essa resposta percorre o caminho de volta até a origem, indicando qual vizinho deve ser usado como **próximo salto** para alcançar o destino.  
   - O peer de origem então armazena essa rota em cache e pode utilizá-la em mensagens futuras (ex.: `SEND`).  

**Exemplo `WHO_HAS`**:

```json
{
  "type": "WHO_HAS",
  "msg_id": "m789",
  "src": "alice@UnB",
  "dst": "carol@UnB",
  "ttl": 1
}
```

**Exemplo `WHO_HAS_HIT`**:

```json
{
  "type": "WHO_HAS_HIT",
  "msg_id": "m789",
  "src": "bob@UnB",
  "dst": "carol@UnB",
  "via": "bob@UnB",
  "ttl": 1
}
```

> O `WHO_HAS` funciona como uma “pergunta aberta” à rede: *“alguém tem rota para este destino?”*.  
> Já o `WHO_HAS_HIT` é a confirmação de que o caminho existe, permitindo ao peer de origem atualizar sua tabela de rotas.

### Encaminhamento com `relay`

A feature **`relay`** permite que um peer atue como **nó intermediário**, repassando mensagens quando não existe conexão direta entre origem e destino. Esse mecanismo é fundamental em cenários com NAT, firewalls ou quando o destino não abriu porta de escuta.

**Funcionamento:**

1. **Negociação inicial**  
   - Dois peers que suportam relay anunciam esse recurso no `HELLO/HELLO_OK`.  
   - Assim, cada peer sabe quais de seus vizinhos podem encaminhar mensagens.

2. **Encaminhamento de mensagens**  
   - Quando um peer precisa enviar uma mensagem (`SEND` ou `PUB`) para um destino inalcançável, ele escolhe um vizinho que suporte relay.  
   - O peer intermediário recebe a mensagem, verifica o campo `dst` e a repassa para frente, decrementando o campo `ttl`.  
   - A mensagem pode passar por no máximo um relay até atingir o destino (TTL = 1).  
   - Após repassar a mensagem, o relay deve enviar uma confirmação de encaminhamento (`RELAY_OK`) ao peer que solicitou o encaminhamento.  

3. **Falha de entrega pelo relay**  
   - Caso o relay não consiga entregar a mensagem ao destino (ex.: falha de conexão), ele deve notificar a origem com uma mensagem de erro `RELAY_FAIL`.  
   - Caso o relay receba a mensagem já com `ttl = 0`, ele deve notificar a origem com uma mensagem específica `TTL_EXPIRED`.  

4. **TTL e deduplicação**  
   - Cada mensagem transporta um identificador único (`msg_id`) e um campo `ttl` (time-to-live).  
   - O relay deve:  
     - **Decrementar o TTL** a cada salto.  
     - **Descartar mensagens** com TTL ≤ 0.  
     - **Evitar duplicações**, descartando mensagens já vistas com o mesmo `msg_id`.


**Exemplo `SEND` via relay**

```json
{
  "type": "SEND",
  "msg_id": "m321",
  "src": "alice@UnB",
  "dst": "carol@UnB",
  "payload": "Oi Carol!",
  "require_ack": true,
  "ttl": 1
}
```

> O peer `alice@UnB` não tem conexão direta com `carol@UnB`, então envia a mensagem para um vizinho que suporta relay. Esse vizinho repassa a mensagem, decrementando o TTL, até que ela alcance `carol@UnB` ou expire.

**Exemplo `RELAY_OK`**:

```json
{
  "type": "RELAY_OK",
  "msg_id": "m321",
  "src": "bob@UnB",
  "dst": "alice@UnB",
  "ttl": 1
}
```

> O peer `alice@UnB` não tem conexão direta com `carol@UnB`, então envia a mensagem para `bob@UnB`, que suporta relay.  

> Se `bob@UnB` conseguir entregar a mensagem, ele responde com `RELAY_OK`, confirmando o sucesso do encaminhamento (exemplo acima).

**Exemplo `RELAY_FAIL`**

```json
{
  "type": "RELAY_FAIL",
  "msg_id": "m321",
  "src": "bob@UnB",
  "dst": "alice@UnB",
  "reason": "Destino inacessível",
  "ttl": 1
}
```

> Se `bob@UnB` não conseguir entregar (por falha de conexão ou porque o TTL chegou a 0), ele deve responder com `RELAY_FAIL`, permitindo que `alice@UnB` saiba que o destino não foi alcançado (exemplo acima).


**Exemplo de erro `ttl_expired`**

```json
{
  "type": "TTL_EXPIRED",
  "msg_id": "m321",
  "src": "bob@UnB",
  "dst": "alice@UnB",
  "reason": "TTL chegou a 0 durante encaminhamento",
  "ttl": 1
}
```

> Se `bob@UnB` receber uma mensagem com `ttl = 0`, ele deve responder com `TTL_EXPIRED`, informando que a mensagem não pode ser encaminhada (exemplo acima).

**Resumo:**

- `relay` transforma peers acessíveis em pontos de encaminhamento.  
- Garante conectividade em topologias dinâmicas e ambientes restritivos.  
- Depende de **TTL = 1** e **msg_id** para evitar loops e duplicações.  
- Toda ação de relay deve ser confirmada com `RELAY_OK`.  
- Em caso de falha, o relay deve enviar `RELAY_FAIL` ao emissor original.  


### Métricas com `metrics`

A feature **`metrics`** permite que um peer consulte e compartilhe informações básicas de desempenho sobre suas conexões ativas.  
O envio das métricas é **sob demanda**, ou seja, só ocorre quando solicitado por outro peer.

**Funcionamento:**

1. **Negociação inicial**  
   - Dois peers anunciam suporte a `metrics` no `HELLO/HELLO_OK`.  
   - Apenas quando ambos confirmam, as mensagens de consulta e resposta podem ser trocadas.

2. **Requisição de métricas**  
   - Um peer interessado envia uma mensagem do tipo `METRICS_REQ` para um vizinho.  
   - Essa mensagem contém apenas o `msg_id`, o destino e o `ttl = 1`.

3. **Resposta com métricas**  
   - O peer que recebeu o `METRICS_REQ` responde com uma mensagem `METRICS`, contendo seus dados atuais.  
   - Campos sugeridos:  
     - **rtt_ms** → tempo médio de resposta calculado a partir de `PING/PONG`.  
     - **sent_count** → número de mensagens enviadas para o vizinho.  
     - **recv_count** → número de mensagens recebidas do vizinho.  
     - **last_seen** → timestamp da última atividade com o vizinho.  

---

**Exemplo `METRICS_REQ`**

```json
{
  "type": "METRICS_REQ",
  "msg_id": "m901",
  "src": "alice@UnB",
  "dst": "bob@UnB",
  "ttl": 1
}
```

> O peer `alice@UnB` solicita métricas ao vizinho `bob@UnB`.
> Se `bob@UnB` suportar `metrics`, ele responderá com uma mensagem `METRICS`.
> Caso contrário, `alice@UnB` pode receber um erro `unknown_command` ou simplesmente não obter resposta.

**Exemplo `METRICS`**

```json
{
  "type": "METRICS",
  "msg_id": "m901",
  "src": "bob@UnB",
  "dst": "alice@UnB",
  "rtt_ms": 42,
  "sent_count": 120,
  "recv_count": 115,
  "last_seen": "2025-09-21T11:45:00Z",
  "ttl": 1
}
```

> O peer `bob@UnB` responde com suas métricas atuais para `alice@UnB`.
> Essas informações podem ser usadas para monitorar a qualidade da conexão e tomar decisões de roteamento.

## 7) Tratamento de erros

**Formato**
```json
{ "status":"ERROR", "error":"<string>", "detail":"<opcional>", "limit":32768 }
```

**Códigos do servidor rendezvous** (já implementados):

- `bad_name`
- `bad_namespace`
- `bad_port`
- `bad_ttl`
- `invalid_json`
- `missing_type`
- `line_too_long`
- `unknown_command`


**Códigos adicionais (camada P2P cliente ↔ cliente)**:

- `ttl_expired`
- `no_route`
- `bad_format`
- `p2p_unknown_command`
- `peer_unreachable`
- `internal_error`
- `ack_timeout`
- `relay_not_supported`
- `who_has_timeout`
- `message_too_large`

> O erro `ttl_expired` ocorre quando uma mensagem chega com `ttl ≤ 0`. Como o TTL é sempre 1, isso indica que a mensagem já foi repassada por um relay e não pode ser encaminhada novamente.

> O erro `no_route` é retornado quando um peer tenta enviar uma mensagem para um destino desconhecido e não possui rota (direta ou via relay) para alcançá-lo.

> O erro `ack_timeout` indica que o peer de origem não recebeu a confirmação (`ACK`) dentro do tempo esperado, sugerindo que a mensagem pode não ter sido entregue.

> O erro `relay_not_supported` é retornado quando um peer tenta usar um vizinho que não suporta relay para encaminhar uma mensagem.

> O erro `who_has_timeout` ocorre quando um peer não recebe resposta ao `WHO_HAS` dentro do tempo limite, indicando que o destino pode estar inacessível.

> O erro `message_too_large` é retornado quando uma mensagem excede o limite de 32 KiB, conforme especificado nas regras de transporte.


---

## 8) Interface de usuário (CLI)

A interface textual deve oferecer comandos mínimos para interação:  

- `/peers` → listar peers conhecidos no namespace.  
- `/connect peer_id` → estabelecer conexão direta.  
- `/msg @peer mensagem` → enviar unicast.  
- `/msg #namespace mensagem` → enviar para todos de um namespace.  
- `/msg * mensagem` → broadcast global.  
- `/routes` → listar rotas conhecidas, TTLs e métricas básicas (RTT).  
- `/watch` → habilitar log em tempo real de mensagens recebidas.  
- `/quit` → sair do cliente.  

---

## 9) Arquitetura (sugestão de módulos)

Sugere-se modularizar a aplicação em componentes:  

- `rendezvous_client.py` → abstração para `REGISTER`, `DISCOVER`, `UNREGISTER`.  
- `p2p_transport.py` → gestão das conexões TCP entre peers (`HELLO`, `PING/PONG`, multiplexação).  
- `message_router.py` → roteamento de mensagens (`SEND`, `PUB`, `WHO_HAS`).  
- `cli.py` → interface de linha de comando, parsing de comandos do usuário.  
- `state.py` → armazenamento em memória de peers, rotas e mensagens deduplicadas.  
- `logger.py` → registro estruturado de eventos, conexões e erros.  
- 
---

## 10) Observabilidade (mínimo)

O cliente deve expor meios de inspeção do estado interno:  

- **Logs obrigatórios**: conexões estabelecidas, mensagens enviadas/recebidas, erros.  
- **Comando `/routes`**: listar vizinhos e rotas conhecidas, com métricas simples (ex.: RTT estimado).  
- **Opção de log em arquivo**: preferencialmente configurável por parâmetro de execução.  
- **Métricas opcionais** (para quem quiser ir além): contadores de mensagens, taxa de sucesso de entrega, peers ativos/inativos.  

---

## 11) Critérios de correção (funcional)

1. **REGISTER/DISCOVER/UNREGISTER** funcionando + lista de peers **atualizada** automaticamente.  
2. **Conexões TCP**: aceitar e abrir; `HELLO` e **keep-alive** `PING/PONG`.  
3. **Mensageria**: unicast com `ACK`; namespace-cast/broadcast com deduplicação + TTL.  
4. **Relay P2P**: `WHO_HAS`/`WHO_HAS_HIT`, **cache de rota** e entrega via vizinho.  
5. **Erros/limites**: tratamento de `no_route`, `ttl_expired`, `line_too_long`, etc.  
6. **Observabilidade**: `/routes`, logs mínimos e (se implementado) métricas.

---

## 12) Cenários mínimos de teste

Para validar a implementação, os alunos devem executar ao menos os seguintes cenários:  

1. **Conexão direta entre peers (sem NAT)**  
   - Dois peers no mesmo namespace.  
   - Registro no Rendezvous (`REGISTER`) e descoberta (`DISCOVER`).  
   - Estabelecimento de conexão TCP direta (`HELLO`, `HELLO_OK`).  
   - Envio de mensagens unicast (`SEND`) e namespace-cast (`PUB #namespace`).  

2. **Conexão indireta via relay (com NAT simulado)**  
   - Um peer inacessível diretamente (porta não aberta).  
   - Outro peer acessível que atua como **relay**.  
   - Testar envio de mensagem `SEND` com encaminhamento e confirmação de entrega.  
   - Verificar decremento do **TTL** e deduplicação.  

3. **Namespace-cast e broadcast**  
   - Vários peers registrados no mesmo namespace.  
   - Envio de mensagem `PUB #namespace` recebida por todos.  
   - Envio de mensagem `PUB *` (broadcast global).  
   - Conferir deduplicação de mensagens e respeito ao TTL.  

4. **Descoberta de rotas (`WHO_HAS` / `WHO_HAS_HIT`)**  
   - Um peer envia `WHO_HAS` para localizar destino desconhecido.  
   - Outro peer responde com `WHO_HAS_HIT`.  
   - A rota é adicionada ao cache e usada para o próximo envio.  

5. **Tratamento de erros**  
   - Mensagem maior que **32 KiB** deve retornar `line_too_long`.  
   - Mensagem com TTL expirado → erro `ttl_expired`.  
   - Tentativa de enviar a peer inexistente → erro `no_route`.  
   - Comando inválido no CLI → erro de formato.  

6. **Resiliência e churn**  
   - Peer sai inesperadamente (desconexão abrupta).  
   - Verificar que conexões são limpas e que o sistema continua funcionando.  
   - Reentrada de peer no mesmo namespace deve atualizar lista de peers.  

7. **Stress test (opcional)**  
   - Múltiplos peers enviando mensagens simultaneamente.  
   - Avaliar estabilidade da aplicação, logs gerados e manutenção de rotas.  

---

## 13) Checklist de funcionalidades (para o aluno)

- [ ] CLI com `/peers`, `/connect`, `/msg` (`@peer`, `#namespace`, `*`), `/routes`, `/watch`.  
- [ ] `REGISTER/DISCOVER/UNREGISTER` + atualização automática da lista.  
- [ ] Servidor e cliente TCP entre peers; `HELLO/HELLO_OK`; `PING/PONG`.  
- [ ] Envio `SEND` (unicast) com **ACK obrigatório**.  
- [ ] `PUB` para `#namespace` e `*` com TTL + deduplicação.  
- [ ] `WHO_HAS` / `WHO_HAS_HIT` para descoberta de rota + **cache**.  
- [ ] Encaminhamento com **TTL = 1**, **deduplicação** e **limites de fila**.  
- [ ] Tratamento de **erros** conforme tabela.  
- [ ] Logs e `/routes` com vizinhos/rotas/RTT.  


---

### Apêndice — Protocolo de Aplicação do Servidor Rendezvous

#### Visão Geral

O **servidor rendezvous** atua como um ponto central de encontro para peers em uma rede P2P.  

- Cada **peer** deve **registrar-se** no servidor para ficar visível.  
- Peers podem **descobrir** outros participantes em uma determinada sala (**namespace**).  
- Peers podem também **remover** seu registro (**unregister**).  
- Todos os registros têm um **tempo de vida (TTL)** em segundos. Expirado esse tempo, o registro é descartado automaticamente.  

A comunicação é feita sobre **TCP**. Cada **conexão aceita apenas um comando (uma linha JSON)** e é encerrada após a resposta.

---

#### Formato das mensagens

- Cada mensagem (requisição ou resposta) é um objeto **JSON válido**, enviado em **uma única linha** terminada por `\n`.  
- O servidor impõe um limite de **32 KB por linha**.  
- Se a linha for vazia ou apenas espaços, o servidor responde com um erro.  

---

#### Comandos aceitos

##### 1. `REGISTER`

Registra (ou atualiza) um peer no servidor.

**Campos obrigatórios:**
- `type`: `"REGISTER"`
- `namespace`: string (até 64 caracteres)  
- `name`: string (até 64 caracteres)  
- `port`: inteiro (1–65535)  

**Campos opcionais:**
- `ttl`: inteiro em segundos (1–86400). Se omitido, assume **7200 (2h)**.

**Exemplo de requisição:**
```json
{ "status":"ERROR", "error":"line_too_long", "limit":32768 }
```

**Sem rota (camada P2P)**  
```json
{ "type":"ERROR", "code":"no_route", "ref":"m123", "detail":"carol@UnB not reachable" }
```

**Possíveis erros:**
```json
{ "status": "ERROR", "error": "bad_name" }
{ "status": "ERROR", "error": "bad_namespace" }
{ "status": "ERROR", "error": "bad_port" }
{ "status": "ERROR", "error": "bad_ttl" }
```

---

##### 2. `DISCOVER`

Retorna a lista de peers registrados em um namespace.

**Campos:**
- `type`: `"DISCOVER"`
- `namespace`: string (opcional).  
  - Se omitido, retorna todos os peers de todos os namespaces.
  - `namespace` inexistente, o servidor retorna uma lista vazia.

**Exemplo de requisição:**
```json
{ "type": "DISCOVER", "namespace": "room1" }
```

**Exemplo de resposta:**
```json
{
  "status": "OK",
  "peers": [
    {
      "ip": "203.0.113.45",
      "port": 4000,
      "name": "peerA",
      "namespace": "room1",
      "ttl": 60,
      "expires_in": 42,
      "observed_ip": "203.0.113.45",
      "observed_port": 54321
    }
  ]
}
```

**Requisição para `namespace` inexistente**
```json
{ "type": "DISCOVER", "namespace": "room1" }
```

**Exemplo de resposta:**
```json
{"status": "OK", "peers": []}
```

---

##### 3. `UNREGISTER`

Remove peers previamente registrados.

**Campos obrigatórios:**
- `type`: `"UNREGISTER"`
- `namespace`: string 

**Campos opcionais:**
- `name`: string  
- `port`: inteiro  

**Exemplo de requisição:**
```json
{ "type": "UNREGISTER", "namespace": "room1", "name": "peerA", "port": 4000 }
```

**Resposta de sucesso:**
```json
{ "status": "OK" }
```

**Erros possíveis:**
```json
{ "status": "ERROR", "error": "bad_port (abc)" }
```
---

##### 4. Mensagens de Erro Genéricas

- Linha vazia ou só espaços:
```json
{ "status": "ERROR", "message": "Empty request line" }
```

- Linha muito longa (> 32768 bytes):
```json
{ "status": "ERROR", "error": "line_too_long", "limit": 32768 }
```

- Timeout de inatividade:
```json
{ "status": "ERROR", "message": "Timeout: no data received, closing connection" }
```

- Comando desconhecido:
```json
{ "status": "ERROR", "message": "Unknown command" }
```

---

#### Resumo do Ciclo de Uso

1. O cliente se conecta ao servidor rendezvous (TCP/8888 por padrão).  
2. Envia um **REGISTER** para se anunciar.  
3. Usa **DISCOVER** para consultar peers de um namespace.  
4. Pode **UNREGISTER** ao sair.  
5. Se o TTL expirar, o registro desaparece automaticamente.  