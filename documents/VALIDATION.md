# Validação local — 07/11/2026

Ambiente: Windows, Python 3.14.10. Projeto novo em `F:/Jobs/SaaS/monitor-ips`.

## Resultado

- 18 testes automatizados do serviço, CLI e ciclo de vida dos handles Win32 passaram.
- `compileall` passou para entrada, módulos, testes e script de QA.
- Smoke test da janela Tkinter passou: leitura, comparação, aplicação simulada,
  restauração simulada, ajustes manuais, descarte de prévia e rolagem no tamanho mínimo.
- Captura nativa inspecionada em `output/gui-demo.png`. O QA não usa navegador,
  pois a interface é Tkinter. A janela e o worker próprios foram encerrados.
- Ruff não pôde ser executado: módulo `ruff` não está instalado neste Python.
  Nenhuma dependência global foi instalada para contornar isso.

## Hardware real: leitura e backup, sem escrita

Os dois monitores responderam aos cinco controles. Não foi inferido qual painel
é IPS ou VA. Os nomes abaixo combinam a descrição Win32 com o identificador de modelo.

| Tela | Nome | ID para CLI | Brilho | Contraste | Vermelho | Verde | Azul |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DISPLAY1 | Generic PnP Monitor (LHCFFFF) | `43ecb36d2d9651ca` | 5/100 | 50/100 | 45/100 | 43/100 | 50/100 |
| DISPLAY2 | Generic PnP Monitor (VLK2730) | `0581ae7f4b073cc4` | 30/100 | 50/100 | 44/100 | 50/100 | 50/100 |

Backups iniciais reais, excluídos do Git por conterem identificação local:

- DISPLAY1: `backups/20261107T132219Z-c691d41ad46f4326b1a6510950edead3.json`
- DISPLAY2: `backups/20261107T132219Z-018e927d070145dd93d0dc0142e8767f.json`

As escritas e restaurações foram verificadas apenas no backend simulado.
Aceitação de escrita por esses modelos, persistência após desligar e correspondência
visual de cores permanecem sem validação física. O usuário deve identificar as telas
antes de preparar/aplicar qualquer cópia.

## Decisões da interface

Aplicada a direção achromatic-ledger da skill design-taste-frontend: cores neutras,
sem decoração, tabela como superfície principal, prévia numérica do destino e uma
única ação primária. Adaptação para widgets Tkinter e fonte nativa Segoe UI, sem
assets web. Uma comparação de controles identifica o produto; não há dados inventados
fora do modo de demonstração explicitamente sinalizado.
