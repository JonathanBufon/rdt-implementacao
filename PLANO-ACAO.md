# Plano de Ação — Sistema de Mensageria P2P Confiável com UDP

## Contexto

Trabalho acadêmico de Redes de Computadores — Unochapecó 2026/1.

Implementação de um sistema de mensageria P2P confiável usando apenas sockets UDP, com roteamento por Dijkstra e confiabilidade via stop-and-wait (RDT 3.0).

---

## 1. Decisão de arquitetura

**Linguagem:** Python 3

**Motivos:**
- `socket` UDP já vem na biblioteca padrão
- `threading` facilita escutar pacotes enquanto o usuário digita
- `heapq` facilita implementar Dijkstra
- `json` facilita serializar pacotes
- `logging` resolve os logs locais

---

## 2. Estrutura do projeto

```
p2p-router/
├── main.py           # Ponto de entrada, lê ID via CLI
├── router.py         # Socket UDP, recebimento, encaminhamento, descarte
├── config_loader.py  # Lê roteador.config e enlaces.config
├── graph.py          # Grafo, Dijkstra, tabela de encaminhamento
├── packet.py         # Formato e serialização dos pacotes JSON
├── reliability.py    # Stop-and-wait, timeout, reenvio, deduplicação
├── logger.py         # Logs locais por roteador
├── roteador.config   # Mapeamento ID → porta/IP
├── enlaces.config    # Topologia e custos
└── logs/             # Gerado em runtime
    ├── router_1.log
    ├── router_2.log
    └── ...
```

### Responsabilidade de cada arquivo

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Lê ID via `argv`, inicializa roteador, inicia threads de escuta e input |
| `config_loader.py` | Carrega e valida `roteador.config` e `enlaces.config` |
| `graph.py` | Constrói grafo, executa Dijkstra, gera tabela de encaminhamento |
| `packet.py` | Define e serializa/desserializa pacotes DATA e ACK |
| `router.py` | Gerencia socket UDP, recebe pacotes, decide encaminhar ou entregar |
| `reliability.py` | Stop-and-wait: controla pending\_ack, timeout, reenvio, deduplicação |
| `logger.py` | Escreve eventos categorizados no arquivo de log do roteador |

---

## 3. Arquivos de configuração

### `roteador.config`
```
1 25001 127.0.0.1
2 25002 127.0.0.1
3 25003 127.0.0.1
4 25004 127.0.0.1
5 25005 127.0.0.1
```

### `enlaces.config`
```
1 2 10
1 3 5
2 3 2
2 4 1
3 4 9
3 5 2
4 5 4
```

**Topologia resultante (enlaces bidirecionais):**

```
    1
   / \
 10   5
 /     \
2---2---3
|       |
1   9   2
|       |
4---4---5
```

Caminho mais curto de 1 para 5: `1 → 3 → 5` (custo 7)

---

## 4. Formato dos pacotes UDP (JSON)

### Pacote DATA
```json
{
  "type": "DATA",
  "seq": 1,
  "origin": 1,
  "destination": 5,
  "payload": "Olá roteador 5",
  "path": [1, 3, 5]
}
```

> `path` é informacional (para log). O roteamento usa a forwarding table local de cada roteador, não o campo `path`.

### Pacote ACK
```json
{
  "type": "ACK",
  "seq": 1,
  "origin": 5,
  "destination": 1
}
```

> O `seq` no ACK deve corresponder ao `seq` do DATA que está sendo confirmado (conforme RDT 2.2).

---

## 5. Protocolo de confiabilidade — RDT 3.0

O sistema implementa **RDT 3.0** (canal com erros e perda), conforme ensinado nos slides de Camada de Transporte (Kurose/Ross, 9ª Ed.).

### Progressão dos protocolos RDT

| Versão | Problema tratado | Mecanismo |
|---|---|---|
| RDT 1.0 | Canal perfeito | Nenhum |
| RDT 2.0 | Bits corrompidos | ACK/NAK + checksum |
| RDT 2.1 | ACK/NAK corrompido | Número de sequência |
| RDT 2.2 | Sem NAK | ACK com seq do pacote confirmado |
| **RDT 3.0** | **Perda de pacote** | **Timeout + retransmissão** |

### Regras de stop-and-wait

1. Origem envia pacote DATA e guarda como `pending_ack`
2. Origem inicia timer de **3 segundos**
3. Se ACK com `seq` correto chegar → libera envio da próxima mensagem
4. Se timeout → reenvia o **mesmo** pacote, loga `[REENVIO]`, reinicia timer
5. Reenvio indefinido até ACK chegar

### Deduplicação no destino (obrigatória — slide 3-53/3-64)

- O destino rastreia o último `seq` recebido por origem
- Se DATA chegar com `seq` duplicado (ACK anterior se perdeu):
  - Reenvia ACK
  - **Não entrega a mensagem novamente ao usuário**

### Descarte aleatório (10%)

```python
if random.random() < 0.10:
    # descartar pacote, registrar [DESCARTE]
```

- Aplica-se a pacotes **DATA e ACK**
- Acontece antes do encaminhamento ou entrega
- Torna o reenvio testável em condições realistas

---

## 6. Tabela de encaminhamento

