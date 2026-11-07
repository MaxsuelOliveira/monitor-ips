# Monitor IPS

Aplicativo Windows com **Electron + HTML/CSS** e backend Python local para
aproximar as configurações do VA às do IPS. A janela principal agora tem três
seções: **Sincronizar**, **Ajuste fino** e **Backups**. O CLI continua independente
de Node/Electron. O perfil OLED anterior não aparece no novo fluxo principal.

## Abrir

Dê dois cliques em **abrir.cmd** na pasta `F:\Jobs\SaaS\monitor-ips`.
Feche uma janela Tkinter antiga e abra pelo atalho para carregar a interface nova.
O Electron já foi instalado e validado nesta máquina.

Requisitos: Windows 10/11, Python 3.10+ no PATH, DDC/CI habilitado nos monitores.
Para instalar a interface: Node.js 22.12+ com npm e internet na primeira preparação.
Depois disso, a aplicação funciona localmente, sem conta, CDN ou servidor HTTP.
Não há pacotes Python externos para instalar.

```powershell
npm ci
npm run prepare:desktop
npm start

# Alternativas
python monitor_ips.py gui
python monitor_ips.py

# Demonstração, sem hardware
npm run demo
python monitor_ips.py --demo gui
```

A janela Tkinter anterior continua em `python monitor_ips.py gui-tk`.
Os comandos legados `compare`, `apply`, `pattern` e `oled` foram preservados.

## Igualar o VA ao IPS

1. Em Sincronizar, escolha o IPS como **Referência** e o VA como **Destino**.
2. Confira a tabela: referência, destino atual, depois da cópia e comparação.
3. **Mesmos valores** copia os números nativos. **Proporcional ao máximo**
   copia proporções quando as escalas forem diferentes.
4. A curva SDR opcional copia a curva atual do IPS, sem criar outro perfil.
   Se HDR ou o driver impedir a leitura, desmarque para copiar apenas DDC.
5. Clique em **Igualar VA ao IPS**, revise e confirme. Um backup completo dos
   campos legíveis do destino é salvo antes da primeira escrita.

O IPS é apenas lido. Se o IPS ou o destino mudarem depois da prévia, a operação
é bloqueada. Após aplicar, o serviço relê e verifica os controles compatíveis.

Nesta máquina: **DISPLAY2 / VLK2730 = IPS** e **DISPLAY1 / LHCFFFF = VA**,
conforme identificação do usuário. O arquivo local `monitor_roles.json` mapeia IDs
para tipos e é ignorado pelo Git. Não há detecção automática da tecnologia do painel.

### Modo de cor e RGB bloqueado

Os presets de fábrica dos dois modelos possuem ganhos RGB diferentes. O diagnóstico
real mostrou que o VA confirmava o comando DDC, mas ignorava o novo ganho RGB.
No VA local, **Usuário 2 (0x0C)** permite editar RGB. Presets 0x05, 0x08 e Usuário 1
não aceitaram os ganhos individuais.

O automático consulta as capacidades anunciadas e pode usar um modo Usuário
para copiar os ganhos. Prefere Usuário 2 quando disponível e mantém um modo Usuário
já ativo. O preset nominal pode diferir do IPS, mas os controles copiados são
verificados. A prévia e a confirmação mostram essa mudança; presets não anunciados
não são enviados. Alterar um preset pode mudar outros controles: o serviço relê e
aplica novamente os valores desejados.

Em **Opções do modo de cor**, escolha automático, mesmo preset literal da
referência, Usuário 1 ou Usuário 2. O preset literal pode bloquear RGB e provocar
falha de verificação. A aplicação informa essa falha, sem declarar sucesso.

## Ajuste fino e backups

- **Ajuste fino:** brilho, contraste e ganhos RGB em unidades nativas, dentro dos
  máximos mostrados. Revise antes de aplicar. Também há backup automático.
- **Teste visual:** sombras, realces e escala de cinza no destino. Esc ou Fechar
  encerra somente essa janela.
- **Backups:** crie uma cópia, abra a pasta ou escolha um JSON do mesmo monitor
  para restaurar. A restauração também tem prévia, confirmação e backup anterior.
- **Histórico:** resultados, falhas e caminhos dos backups da sessão.

Padrão: `%LOCALAPPDATA%\MonitorIPS\backups`; demo:
`%LOCALAPPDATA%\MonitorIPS\demo-backups`. Use `--backup-dir` para outra pasta.
Arquivos nunca são sobrescritos e são publicados completos antes de escrever.
A publicação usa hard link: prefira uma pasta local NTFS. Falha de disco bloqueia o ajuste.

| Schema | Conteúdo restaurável |
| --- | --- |
| 1 | Brilho, contraste e ganhos RGB legíveis |
| 2 | Controles DDC e curva GPU SDR de 3 × 256 valores |
| 3 | Controles DDC, modo de cor e, quando legível, curva GPU SDR |

