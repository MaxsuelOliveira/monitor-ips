# Sabor OLED e restauração do IPS — 07/11/2026

O usuário identificou seu IPS como DISPLAY2 e escolheu o perfil Equilibrado.
O outro painel do par IPS/VA é DISPLAY1. A identificação é uma classificação
fornecida pelo usuário, não uma detecção da tecnologia do painel.

## Restauração solicitada

O IPS DISPLAY2 (`0581ae7f4b073cc4`, VLK2730) estava com brilho 5/100.
Foi restaurado a partir de `backups/20261107T132219Z-018e927d070145dd93d0dc0142e8767f.json`:

- Brilho voltou a 30/100, confirmado pela leitura após escrita.
- Contraste 50, vermelho 44, verde 50 e azul 50 já correspondiam ao backup.
- O serviço criou backup anterior à restauração em
  `C:/Users/maxsu/AppData/Local/MonitorIPS/backups/20261107T140747Z-2437e2348cf34688b1dc721395f4376b.json`.

Depois dessa restauração foi aplicado o perfil estético escolhido, descrito abaixo.

## Implementação e validação automatizada

- 37 testes passaram: serviço, CLI, curvas, preservação de extremos, intensidade,
  ausência de acúmulo, restauração de curva/DDC, backup sem controles DDC,
  rejeição HDR, falhas silenciosas da API, topologia espelhada e liberação de DC/handles.
- `compileall` passou. Ruff não está instalado no Python local; não foi executado.
- Smoke test nativo Tkinter passou com operações simuladas: copiar, ajustar,
  aplicar/restaurar DDC, aplicar Sabor OLED, confirmar reaplicação sem mudanças,
  abrir/fechar o padrão visual e acessar a interface com rolagem no tamanho mínimo.
- Capturas próprias inspecionadas: `output/gui-demo.png`, `output/pattern-demo.png`.
  O QA captura apenas seus próprios HWNDs, sem depender da janela em primeiro plano.
- Estruturas Win32 conferidas em execução: DISPLAYCONFIG_PATH_INFO 72 bytes,
  DISPLAYCONFIG_MODE_INFO 64 bytes, ADVANCED_COLOR_INFO 32 bytes.

## Aplicação em hardware real

As duas telas foram identificadas em modo SDR pela topologia Win32 antes da escrita.
Foi aplicado **Sabor OLED Equilibrado com curva GPU SDR**, uma tela por vez, com
backups completos DDC + curva anterior. A verificação após a primeira aplicação
confirmou que a curva da outra tela permaneceu intacta. Ao final, as duas curvas
foram lidas e comparadas com os respectivos perfis. Contraste e RGB permaneceram
iguais aos snapshots anteriores, e preparar novamente o mesmo perfil retornou
zero alterações.
Uma nova leitura posterior confirmou as duas curvas ainda ativas, com diferença
máxima de **0** entre cada entrada lida e seu perfil esperado (3 canais × 256 valores).

| Tela | Painel | Brilho antes do perfil | Brilho depois | Contraste | R / G / B |
| --- | --- | --- | --- | --- | --- |
| DISPLAY1 / LHCFFFF | VA | 5/100 | 5/100 | 50/100 | 45 / 43 / 50 |
| DISPLAY2 / VLK2730 | IPS | 30/100 (restaurado) | 22/100 | 50/100 | 44 / 50 / 50 |

O VA já tinha brilho abaixo do teto de 16%, portanto a aplicação preservou 5/100.
No IPS, o teto Equilibrado reduziu o brilho restaurado de 30 para 22/100.
As curvas são diferentes para IPS/VA e não alteram os controles DDC de ganho RGB.

Backups anteriores ao Sabor OLED, com curva original, para desfazer integralmente:

- VA DISPLAY1: `backups/20261107T141732Z-2b428761fe0946f1b450de4b70a4b0c4.json`.
- IPS DISPLAY2: `backups/20261107T141732Z-1127fc92d0c34f8d8dc4a60725f8f5be.json`.

O serviço também criou backups automáticos imediatamente antes de cada aplicação:

- VA: `backups/20261107T141733Z-5177d340b3a44535b9f7f3042d39e741.json`.
- IPS: `backups/20261107T141734Z-e1fe478d6830463297954adfae29e842.json`.

Snapshots e resultados completos estão em `output/balanced-applied.json`, ignorado
pelo Git, assim como os backups e a classificação local `monitor_roles.json`.

Exemplos de restauração dos estados anteriores ao perfil:

```powershell
python monitor_ips.py restore --monitor 0581ae7f4b073cc4 --file backups/20261107T141732Z-1127fc92d0c34f8d8dc4a60725f8f5be.json
python monitor_ips.py restore --monitor 43ecb36d2d9651ca --file backups/20261107T141732Z-2b428761fe0946f1b450de4b70a4b0c4.json
```

## Limites da evidência

As escritas e leituras reais foram confirmadas. A restauração da curva foi testada
no backend simulado; a restauração DDC do IPS também foi executada em hardware real.
Não foi realizada medição com colorímetro nem avaliação humana do resultado visual.
Não há equivalência física de preto, gamut ou HDR com OLED. Os perfis são heurísticos.
A curva GDI pode ser substituída pelo sistema, jogos ou software de calibração e
pode ser perdida após eventos de vídeo; nenhum serviço/watchdog foi instalado.

## Encerramento de recursos

As janelas/threads de QA próprias foram encerradas. A checagem encontrou uma
instância `pythonw.exe monitor_ips.py gui` aberta fora dos comandos de QA desta
tarefa; ela foi preservada. É preciso fechar e reabrir essa janela para carregar
os módulos atualizados, inclusive suporte a backups schema 2.
