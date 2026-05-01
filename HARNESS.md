# HARNESS.md — Mensageria P2P Confiável com RDT, Grafos e Visualização

## 1. Identidade do Projeto

Projeto acadêmico para simular um **sistema de mensageria P2P confiável** usando:

* Python no backend
* FastAPI para API HTTP e WebSocket
* Sockets UDP para comunicação entre roteadores
* Grafos ponderados para representar a topologia da rede
* Algoritmo de Dijkstra para cálculo de menor caminho
* Protocolos RDT sobre UDP
* React no frontend para visualização da simulação

O sistema deve demonstrar, de forma visual e rastreável, o envio de mensagens entre roteadores, incluindo encaminhamento, perdas, ACKs, NAKs, timeouts, retransmissões e logs.

---

## 2. Objetivo Principal

Construir uma aplicação que permita visualizar e testar uma rede P2P confiável baseada em UDP.

A comunicação real entre os roteadores deve usar **somente sockets UDP**.

A API Python e o frontend React existem apenas para controle, visualização e demonstração. Eles não substituem a comunicação UDP entre roteadores.

---

## 3. Enunciado Base do Trabalho

O sistema deve implementar:

* Inicialização de roteadores por ID
* Leitura de arquivos de configuração
* Topologia com pelo menos 5 nós
* Cálculo de rotas usando Teoria dos Grafos, preferencialmente Dijkstra
* Tabela de encaminhamento por roteador
* Mensagens de texto limitadas a 100 caracteres
* Encaminhamento hop-by-hop entre roteadores
* Logs locais por roteador
* Descarte aleatório de pacotes com probabilidade de 10%
* Confiabilidade via ACK, timeout e retransmissão
* Estratégia stop-and-wait
* Uso exclusivo de UDP para transporte entre roteadores

---

## 4. Decisão de Arquitetura

A aplicação será separada em duas partes principais:

```text
Frontend React
    ↓ HTTP / WebSocket
Backend Python FastAPI
    ↓ controle da simulação
Motor de Simulação
    ├── Grafo e Dijkstra
    ├── Protocolos RDT
    └── Roteadores UDP
```

### 4.1 Frontend

Responsável apenas pela visualização e interação:

* Exibir a topologia da rede
* Mostrar roteadores e enlaces
* Permitir envio de mensagens
* Mostrar eventos em tempo real
* Mostrar tabela de rotas
* Mostrar logs por roteador
* Destacar mensagens em trânsito
* Destacar perda, retransmissão, ACK, NAK e timeout

### 4.2 Backend

Responsável pela lógica real:

* Ler `roteador.config`
* Ler `enlaces.config`
* Montar o grafo ponderado
* Calcular rotas com Dijkstra
* Inicializar roteadores UDP
* Implementar protocolos RDT
* Simular perda e corrupção
* Registrar logs
* Emitir eventos para o frontend via WebSocket

---

## 5. Regras Invioláveis

O Codex deve respeitar obrigatoriamente estas regras:

1. Não remover o uso de UDP entre roteadores.
2. Não transformar a comunicação entre roteadores em HTTP.
3. Não fazer o frontend conversar diretamente com os sockets UDP.
4. Não remover os arquivos `roteador.config` e `enlaces.config`.
5. Não ignorar o limite de 100 caracteres por mensagem.
6. Não remover logs locais por roteador.
7. Não remover o descarte aleatório de 10%.
8. Não remover ACK, timeout e retransmissão no RDT 3.0.
9. Não remover a estratégia stop-and-wait.
10. Não implementar múltiplos pacotes por mensagem neste MVP.
11. Não misturar responsabilidades entre frontend, API e motor de simulação.
12. Não criar soluções mágicas que pulem o encaminhamento hop-by-hop.
13. Não enviar mensagem diretamente ao destino final se houver caminho intermediário calculado.
14. Não usar banco de dados no MVP, salvo se explicitamente solicitado depois.
15. Não adicionar autenticação no MVP, salvo se explicitamente solicitado depois.

---

## 6. Escopo do MVP

O MVP deve conter:

### Backend

* API FastAPI
* WebSocket para eventos
* Leitura dos arquivos de configuração
* Grafo ponderado
* Dijkstra
* Roteadores UDP simulados
* RDT 1.0
* RDT 2.0
* RDT 3.0
* Perda aleatória de pacotes
* Corrupção simulada de pacotes
* Logs por roteador
* Envio de mensagens via API

