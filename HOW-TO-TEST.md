# Como Testar o Projeto

Este guia descreve os testes manuais para verificar cada requisito do sistema.

---

## Pré-requisitos

- Python 3.8+
- 5 terminais abertos na pasta do projeto
- Sem dependências externas

---

## 1. Iniciando os roteadores

Abra um terminal por roteador e execute cada comando abaixo em um terminal diferente:

```bash
# Terminal 1
python3 main.py 1

# Terminal 2
python3 main.py 2

# Terminal 3
python3 main.py 3

# Terminal 4
python3 main.py 4

# Terminal 5
python3 main.py 5
```

Saída esperada em cada terminal ao iniciar:

```
Roteador 1 iniciado em 127.0.0.1:25001
```

> Inicie todos os 5 roteadores antes de enviar qualquer mensagem.

---

## 2. Enviando uma mensagem simples

No **Terminal 1** (Roteador 1), envie uma mensagem para o Roteador 5:

```
send 5 Ola roteador 5
```

### Saída esperada

**Terminal 1** (origem):
```
Roteador 1 encaminhando mensagem (Seq: 1) para o destino 5 via proximo salto 3
Roteador 1 recebeu ACK (Seq: 1) — mensagem entregue com sucesso
```

**Terminal 3** (intermediário):
```
Roteador 3 encaminhando mensagem (Seq: 1) para o destino 5 via proximo salto 5
Roteador 3 enviou ACK (Seq: 1) para 1 via proximo salto 1
```

**Terminal 5** (destino):
```
Roteador 5 recebeu mensagem (Seq: 1) de 1: "Ola roteador 5"
Roteador 5 enviou ACK (Seq: 1) para 1 via proximo salto 3
```

**O que verificar:**
- [ ] Caminho percorrido: `1 → 3 → 5` (conforme tabela Dijkstra)
- [ ] ACK retorna: `5 → 3 → 1`
- [ ] Roteadores 2 e 4 não imprimem nada (fora do caminho)

---

## 3. Testando diferentes rotas

Envie mensagens entre pares distintos para verificar as rotas calculadas pelo Dijkstra.

| Origem | Destino | Caminho esperado | Custo |
|--------|---------|-----------------|-------|
| 1 | 5 | 1 → 3 → 5 | 7 |
| 1 | 4 | 1 → 3 → 2 → 4 | 8 |
| 1 | 2 | 1 → 3 → 2 | 7 |
| 2 | 5 | 2 → 3 → 5 | 4 |
| 4 | 1 | 4 → 2 → 3 → 1 | 8 |

Exemplo — no **Terminal 2**, enviar para o Roteador 5:

```
send 5 teste de rota
```

**O que verificar:**
- [ ] Caminho impresso no console bate com a tabela acima
- [ ] A mensagem sempre chega ao destino correto

---

## 4. Testando o descarte aleatório e reenvio (RDT 3.0)

Com 10% de descarte por salto, descartes ocorrem naturalmente. Para forçar descartes frequentes e observar o mecanismo de reenvio, aumente temporariamente a probabilidade em `router.py`:

```python
LOSS_PROBABILITY = 0.50  # linha 11 de router.py
```

Reinicie todos os roteadores e envie uma mensagem:

```
send 5 teste com perda
```

**Saída esperada com descartes:**

```
# Terminal 1
Roteador 1 encaminhando mensagem (Seq: 1) para o destino 5 via proximo salto 3
Roteador 1 timeout (Seq: 1) — reenviando tentativa 2
Roteador 1 timeout (Seq: 1) — reenviando tentativa 3
Roteador 1 recebeu ACK (Seq: 1) — mensagem entregue com sucesso

# Terminal 3 ou 5 (onde ocorreu o descarte)
Roteador 3 descartou pacote DATA (Seq: 1) — perda simulada
```

