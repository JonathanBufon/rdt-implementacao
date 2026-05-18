# Sistema de Mensageria P2P Confiável com UDP

Trabalho acadêmico — Redes de Computadores, Unochapecó 2026/1.

Simulação de uma rede de roteadores P2P usando apenas sockets UDP. Cada roteador executa Dijkstra para calcular rotas e encaminha mensagens salto a salto. A confiabilidade é garantida por stop-and-wait com ACK fim-a-fim e retransmissão por timeout (RDT 3.0).

---

## Requisitos

- Python 3.8+
- Sem dependências externas

---

## Estrutura do projeto

```
├── main.py           # Ponto de entrada
├── router.py         # Socket UDP e lógica de encaminhamento
├── config_loader.py  # Leitura dos arquivos de configuração
├── graph.py          # Dijkstra e tabela de encaminhamento
├── packet.py         # Serialização de pacotes JSON
├── reliability.py    # Stop-and-wait, timeout, reenvio
├── logger.py         # Logs locais por roteador
├── roteador.config   # Mapeamento ID → porta/IP
├── enlaces.config    # Topologia e custos dos enlaces
└── logs/             # Criado automaticamente em runtime
```

---

## Configuração da topologia

### `roteador.config`

Formato: `[ID] [Porta] [IP]`

```
1 25001 127.0.0.1
2 25002 127.0.0.1
3 25003 127.0.0.1
4 25004 127.0.0.1
5 25005 127.0.0.1
```

### `enlaces.config`

Formato: `[ID_Origem] [ID_Destino] [Custo]` (enlaces bidirecionais)

```
1 2 10
1 3 5
2 3 2
2 4 1
3 4 9
3 5 2
4 5 4
```

---

## Como executar

Abra um terminal por roteador e execute:

```bash
python3 main.py 1
python3 main.py 2
python3 main.py 3
python3 main.py 4
python3 main.py 5
```

Todos os roteadores devem estar ativos antes de enviar mensagens.

---

## Como enviar mensagens

No terminal do roteador de origem, use o comando:

```
send <destino> <mensagem>
```

Exemplo — enviar do roteador 1 para o roteador 5:

```
send 5 Olá roteador 5
```

Limite: **100 caracteres** por mensagem.

---

## Saída esperada no console

```
Roteador 1 iniciado em 127.0.0.1:25001
Roteador 1 encaminhando mensagem (Seq: 1) para o destino 5 via próximo salto 3
Roteador 3 encaminhando mensagem (Seq: 1) para o destino 5 via próximo salto 5
Roteador 5 recebeu mensagem (Seq: 1) de 1: "Olá roteador 5"
Roteador 1 recebeu ACK (Seq: 1) — mensagem entregue com sucesso
```

Com descarte aleatório ativo, pode aparecer:

```
Roteador 3 descartou pacote DATA (Seq: 1) — perda simulada
Roteador 1 timeout (Seq: 1) — reenviando tentativa 2
```

---

## Como verificar os logs

Após trocar mensagens, inspecione os arquivos de log:

```bash
cat logs/router_1.log
cat logs/router_3.log
cat logs/router_5.log
```

Categorias registradas:

| Categoria | Descrição |
|---|---|
| `[ENVIADA]` | Mensagem originada neste roteador |
| `[ENCAMINHADA]` | Pacote repassado para o próximo salto |
| `[RECEBIDA]` | Mensagem entregue a este roteador |
| `[DESCARTE]` | Pacote descartado (10% de probabilidade) |
| `[ACK_ENVIADO]` | ACK enviado pelo destino final |
| `[ACK_RECEBIDO]` | ACK recebido pela origem |
| `[REENVIO]` | Timeout disparou, pacote reenviado |

---

## Como testar a confiabilidade

O descarte aleatório de 10% afeta pacotes DATA e ACK. Para observar o mecanismo de reenvio:

1. Inicie os 5 roteadores
2. Envie várias mensagens entre roteadores distantes (ex: 1 → 5 ou 2 → 5)
3. Observe nos logs os eventos `[DESCARTE]` e `[REENVIO]`
4. Confirme que a mensagem sempre chega ao destino final

Para aumentar a probabilidade de descarte durante testes, edite temporariamente em `router.py`:

```python
LOSS_PROBABILITY = 0.30  # 30% para facilitar visualização
```

---

## Algoritmo de Dijkstra

Cada roteador conhece a topologia completa por meio dos arquivos de configuração. Ao iniciar, executa Dijkstra a partir do próprio ID para calcular o caminho de menor custo até todos os destinos.

A tabela de encaminhamento resultante mapeia cada destino ao **próximo salto** (não ao destino final diretamente):

```
Destino 2 → próximo salto 3
Destino 3 → próximo salto 3
Destino 4 → próximo salto 3
Destino 5 → próximo salto 3
```

O pacote viaja salto a salto, e cada roteador intermediário consulta sua própria tabela para decidir para onde enviar.

---

## Protocolo de confiabilidade (RDT 3.0)

O sistema implementa **stop-and-wait** com **ACK fim-a-fim**:

1. Origem envia DATA e aguarda ACK do destino final
2. Se o ACK não chegar em **3 segundos**, reenvia o mesmo pacote
3. O reenvio continua indefinidamente até o ACK chegar
4. O destino detecta duplicatas pelo número de sequência e reenvio o ACK sem re-entregar a mensagem

O número de sequência garante que retransmissões não causem entregas duplicadas ao usuário.