### Frontend

* React com Vite
* Visualização da rede
* Formulário de envio de mensagem
* Seleção do protocolo RDT
* Timeline de eventos
* Painel de logs
* Painel de tabela de rotas
* Destaque visual do fluxo da mensagem

---

## 7. Fora do Escopo Inicial

Não implementar no MVP:

* Banco de dados
* Login/autenticação
* Deploy em nuvem
* Sliding Window
* Fragmentação de arquivos
* Upload real de arquivos
* Múltiplas mensagens simultâneas
* Alteração dinâmica da topologia durante a execução
* Persistência histórica de simulações
* Comparação avançada de algoritmos de roteamento

Esses itens podem virar extensões futuras.

---

## 8. Estrutura Recomendada do Projeto

```text
rdt-p2p-visualizer/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes.py
│   │   │   └── websocket.py
│   │   ├── core/
│   │   │   ├── config_loader.py
│   │   │   ├── graph.py
│   │   │   ├── dijkstra.py
│   │   │   └── event_bus.py
│   │   ├── network/
│   │   │   ├── router.py
│   │   │   ├── packet.py
│   │   │   ├── udp_server.py
│   │   │   └── reliable_sender.py
│   │   ├── rdt/
│   │   │   ├── base.py
│   │   │   ├── rdt_1.py
│   │   │   ├── rdt_2.py
│   │   │   └── rdt_3.py
│   │   ├── simulation/
│   │   │   ├── network_engine.py
│   │   │   └── fault_simulator.py
│   │   └── logging/
│   │       └── router_logger.py
│   ├── config/
│   │   ├── roteador.config
│   │   └── enlaces.config
│   ├── logs/
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/
│   │   │   └── client.js
│   │   ├── websocket/
│   │   │   └── eventsSocket.js
│   │   ├── components/
│   │   │   ├── NetworkGraph.jsx
│   │   │   ├── MessageForm.jsx
│   │   │   ├── EventTimeline.jsx
│   │   │   ├── RouterDetails.jsx
│   │   │   ├── RoutingTable.jsx
│   │   │   └── LogPanel.jsx
│   │   └── pages/
│   │       └── Dashboard.jsx
│   ├── package.json
│   └── README.md
│
├── docker-compose.yml
├── Makefile
├── HARNESS.md
└── README.md
```

---

## 9. Arquivos de Configuração

### 9.1 `roteador.config`

Formato:

```text
[ID] [Porta] [IP]
```

Exemplo obrigatório para desenvolvimento:

```text
1 25001 127.0.0.1
2 25002 127.0.0.1
3 25003 127.0.0.1
4 25004 127.0.0.1
5 25005 127.0.0.1
```

### 9.2 `enlaces.config`

Formato:

```text
[ID_Origem] [ID_Destino] [Custo]
```

Exemplo obrigatório para desenvolvimento:

```text
1 2 10
1 3 15
2 4 5
3 4 10
4 5 2
2 5 20
```

A topologia deve ser tratada como não-direcionada, salvo se o enunciado for alterado explicitamente.

---

## 10. Modelo de Pacote

Todos os pacotes UDP devem trafegar como JSON serializado em UTF-8.

### 10.1 DATA

```json
{
  "type": "DATA",
  "rdt_version": "3.0",
  "seq": 1,
  "source": 1,
  "destination": 5,
  "current_router": 1,
  "payload": "Mensagem de teste",
  "checksum": "abc123",
  "path": [1, 2, 4, 5],
  "attempt": 1
}
```

### 10.2 ACK

```json
{
  "type": "ACK",
  "rdt_version": "3.0",
  "seq": 1,
  "source": 5,
  "destination": 1,
  "checksum": "def456"
}
```

### 10.3 NAK

```json
{
  "type": "NAK",
  "rdt_version": "2.0",
  "seq": 1,
  "source": 5,
  "destination": 1,
  "checksum": "ghi789"
}
```

---

## 11. Protocolos RDT

O projeto deve implementar os protocolos como classes separadas e intercambiáveis.

### 11.1 RDT 1.0

Canal perfeito.

Características:

* Sem perda
* Sem corrupção
* Sem ACK
* Sem NAK
* Sem timeout
* Sem retransmissão

Finalidade:

* Demonstrar envio básico da mensagem pela rota calculada.

### 11.2 RDT 2.0

