# Como Testar o Projeto

Este guia descreve os testes manuais para verificar cada requisito do sistema.

---

## Pré-requisitos

**Via Docker (recomendado — funciona em Windows, Mac e Linux):**
- Docker Desktop instalado e rodando

**Via local (Linux):**
- Python 3.8+
- `make` instalado
- `tmux` instalado (recomendado): `sudo apt install tmux`
- Sem dependências Python externas

---

## Início rápido

### Docker

```bash
make docker-build          # constrói a imagem (só na primeira vez)
make docker-run            # sobe os 5 roteadores em tmux no container
make docker-test           # teste automático sem abrir janelas
```

### Local (Linux)

```bash
make start   # sobe os 5 roteadores
make stop    # encerra tudo e libera as portas
make test    # teste automático R1→R5 (sem abrir terminais)
make logs    # exibe todos os arquivos de log
make status  # mostra quais roteadores estão ativos
make clean   # remove logs e __pycache__
```

---

## 0. Testando via Docker

> Use esta seção se estiver no **Windows** ou preferir não instalar Python e tmux localmente.

### Pré-requisitos

- Instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/) e certifique-se de que ele está rodando.
- Instale o **GNU Make** para poder usar os comandos `make ...` no PowerShell — veja o guia [WINDOWS-MAKE-SETUP.md](WINDOWS-MAKE-SETUP.md).

### Passo 1 — Construir a imagem

```bash
make docker-build
```

Ou diretamente:

```bash
docker build -t rdt-p2p .
```

Isso instala Python 3, tmux e make num container Debian. Só é necessário fazer uma vez.

### Passo 2 — Subir os roteadores interativamente

```bash
make docker-run
```

Ou diretamente:

```bash
docker run -it --rm --name rdt-p2p rdt-p2p
```

O container abre automaticamente uma sessão tmux com **5 panes**, um por roteador:

```
┌─────────────┬─────────────┬─────────────┐
│  Roteador 1 │  Roteador 2 │  Roteador 3 │
├─────────────┴──────┬──────┴─────────────┤
│     Roteador 4     │     Roteador 5     │
└────────────────────┴────────────────────┘
```

**Navegar entre panes:**

| Atalho | Ação |
|--------|------|
| `Ctrl+b` → seta | Move para o pane na direção da seta |
| `Ctrl+b` → `q` | Mostra número dos panes; digita para ir direto |
| `Ctrl+b` → `z` | Zoom no pane atual (tela cheia); repete para voltar |
| `Ctrl+b` → `d` | Sai do container (roteadores continuam rodando) |

Para voltar ao container após `Ctrl+b d`:

```bash
docker attach rdt-p2p
```

Para encerrar tudo:

```bash
docker stop rdt-p2p
```

### Passo 3 — Enviar uma mensagem

No pane do **Roteador 1**, digite:

```
send 5 Ola roteador 5
```

A saída esperada é a mesma descrita na seção 2 abaixo.

### Alternativa — Teste automático sem janelas

```bash
make docker-test
```

Ou diretamente:

```bash
docker run --rm --entrypoint make rdt-p2p test
```

Executa o teste R1→R5 dentro do container e imprime o resultado no terminal. Não exige interatividade.

### Limpar a imagem

```bash
make docker-clean
```

---

## 1. Iniciando os roteadores

### Com Makefile (recomendado — Linux)

```bash
make start
```

Com tmux instalado, abre uma sessão com 5 panes lado a lado — um por roteador.
Sem tmux, abre 5 abas no gnome-terminal.

**Navegar entre panes no tmux:**

| Atalho | Ação |
|--------|------|
| `Ctrl+b` → seta | Move para o pane na direção da seta |
| `Ctrl+b` → `q` | Mostra número dos panes; digita o número para ir direto |
| `Ctrl+b` → `z` | Zoom no pane atual (tela cheia); repete para voltar |
| `Ctrl+b` → `d` | Desanexa da sessão (roteadores continuam rodando) |

Para reconectar após `Ctrl+b d`:

```bash
make attach
```

### Manual (sem Makefile)

Abra um terminal por roteador e execute:

```bash
python3 main.py 1   # terminal 1
python3 main.py 2   # terminal 2
python3 main.py 3   # terminal 3
python3 main.py 4   # terminal 4
python3 main.py 5   # terminal 5
```

Saída esperada ao iniciar:

```
Roteador 1 iniciado em 127.0.0.1:25001
```

> Inicie todos os 5 roteadores antes de enviar qualquer mensagem.

---

## 2. Enviando uma mensagem simples

No pane do **Roteador 1**, envie uma mensagem para o Roteador 5:

```
send 5 Ola roteador 5
```

### Saída esperada

**Roteador 1** (origem):
```
Roteador 1 encaminhando mensagem (Seq: 1) para o destino 5 via proximo salto 3
Roteador 1 recebeu ACK (Seq: 1) — mensagem entregue com sucesso
```

**Roteador 3** (intermediário):
```
Roteador 3 encaminhando mensagem (Seq: 1) para o destino 5 via proximo salto 5
Roteador 3 enviou ACK (Seq: 1) para 1 via proximo salto 1
```

**Roteador 5** (destino):
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

Exemplo — no pane do **Roteador 2**, enviar para o Roteador 5:

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

Reinicie os roteadores (`make stop && make start`) e envie:

```
send 5 teste com perda
```

**Saída esperada com descartes:**

```
# Roteador 1
Roteador 1 encaminhando mensagem (Seq: 1) para o destino 5 via proximo salto 3
Roteador 1 timeout (Seq: 1) — reenviando tentativa 2
Roteador 1 timeout (Seq: 1) — reenviando tentativa 3
Roteador 1 recebeu ACK (Seq: 1) — mensagem entregue com sucesso

# Roteador 3 ou 5 (onde ocorreu o descarte)
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
- [ ] O Roteador 5 imprime `recebeu mensagem` **apenas uma vez**, mesmo que o roteador 1 reenvie várias vezes
- [ ] Nos logs do roteador 5, `[RECEBIDA]` aparece **somente uma vez** para o mesmo Seq

---

## 6. Testando o limite de 100 caracteres

No pane de qualquer roteador, tente enviar uma mensagem longa:

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

```bash
make logs
```

Ou individualmente:

```bash
cat logs/router_1.log
cat logs/router_3.log
cat logs/router_5.log
```

**Exemplo de log do roteador 1:**
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

## 8. Teste automático (sem abrir terminais)

```bash
make test
```

Sobe os roteadores em background, envia `"Ola roteador 5"` de R1 para R5 e imprime o console de cada roteador e os logs de arquivo. Útil para verificar rapidamente que o sistema está funcionando.

---

## 9. Encerrando os roteadores

```bash
make stop
```

Mata todos os processos e libera as portas UDP. Ou, dentro do tmux, pressione `Ctrl+C` em cada pane e depois `Ctrl+b d` para desanexar.

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
| Arquivos de log | Todos os 7 tipos de evento registrados corretamente |
| Teste automático | `make test` passa sem erros |