Cada roteador computa via Dijkstra o próximo salto para cada destino.

Exemplo para o Roteador 1:

| Destino | Próximo salto |
|---|---|
| 2 | 3 |
| 3 | 3 |
| 4 | 3 |
| 5 | 3 |

---

## 7. Logs locais

Cada roteador escreve em `logs/router_<ID>.log`:

| Categoria | Quando registrar |
|---|---|
| `[ENVIADA]` | Mensagem originada neste roteador |
| `[ENCAMINHADA]` | Pacote de terceiro repassado adiante |
| `[RECEBIDA]` | Mensagem cujo destino final é este roteador |
| `[DESCARTE]` | Pacote descartado pelo mecanismo de 10% |
| `[ACK_ENVIADO]` | ACK enviado pelo destino final |
| `[ACK_RECEBIDO]` | ACK recebido pela origem |
| `[REENVIO]` | Timeout disparou, pacote reenviado |

**Exemplo:**
```
2026-05-18 16:40:12 [ENVIADA]      Seq 1 destino 5 payload="Olá"
2026-05-18 16:40:13 [ENCAMINHADA]  Seq 1 origem 1 destino 5 próximo_salto 5
2026-05-18 16:40:14 [RECEBIDA]     Seq 1 origem 1 payload="Olá"
2026-05-18 16:40:14 [ACK_ENVIADO]  Seq 1 para origem 1
2026-05-18 16:40:17 [REENVIO]      Seq 1 destino 5 tentativa 2
2026-05-18 16:40:18 [DESCARTE]     DATA Seq 1 origem 1 destino 5
```

---

## 8. Interface de execução

Cada roteador é iniciado em um terminal separado:

```bash
python3 main.py 1
python3 main.py 2
python3 main.py 3
python3 main.py 4
python3 main.py 5
```

Comando para enviar mensagem no terminal do roteador origem:

```
send <destino> <mensagem>
```

Exemplo:
```
send 5 Olá roteador 5
```

Limite de payload: **100 caracteres**. Mensagens maiores são rejeitadas antes do envio.

---

## 9. Ordem de implementação (fases)

### Fase 1 — Base do projeto
Criar estrutura de arquivos. Critério: `python3 main.py 1` imprime:
```
Roteador 1 iniciado em 127.0.0.1:25001
```

### Fase 2 — Leitura de configuração
Implementar `load_routers_config()` e `load_links_config()`. Critério: estruturas corretas em memória.

### Fase 3 — Grafo e Dijkstra
Implementar `graph.shortest_path(1, 5)` → `[1, 3, 5]` e tabela de encaminhamento.

### Fase 4 — Socket UDP básico
Thread de escuta + envio manual. Critério: R1 envia para R3, R3 imprime que recebeu.

### Fase 5 — Encaminhamento hop-a-hop
Implementar forwarding. Critério: mensagem de R1 chega em R5 passando por R3, com prints em cada salto.

### Fase 6 — Logs
Adicionar log local em todos os eventos. Critério: arquivos `logs/router_*.log` com eventos corretos.

### Fase 7 — Descarte aleatório
Adicionar probabilidade de 10%. Critério: durante testes repetidos, aparece `[DESCARTE]` nos logs.

### Fase 8 — ACK e stop-and-wait
Implementar `pending_ack`, timeout, reenvio e deduplicação. Critério: mensagem chega mesmo com descartes, sem duplicação de entrega.

### Fase 9 — README e testes finais
Documentar como rodar, configurar topologia, testar perdas e verificar logs.

---

## 10. Pontos críticos de implementação

### Thread safety
`pending_ack` e `seq_number` são acessados pela thread de escuta e pela thread de envio simultaneamente. Usar `threading.Lock()` ou `threading.Event()`.

### Timeout eficiente
Usar `threading.Event.wait(timeout=3)` em vez de `time.sleep(3)`. Permite que o ACK desbloqueie o wait imediatamente ao chegar, sem esperar o timeout completo.

### Escopo do stop-and-wait
Um único `pending_ack` por roteador (não por destino). O roteador só envia a próxima mensagem quando a atual for confirmada.

### Campo `path` no pacote
Informacional apenas. O roteamento usa a forwarding table local de cada roteador, não o `path`.

---

## 11. Checklist final da atividade

```
[ ] Roteador recebe ID via linha de comando
[ ] Carrega roteador.config
[ ] Carrega enlaces.config
[ ] Topologia tem pelo menos 5 nós
[ ] Usa apenas sockets UDP
[ ] Implementa Dijkstra
[ ] Monta tabela de encaminhamento
[ ] Mensagem limitada a 100 caracteres
[ ] Encaminha mensagem salto a salto
[ ] Imprime status no console em cada salto
[ ] Gera logs locais por roteador
[ ] Registra mensagens enviadas
[ ] Registra mensagens encaminhadas
[ ] Registra mensagens recebidas
[ ] Registra descartes
[ ] Implementa 10% de perda aleatória (DATA e ACK)
[ ] Implementa ACK fim-a-fim
[ ] Implementa timeout com reenvio
[ ] Implementa stop-and-wait
[ ] Implementa deduplicação no destino
[ ] README explica execução e testes
```