Canal com corrupção detectável.

Características:

* Checksum
* ACK
* NAK
* Retransmissão quando houver NAK
* Simulação opcional de corrupção

Finalidade:

* Demonstrar detecção de erro e retransmissão por NAK.

### 11.3 RDT 3.0

Canal com perda.

Características obrigatórias:

* Checksum
* ACK
* Número de sequência
* Timeout
* Retransmissão
* Stop-and-wait
* Descarte aleatório de pacote

Finalidade:

* Atender diretamente ao requisito principal do trabalho: entrega confiável mesmo com perda de pacotes.

---

## 12. Stop-and-Wait

No RDT 3.0, o emissor deve:

1. Criar pacote DATA.
2. Enviar ao próximo salto calculado pela tabela de roteamento.
3. Aguardar ACK do destino final.
4. Se o ACK chegar antes do timeout, concluir envio.
5. Se o timeout estourar, retransmitir o mesmo pacote.
6. Repetir até sucesso ou até atingir o limite máximo de tentativas.

Configuração recomendada:

```text
TIMEOUT_SECONDS = 2
MAX_RETRIES = 5
LOSS_RATE = 0.10
CORRUPTION_RATE = 0.10
```

---

## 13. Roteamento

Cada roteador deve possuir uma tabela de encaminhamento.

Exemplo:

```json
{
  "router_id": 1,
  "routes": {
    "2": {
      "path": [1, 2],
      "next_hop": 2,
      "cost": 10
    },
    "5": {
      "path": [1, 2, 4, 5],
      "next_hop": 2,
      "cost": 17
    }
  }
}
```

O caminho deve ser calculado usando Dijkstra.

Não usar caminho fixo manual, exceto nos testes.

---

## 14. Encaminhamento Hop-by-Hop

Ao receber um pacote DATA:

1. O roteador valida o pacote.
2. Verifica se deve simular perda ou corrupção.
3. Se o pacote for perdido, registra descarte e não encaminha.
4. Se o roteador atual for o destino final, entrega a mensagem.
5. Se não for o destino final, consulta a tabela de roteamento.
6. Encaminha para o próximo salto.
7. Registra log.
8. Emite evento WebSocket.

---

## 15. Logs

Cada roteador deve possuir um arquivo local:

```text
backend/logs/router_1.log
backend/logs/router_2.log
backend/logs/router_3.log
backend/logs/router_4.log
backend/logs/router_5.log
```

Eventos mínimos de log:

* SENT
* FORWARDED
* RECEIVED
* DROPPED
* CORRUPTED
* ACK_SENT
* ACK_RECEIVED
* NAK_SENT
* NAK_RECEIVED
* TIMEOUT
* RETRY
* DELIVERED
* FAILED

Exemplo:

```text
[2026-05-01 20:10:33] SENT seq=1 destination=5 next_hop=2 payload="Olá"
[2026-05-01 20:10:34] FORWARDED seq=1 destination=5 next_hop=4
[2026-05-01 20:10:36] ACK_RECEIVED seq=1 from=5
```

---

## 16. Eventos WebSocket

O backend deve emitir eventos em tempo real para o frontend.

Eventos mínimos:

```text
NETWORK_STARTED
ROUTES_COMPUTED
MESSAGE_CREATED
MESSAGE_SENT
MESSAGE_FORWARDED
MESSAGE_RECEIVED
PACKET_DROPPED
PACKET_CORRUPTED
ACK_SENT
ACK_RECEIVED
NAK_SENT
NAK_RECEIVED
TIMEOUT
MESSAGE_RETRY
MESSAGE_DELIVERED
MESSAGE_FAILED
LOG_CREATED
```

Formato geral:

```json
{
  "type": "MESSAGE_FORWARDED",
  "timestamp": "2026-05-01T20:10:33",
  "seq": 1,
  "router_id": 2,
  "source": 1,
  "destination": 5,
  "next_hop": 4,
  "message": "Roteador 2 encaminhou pacote seq=1 para o roteador 4"
}
```

---

## 17. API HTTP

Endpoints mínimos:

```text
GET /health
GET /topology
GET /routers
GET /routes/{router_id}
GET /logs/{router_id}
POST /messages/send
WS /ws/events
```

### 17.1 `GET /health`

Resposta:

```json
{
  "status": "ok"
}
```

### 17.2 `GET /topology`

Deve retornar nós e enlaces.