Backups antigos sem modo/curva não restauram esses campos. Schema 3 restaura o
preset antes dos ganhos e verifica os efeitos sobre outros controles.
Restaurar recupera o arquivo escolhido; não executa reset de fábrica, nem altera
firmware ou arquivos ICC. Identidade, máximos e modo real/demo precisam corresponder.
Trocar porta, dock ou modo de imagem pode exigir nova leitura. Não force outro monitor.
Evite ajustar pelo OSD ou por outro aplicativo durante a operação.

## CLI

```powershell
python monitor_ips.py list
python monitor_ips.py list --json

# Cópia atual do IPS DISPLAY2 para VA DISPLAY1
python monitor_ips.py match --source 0581ae7f4b073cc4 --target 43ecb36d2d9651ca --dry-run
python monitor_ips.py match --source 0581ae7f4b073cc4 --target 43ecb36d2d9651ca

# Alternativas explícitas (substitua ID_IPS e ID_VA)
python monitor_ips.py match --source ID_IPS --target ID_VA --mode relative --no-tone
python monitor_ips.py match --source ID_IPS --target ID_VA --color-mode source --dry-run
python monitor_ips.py match --source ID_IPS --target ID_VA --color-mode user2

python monitor_ips.py set --monitor ID_VA brightness=30 contrast=50 --dry-run
python monitor_ips.py backup --monitor ID_VA --output backups\va-original.json
python monitor_ips.py restore --monitor ID_VA --file backups\va-original.json
python monitor_ips.py --backup-dir backups match --source ID_IPS --target ID_VA --yes

python monitor_ips.py --demo match --source demo-ips --target demo-va --yes
python monitor_ips.py --help
```

Opções globais vêm antes do subcomando. Escritas exigem confirmação interativa
ou `--yes` em automações. `--dry-run` não escreve e prevalece sobre `--yes`.
O estado demo dura o processo atual; na janela, dura a sessão.
`compare` e `apply` mantêm a cópia proporcional anterior dos cinco controles DDC.
O comando legado `oled` não participa do novo fluxo de sincronização.

## Limitações

- Mesmos números não garantem mesma luminância, gamut, gamma físico ou contraste.
  Calibração medida exige colorímetro. Não transforma IPS/VA em OLED.
- A curva GPU usa uma API legada. HDR/WCG, topologia ambígua ou falha ao verificar SDR
  bloqueiam sua cópia. Windows, jogos e apps de cor podem substituí-la depois.
  Não há serviço, tarefa agendada ou watcher de reaplicação.
- Ler um VCP não garante que aceite escrita. Falhas parciais informam o backup;
  o controle pode ter mudado antes de falhar na verificação. Sem rollback silencioso.
- Controles indisponíveis ou valores acima do máximo do destino são identificados
  e não contam como iguais. Um preset pode afetar controles não legíveis.
- Docks, telas internas, drivers e sessão remota podem limitar DDC. Prefira
  conexão HDMI/DisplayPort direta, modo estendido e DDC/CI habilitado.
- Não copia resolução, frequência, entrada, energia, ICC ou HDR.

## Desenvolvimento e validação

`desktop/` contém Electron, preload isolado, HTML/CSS/JS e cliente RPC.
O renderer não tem Node, shell ou acesso direto a arquivos. Um Python por janela
recebe JSON por stdin/stdout. Planos ficam no Python e são aplicados por token
de uso único. `monitor_tool/service.py` concentra as regras, `windows.py` acessa
DDC/CI e `tone.py` acessa a curva SDR. A janela aguarda operações antes de fechar
e encerra seu próprio processo Python.

```powershell
rtk proxy python -m unittest discover -s tests -v
rtk proxy python -m compileall -q monitor_ips.py monitor_tool tests scripts
rtk proxy npm.cmd test
rtk proxy npm.cmd run check

# QA Electron com CDP temporário e sessão exclusiva
rtk proxy node scripts/qa-desktop-launch.cjs
rtk proxy node scripts/qa-desktop-launch.cjs --real-read-only

# QA Tkinter legado
rtk proxy python scripts/qa_gui.py
```

O launcher de QA informa porta/PID/sessão em `output/desktop-qa.json`.
Use Agent Browser com esse nome e porta. Ao terminar, invoque
`window.monitor.qa('quit')`, feche a sessão exata e confirme a saída do launcher.
QA só é habilitado em demo ou diagnóstico `--read-only`, que bloqueia apply no
main. A abertura normal não usa CDP nem canais de QA.

Evidências: [DESKTOP-VALIDATION.md](documents/DESKTOP-VALIDATION.md).
Histórico: [VALIDATION.md](documents/VALIDATION.md),
[OLED-VALIDATION.md](documents/OLED-VALIDATION.md).
Referências: [Electron](https://www.electronjs.org/docs/latest/tutorial/security),
[VCP](https://learn.microsoft.com/en-us/windows/win32/api/lowlevelmonitorconfigurationapi/nf-lowlevelmonitorconfigurationapi-getvcpfeatureandvcpfeaturereply),
[curva GPU](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setdevicegammaramp),
[VCP 0x14](https://www.ddcutil.com/vcpinfo_output/).