**O que verificar:**
- [ ] `[DESCARTE]` aparece nos logs e no console
- [ ] `[REENVIO]` aparece no log do roteador de origem
- [ ] A mensagem **sempre** chega ao destino, independente do número de tentativas
- [ ] A mensagem é entregue **apenas uma vez** no destino (sem duplicação)

> Lembre de restaurar `LOSS_PROBABILITY = 0.10` após o teste.

---

## 5. Testando a deduplicação

Este teste verifica que o destino não entrega a mesma mensagem duas vezes quando o ACK se perde.

Configure `LOSS_PROBABILITY = 0.90` em `router.py` e envie:

```
send 5 teste deduplicacao
```

**O que verificar:**
- [ ] O Terminal 5 imprime `recebeu mensagem` **apenas uma vez**, mesmo que o roteador 1 reenvie várias vezes
- [ ] Nos logs do roteador 5, `[RECEBIDA]` aparece **somente uma vez** para o mesmo Seq

---

## 6. Testando o limite de 100 caracteres

No terminal de qualquer roteador, tente enviar uma mensagem longa:

```
send 5 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

**Saída esperada:**
```
Mensagem rejeitada: payload deve ter no maximo 100 caracteres.
```

**O que verificar:**
- [ ] Mensagem acima de 100 caracteres é rejeitada antes do envio
- [ ] Nenhum pacote é enviado pela rede

---

## 7. Verificando os arquivos de log

Após executar os testes acima, inspecione os arquivos de log:

```bash
cat logs/router_1.log
cat logs/router_3.log
cat logs/router_5.log
```

**Exemplo de log completo do roteador 1:**
```
2026-05-18 16:40:12 [ENVIADA]      Seq 1 destino 5 payload="Ola roteador 5"
2026-05-18 16:40:12 [ACK_RECEBIDO] Seq 1 de destino 5
2026-05-18 16:40:15 [ENVIADA]      Seq 2 destino 5 payload="teste com perda"
2026-05-18 16:40:18 [REENVIO]      Seq 2 destino 5 tentativa 2
2026-05-18 16:40:19 [ACK_RECEBIDO] Seq 2 de destino 5
```

**Exemplo de log do roteador 3:**
```
2026-05-18 16:40:12 [ENCAMINHADA]  Seq 1 origem 1 destino 5 proximo_salto 5
2026-05-18 16:40:15 [DESCARTE]     DATA Seq 2 origem 1 destino 5
2026-05-18 16:40:18 [ENCAMINHADA]  Seq 2 origem 1 destino 5 proximo_salto 5
```

**Exemplo de log do roteador 5:**
```
2026-05-18 16:40:12 [RECEBIDA]     Seq 1 origem 1 payload="Ola roteador 5"
2026-05-18 16:40:12 [ACK_ENVIADO]  Seq 1 para origem 1
2026-05-18 16:40:18 [RECEBIDA]     Seq 2 origem 1 payload="teste com perda"
2026-05-18 16:40:18 [ACK_ENVIADO]  Seq 2 para origem 1
```

**O que verificar:**
- [ ] Todos os 7 tipos de evento aparecem nos logs ao longo dos testes
- [ ] Timestamps e números de sequência são coerentes entre os roteadores

---

## 8. Encerrando os roteadores

Em cada terminal, pressione `Ctrl+C` ou digite:

```
exit
```

---

## Resumo do checklist

| Teste | O que verifica |
|-------|---------------|
| Inicialização | Roteador imprime IP e porta corretos |
| Mensagem simples 1→5 | Roteamento Dijkstra, encaminhamento hop-a-hop, ACK fim-a-fim |
| Diferentes rotas | Tabela de encaminhamento correta para todos os pares |
| Descarte + reenvio | RDT 3.0: timeout de 3s, retransmissão indefinida |
| Deduplicação | Destino entrega a mensagem apenas uma vez |
| Limite de 100 chars | Validação de payload antes do envio |
| Arquivos de log | Todos os eventos registrados corretamente |