```json
{
  "routers": [
    { "id": 1, "ip": "127.0.0.1", "port": 25001 },
    { "id": 2, "ip": "127.0.0.1", "port": 25002 }
  ],
  "links": [
    { "source": 1, "target": 2, "cost": 10 }
  ]
}
```

### 17.3 `POST /messages/send`

Entrada:

```json
{
  "source": 1,
  "destination": 5,
  "message": "Olá roteador 5",
  "rdt_version": "3.0"
}
```

Resposta:

```json
{
  "status": "queued",
  "seq": 1,
  "source": 1,
  "destination": 5,
  "path": [1, 2, 4, 5]
}
```

Validações obrigatórias:

* `source` existe
* `destination` existe
* `source != destination`
* `message` não está vazia
* `message` possui no máximo 100 caracteres
* `rdt_version` é `1.0`, `2.0` ou `3.0`
* Existe rota entre origem e destino

---

## 18. Frontend

O frontend deve ser simples, didático e funcional.

### 18.1 Tela Principal

A tela principal deve conter:

* Grafo visual da rede
* Formulário de envio
* Timeline de eventos
* Painel de detalhes do roteador selecionado
* Tabela de roteamento
* Painel de logs

### 18.2 Componentes

Componentes mínimos:

```text
NetworkGraph.jsx
MessageForm.jsx
EventTimeline.jsx
RouterDetails.jsx
RoutingTable.jsx
LogPanel.jsx
```

### 18.3 Formulário de Envio

Campos:

* Origem
* Destino
* Mensagem
* Protocolo RDT
* Botão enviar

Validações no frontend:

* Mensagem obrigatória
* Mensagem até 100 caracteres
* Origem diferente do destino
* Protocolo obrigatório

---

## 19. Visualização Esperada

A interface deve deixar claro:

* Qual roteador enviou a mensagem
* Qual roteador recebeu
* Qual roteador encaminhou
* Qual pacote foi descartado
* Qual pacote foi corrompido
* Quando houve ACK
* Quando houve NAK
* Quando houve timeout
* Quando houve retransmissão
* Quando a mensagem foi entregue com sucesso
* Quando a mensagem falhou após máximo de tentativas

---

## 20. Fluxo de Demonstração Obrigatório

Exemplo:

```text
Origem: 1
Destino: 5
Mensagem: Teste UDP confiável
Protocolo: RDT 3.0
```

Timeline esperada:

```text
Rota calculada: 1 → 2 → 4 → 5
Roteador 1 enviou DATA seq=1 para Roteador 2
Roteador 2 encaminhou DATA seq=1 para Roteador 4
Roteador 4 descartou DATA seq=1
Roteador 1 entrou em timeout aguardando ACK
Roteador 1 reenviou DATA seq=1 para Roteador 2
Roteador 2 encaminhou DATA seq=1 para Roteador 4
Roteador 4 encaminhou DATA seq=1 para Roteador 5
Roteador 5 recebeu DATA seq=1
Roteador 5 enviou ACK seq=1 para Roteador 1
Roteador 1 recebeu ACK seq=1
Mensagem entregue com sucesso
```

---

## 21. Fases de Implementação

### Fase 1 — Ambiente de Desenvolvimento e Estrutura Base

Implementar:

* Ambiente de desenvolvimento com containers
* `docker-compose.yml` para backend e frontend
* `Makefile` na raiz para comandos comuns
* Estrutura de diretórios
* FastAPI básico
* React básico
* Configurações iniciais
* `GET /health`

Critério de aceite:

* Backend sobe sem erro via container
* Frontend sobe sem erro via container
* `make up` inicia o ambiente de desenvolvimento
* `make down` encerra o ambiente
* `make logs` exibe logs dos serviços
* Frontend consegue consultar `/health`

---

### Fase 2 — Configuração e Grafo

Implementar:

* Leitura de `roteador.config`
* Leitura de `enlaces.config`
* Montagem do grafo
* Endpoint `/topology`

Critério de aceite:

* API retorna roteadores e enlaces corretamente
* Frontend mostra a topologia

---

### Fase 3 — Dijkstra e Rotas

Implementar:

* Algoritmo de Dijkstra
* Tabela de rotas por roteador
* Endpoint `/routes/{router_id}`

Critério de aceite:

* API retorna menor caminho, próximo salto e custo
* Frontend mostra tabela de rotas

---

### Fase 4 — UDP Básico

Implementar:

* Roteadores UDP
* Envio de DATA
* Recebimento de DATA
* Encaminhamento hop-by-hop
* Logs básicos

Critério de aceite:

* Mensagem sai da origem e chega ao destino via UDP
* Roteadores intermediários encaminham corretamente
* Logs são gravados

---

### Fase 5 — RDT 1.0

Implementar:

* Envio em canal perfeito
* Sem perda
* Sem ACK
* Sem timeout

Critério de aceite:

* Mensagem chega ao destino seguindo rota calculada
* Eventos aparecem no frontend

---

### Fase 6 — RDT 2.0

Implementar:

* Checksum
* Corrupção simulada
* ACK
* NAK
* Retransmissão por NAK

Critério de aceite:

* Pacote corrompido gera NAK
* Origem retransmite após NAK
* Frontend mostra corrupção, NAK e retransmissão

---

### Fase 7 — RDT 3.0

Implementar:

* Perda aleatória
* Timeout
* ACK
* Número de sequência
* Retransmissão por timeout
* Stop-and-wait

Critério de aceite:

* Com perda de pacotes, mensagem ainda chega ao destino
* Timeout aparece no frontend
* Reenvio aparece no frontend
* ACK finaliza a transmissão

---

### Fase 8 — Logs e Timeline

Implementar:

* Logs completos por roteador
* Endpoint `/logs/{router_id}`
* Timeline visual no React

Critério de aceite:

* Logs aparecem no frontend
* Timeline representa fielmente os eventos do backend

---

### Fase 9 — Polimento Visual

Implementar:

* Destaque de nó ativo
* Destaque de enlace ativo
* Destaque de erro/perda
* Layout limpo para apresentação

Critério de aceite:

* Demonstração clara para professor e turma
* Fluxo visual compreensível sem abrir o console

---

## 22. Estratégia de Desenvolvimento para o Codex

O Codex deve trabalhar incrementalmente.

Para cada fase:

1. Ler este `HARNESS.md`.
2. Entender a fase atual.
3. Fazer alterações pequenas e coesas.
4. Não quebrar fases anteriores.
5. Criar ou atualizar testes simples quando fizer sentido.
6. Rodar comandos de validação quando possível.
7. Informar claramente o que foi alterado.
8. Informar como testar.

Não implementar várias fases grandes de uma vez se isso aumentar risco de erro.

---

## 23. Comandos Esperados

### Ambiente com Containers

Os comandos principais devem ficar disponíveis na raiz do projeto via `Makefile`:

```bash
make up
make down
make logs
make backend-shell
make frontend-shell
```

O `docker-compose.yml` deve expor o backend FastAPI e o frontend React/Vite para desenvolvimento local. O ambiente deve ser fácil de iniciar, parar e inspecionar sem exigir configuração manual repetitiva.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 24. Dependências Backend

Dependências mínimas sugeridas:

```text
fastapi
uvicorn[standard]
pydantic
```

Dependências opcionais:

```text
networkx
pytest
```

Preferência:

* Implementar Dijkstra manualmente para fins acadêmicos.
* Usar NetworkX apenas se for explicitamente decidido depois.

---

## 25. Dependências Frontend

Dependências mínimas sugeridas:

```text
react
vite
```

Dependências recomendadas:

```text
reactflow
```

Tailwind é opcional, mas recomendado para acelerar o layout.

---

## 26. Convenções de Código

### Python

* Usar type hints quando possível.
* Separar responsabilidades por módulos.
* Evitar arquivos gigantes.
* Usar nomes claros.
* Não esconder exceções silenciosamente.
* Tratar erros de entrada da API com respostas claras.

### React

* Componentes pequenos.
* Estado centralizado no Dashboard quando fizer sentido.
* WebSocket separado em módulo próprio.
* Evitar lógica pesada no frontend.
* O frontend não decide rota; apenas exibe o que o backend informa.

---

## 27. Estado Global da Simulação

O backend deve manter em memória:

* Roteadores carregados
* Enlaces carregados
* Grafo
* Tabelas de roteamento
* Sequência atual de mensagens
* Clientes WebSocket conectados
* Eventos recentes

Não usar banco de dados neste MVP.

---

## 28. Tratamento de Concorrência

Como vários roteadores UDP podem rodar ao mesmo tempo, o Codex deve tomar cuidado com:

* Threads
* Sockets
* Estado compartilhado
* Sequências de mensagens
* Lista de clientes WebSocket

Solução aceitável para MVP:

* Usar threads para servidores UDP dos roteadores
* Usar locks simples quando manipular estado compartilhado
* Usar fila/event bus para propagar eventos

---

## 29. Critérios Gerais de Aceite

O projeto estará aceitável quando:

1. Backend iniciar corretamente.
2. Frontend iniciar corretamente.
3. Topologia com pelo menos 5 nós aparecer na tela.
4. Rotas forem calculadas com Dijkstra.
5. Mensagem de até 100 caracteres puder ser enviada.
6. Mensagem trafegar via UDP entre roteadores.
7. Encaminhamento hop-by-hop funcionar.
8. Logs forem gerados por roteador.
9. RDT 1.0 funcionar.
10. RDT 2.0 demonstrar corrupção, ACK, NAK e retransmissão.
11. RDT 3.0 demonstrar perda, timeout, retransmissão e ACK.
12. Stop-and-wait funcionar.
13. Frontend mostrar timeline de eventos.
14. Frontend mostrar tabela de rotas.
15. Frontend mostrar logs.

---

## 30. Critérios para Apresentação

Na apresentação, deve ser possível mostrar:

1. Arquivos `roteador.config` e `enlaces.config`.
2. Rede com pelo menos 5 roteadores.
3. Cálculo de menor caminho.
4. Envio de mensagem com RDT 1.0.
5. Envio com RDT 2.0 e corrupção simulada.
6. Envio com RDT 3.0 e perda simulada.
7. Timeout e reenvio.
8. ACK chegando na origem.
9. Logs de cada roteador.
10. Console ou interface mostrando o encaminhamento.

---

## 31. Prompt de Execução para o Codex

Use este prompt ao iniciar o trabalho com o Codex:

```text
Leia o arquivo HARNESS.md inteiro antes de codificar.

Você está implementando um projeto acadêmico chamado Mensageria P2P Confiável com RDT, Grafos e Visualização.

A comunicação entre roteadores deve usar obrigatoriamente sockets UDP. A API FastAPI e o frontend React servem apenas para controle e visualização.

Implemente o projeto de forma incremental, seguindo as fases do HARNESS.md. Não pule fases. Não remova requisitos do enunciado. Não transforme a comunicação entre roteadores em HTTP.

Comece pela Fase 1: ambiente de desenvolvimento com containers, Makefile na raiz, estrutura base do backend e frontend, endpoint /health, configuração mínima e instruções de execução.

Ao finalizar, explique os arquivos criados/alterados e os comandos para testar.
```

---

## 32. Prompt para Continuar uma Fase

```text
Leia o HARNESS.md e identifique a próxima fase pendente.

Implemente somente essa fase, mantendo compatibilidade com o que já funciona.

Depois de alterar o código, rode os testes ou comandos básicos possíveis.

Informe:
1. O que foi implementado
2. Arquivos alterados
3. Como testar
4. Próxima fase recomendada
```

---

## 33. Prompt para Corrigir Bug

```text
Leia o HARNESS.md e preserve as regras invioláveis.

Existe um bug no projeto. Investigue a causa sem remover requisitos.

Não substitua UDP por HTTP.
Não remova RDT.
Não remova logs.
Não remova Dijkstra.

Explique a causa do problema, aplique a correção mínima necessária e informe como testar.
```

---

## 34. Prompt para Melhorar Interface

```text
Leia o HARNESS.md antes de alterar a interface.

Melhore a visualização React sem mover lógica de rede para o frontend.

O frontend deve apenas consumir HTTP/WebSocket e representar visualmente:
- topologia
- eventos
- logs
- tabela de rotas
- mensagens
- ACK/NAK
- perdas
- timeouts
- retransmissões

Não implementar regras de roteamento no frontend.
```

---

## 35. Observações Finais

Este projeto deve priorizar clareza acadêmica e demonstrabilidade.

O mais importante não é criar uma aplicação complexa, mas sim demonstrar corretamente:

* UDP
* Roteadores
* Grafos
* Dijkstra
* Encaminhamento
* RDT
* ACK/NAK
* Timeout
* Retransmissão
* Stop-and-wait
* Logs
* Visualização em tempo real

Sempre que houver dúvida entre fazer algo sofisticado ou algo claro para apresentação, escolher a opção mais clara e didática.
