# Monitor IPS

Ferramenta local para Windows, feita em Python, com janela Tkinter e CLI. Lê os
controles de imagem do IPS e do VA, compara os valores, prepara uma cópia
proporcional, permite ajustes manuais e restaura os valores salvos em backup.
Inclui **Sabor OLED**, um perfil visual com ajustes próprios para IPS e VA,
intensidades Suave/Equilibrado/Cinema e uma curva SDR opcional para meios-tons mais
profundos. É uma aproximação estética: não transforma o painel em OLED e não é
calibração instrumental.
Não precisa de ControlMyMonitor, PowerShell auxiliar, conta ou serviço externo.

## Abrir a janela

Requisitos: Windows 10/11, Python 3.10+ com Tkinter (incluído no instalador padrão
do python.org), monitores conectados e DDC/CI habilitado no menu físico deles.
Não há pacotes para instalar com pip. A validação local usou Python 3.14.

Na pasta `F:\Jobs\SaaS\monitor-ips`, dê dois cliques em **abrir.cmd**, ou execute:

```powershell
python monitor_ips.py gui
```

Para experimentar sem acessar os monitores reais:

```powershell
python monitor_ips.py --demo gui
```

1. Clique em **Atualizar monitores**. Os identificadores são exibidos junto ao nome
   e à conexão `DISPLAY1`, `DISPLAY2` etc. Use Configurações → Sistema → Tela →
   Identificar, no Windows, para reconhecer as telas. O programa não detecta IPS/VA.
2. Para copiar, selecione seu IPS como origem e seu VA como destino. Para perfis e
   restauração, o destino pode ser qualquer uma das telas. Sem classificação local,
   a pré-seleção é apenas a ordem das telas. O arquivo opcional `monitor_roles.json`
   mapeia IDs para `ips`/`va`, é ignorado pelo Git e permite mostrar o tipo nos seletores.
   Nesta máquina, DISPLAY2 foi identificado pelo usuário como IPS e DISPLAY1 como VA.
3. Use **Backup do destino** para guardar uma cópia manual. Antes de qualquer
   aplicação o programa também cria um backup automático.
4. Marque os controles desejados e clique em **Comparar / preparar cópia**. A tabela
   mostra a prévia e os controles ignorados por falha/indisponibilidade de leitura.
5. Clique em **Aplicar prévia** e confira a confirmação. Somente o destino recebe
   escritas. A origem é lida. Se os valores do destino tiverem mudado desde a prévia,
   a operação é bloqueada e você precisa preparar novamente.
6. Para ajuste fino, preencha valores nativos nos campos, mantenha marcados os
   controles desejados e clique em **Preparar ajustes manuais**, depois em Aplicar.
   Campos vazios são ignorados nesse fluxo.
7. Para desfazer, selecione o mesmo destino, clique em **Restaurar backup**, escolha
   o JSON e revise a prévia. Clique em Aplicar. A restauração também salva um backup
   do estado anterior à restauração.

A janela possui rolagem para telas menores ou escala de texto alta. Leituras DDC
rodam em uma thread de trabalho; aguarde a operação terminar para fechar a janela.

## Sabor OLED

Na janela, selecione o **destino**, confira **Painel do destino**, escolha a
intensidade e clique em **Preparar Sabor OLED**, depois em **Aplicar prévia**.
A opção **Curva SDR: substituir curva GPU atual** vem marcada na janela e é
explicitamente listada na confirmação. Desmarque para ajustar somente a luz de fundo.
A origem não participa desse perfil: aplique separadamente em cada tela.

| Intensidade | Teto de brilho IPS | Teto de brilho VA | Curva de meios-tons |
| --- | --- | --- | --- |
| Suave | 28% do máximo | 22% do máximo | Leve |
| Equilibrado (padrão) | 22% do máximo | 16% do máximo | Moderada |
| Cinema | 16% do máximo | 12% do máximo | Mais forte |

Esses números são pontos de partida heurísticos, não nits nem medições de contraste.
O perfil não aumenta um brilho que já esteja abaixo do teto. Preserva os controles
DDC de contraste e RGB. A curva GPU é absoluta e neutra nos três canais: substitui
a curva atual, sem multiplicar reaplicações ou alterar arquivos/perfis ICC. Se havia
uma curva de calibração carregada por outro software, ela será substituída até
restaurar ou o software/Windows carregá-la novamente.

As curvas preservam os códigos de entrada 0..8 e 240..255 e são monotônicas;
escurecem os meios-tons. Isso evita clipping introduzido pelo algoritmo nesses
extremos, mas não garante distinção física de todos os degraus no seu painel.
O ajuste VA é mais suave que o IPS para reduzir o risco de perder detalhes escuros.

Use **Teste visual no destino** para abrir sombras, realces e gradiente neutro na
tela selecionada. **Esc** ou **Fechar** encerra apenas essa janela. Olhe de frente,
na luz em que usa o monitor. A tela ajuda no ajuste visual, sem medir ou certificar cor.

Exemplos CLI:

```powershell
# Prévia com curva GPU (HDR precisa estar desligado)
python monitor_ips.py oled --monitor ID_IPS --panel ips --strength balanced --tone-curve --dry-run

# Aplicar, com confirmação interativa e backup automático
python monitor_ips.py oled --monitor ID_IPS --panel ips --strength balanced --tone-curve
python monitor_ips.py oled --monitor ID_VA --panel va --strength balanced --tone-curve

# Apenas luz de fundo, sem mexer na curva GPU
python monitor_ips.py oled --monitor ID_VA --panel va --strength subtle

# Padrão visual na tela escolhida
python monitor_ips.py pattern --monitor ID_IPS
```

Para desfazer **brilho e curva**, use Restaurar com o backup schema 2 criado antes
do perfil. Backups antigos schema 1 só restauram controles DDC e a prévia avisa isso.
O caminho do backup é apresentado após cada aplicação. Backups reais/simulados
continuam isolados. Se a curva não puder ser confirmada após a escrita, a operação
informa falha e fornece o backup; não relata sucesso apenas porque a API retornou TRUE.

**Limitações da curva:** requer SDR confirmado; HDR/Advanced Color ativo, topologia
ambígua ou impossibilidade de verificar o modo bloqueiam a curva antes de aplicar
o plano. O Windows, jogos ou aplicativos de calibração podem substituí-la depois.
Não há serviço de reaplicação, tarefa agendada ou watcher. A curva pode ser perdida
ao reiniciar, mudar resolução/conexões ou abrir certos jogos. Reaplique manualmente.
Essas limitações são descritas pela [Microsoft na documentação de SetDeviceGammaRamp](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setdevicegammaramp).

## Linha de comando

Execute os comandos dentro da pasta do projeto. As opções globais `--demo` e
`--backup-dir` vêm **antes** do subcomando. Os exemplos com `ID_IPS` e `ID_VA` são
marcadores: substitua pelos IDs apresentados por `list`.

```powershell
# Descobrir monitores e valores atuais
python monitor_ips.py list
python monitor_ips.py list --json

# Backups manuais: o arquivo de saída precisa ser novo
python monitor_ips.py backup --monitor ID_IPS --output backups\ips-original.json
python monitor_ips.py backup --monitor ID_VA --output backups\va-original.json

# Comparar sem escrever
python monitor_ips.py compare --source ID_IPS --target ID_VA

# Preparar somente brilho e contraste sem escrever
python monitor_ips.py apply --source ID_IPS --target ID_VA --features brightness contrast --dry-run

# Aplicar: pergunta antes de escrever em um terminal interativo
python monitor_ips.py apply --source ID_IPS --target ID_VA --features brightness contrast

# Ajustes manuais em unidades nativas, dentro do máximo informado em list
python monitor_ips.py set --monitor ID_VA brightness=35 contrast=65 --dry-run
python monitor_ips.py set --monitor ID_VA red=45 green=43 blue=50

# Restaurar: exige backup do próprio monitor e da mesma conexão
python monitor_ips.py restore --monitor ID_VA --file backups\va-original.json --dry-run
python monitor_ips.py restore --monitor ID_VA --file backups\va-original.json

# Pasta personalizada para backups automáticos
python monitor_ips.py --backup-dir backups apply --source ID_IPS --target ID_VA

# Ajuda completa e ajuda por operação
python monitor_ips.py --help
python monitor_ips.py restore --help
```

Em automações, adicione `--yes` a `apply`, `set`, `restore` ou `oled` para confirmar a escrita
sem pergunta. Sem terminal interativo, a ferramenta exige essa opção. `--dry-run`
sempre prevalece e nunca escreve. `compare` e `list` apenas leem.

Exemplos executáveis de demonstração:

```powershell
python monitor_ips.py --demo list --json
python monitor_ips.py --demo compare --source demo-ips --target demo-va
python monitor_ips.py --demo apply --source demo-ips --target demo-va --yes
```

O estado simulado dura somente o processo atual. Para observar uma aplicação e
restauração mantendo estado, use a janela de demonstração. Backups simulados são
marcados e não podem ser usados em monitores reais, nem o inverso.

Saída do CLI: `0` = operação concluída, prévia ou cancelamento voluntário;
`1` = erro de operação/entrada; `2` = falha de argumentos do argparse ou aplicação
incompleta (esta última informa `ok: false`, backup, controles verificados e falhas);
`130` = interrupção por teclado. O JSON de `list --json` não recebe texto extra em
stdout. Resultados de aplicação incluem um objeto JSON após a prévia textual.

## O que é salvo e restaurado

Os cinco controles permitidos são:

| Nome no CLI | Controle | Código VCP |
| --- | --- | --- |
| `brightness` | Brilho | `0x10` |
| `contrast` | Contraste | `0x12` |
| `red` | Ganho vermelho | `0x16` |
| `green` | Ganho verde | `0x18` |
| `blue` | Ganho azul | `0x1A` |

O backup JSON versão 1 contém data UTC, identificação da interface do monitor,
valores e máximos dos controles legíveis, e erros dos controles indisponíveis.
Backups novos também tentam ler a curva GPU SDR: quando disponível, usam a versão 2
e incluem os três canais de 256 valores. Se HDR/driver impedir a leitura da curva,
o backup apenas DDC registra esse motivo. Uma aplicação que inclua curva exige
que ela tenha sido lida e salva antes da primeira escrita. Um backup de curva sem
controles DDC legíveis também é válido na versão 2.
Isso salva os controles e, na versão 2, a curva GPU SDR; não salva todos os menus,
firmware, LUT interna do monitor, arquivo ICC ou configurações do Windows.
**Restaurar significa voltar aos valores do
arquivo, não executar reset de fábrica.**

Por padrão, backups automáticos ficam em `%LOCALAPPDATA%\MonitorIPS\backups`.
O modo demo usa `%LOCALAPPDATA%\MonitorIPS\demo-backups`. O caminho exato é exibido
no log/resultado. Nomes únicos evitam sobrescrita. O arquivo é publicado completo
antes de escrever no monitor; se o disco/pasta falhar, nada é aplicado. A publicação
atômica usa hard link: prefira uma pasta local NTFS. Pastas em sistemas de arquivos
que não suportem hard links serão recusadas antes de qualquer ajuste.

A restauração exige o mesmo ID de interface e os mesmos máximos. Se trocar de
porta, cabo/dock, modo de imagem ou monitor, atualize a lista e confira seus backups;
não há opção para forçar uma restauração incompatível. A identidade usada vem do
Windows, não é uma autenticação criptográfica nem uma garantia de número de série.
Conexões espelhadas/agrupadas com identificação física ambígua bloqueiam escrita.

O programa coordena acessos entre suas instâncias GUI/CLI. Evite ajustar no menu
físico ou em outro software durante uma operação; esses acessos externos não podem
ser bloqueados por esta ferramenta.

## Limitações e solução de problemas

- Os valores são proporcionais ao intervalo nativo, com arredondamento. Por
  exemplo, 35/100 vira 70/200. Isso **não é equivalência de luminância ou cor**.
  IPS e VA precisam de ajuste visual; calibração precisa requer um colorímetro.
- Gamma VCP e temperatura de cor não são copiados. A curva GPU opcional é um
  recurso separado. Ganhos RGB são individuais e não equivalem a uma temperatura Kelvin.
- Uma leitura válida indica que o controle respondeu, mas não garante que aceite
  escrita no modo atual. A aplicação confere a leitura após cada escrita e ao final.
  Presets de imagem, HDR e contraste dinâmico podem limitar ou modificar controles.
- Se uma escrita falhar, a sequência para e informa o backup. O controle que falhou
  pode ter mudado antes da falha de verificação. Não há rollback silencioso; use
  Restaurar e confira o resultado. Se DDC ficar indisponível, use o menu do monitor.
- O suporte varia com monitor, driver, adaptadores, dock e conexão. Ative DDC/CI
  no menu e tente conexão HDMI/DisplayPort direta em modo estendido. Telas internas
  de notebooks e sessões remotas podem não expor DDC/CI.
- Se `python` não for reconhecido, instale Python com Tcl/Tk e adicione ao PATH;
  ou use `py -3 monitor_ips.py gui`. Para diagnosticar o atalho, abra pelo terminal.
- Não altera ICC, HDR, resolução, taxa de atualização, entrada de vídeo ou energia.
  A persistência dos ajustes após desligar depende do próprio monitor.

## Desenvolvimento e verificação

```powershell
rtk proxy python -m unittest discover -s tests -v
rtk proxy python -m compileall -q monitor_ips.py monitor_tool tests scripts
rtk proxy python scripts/qa_gui.py
```

Os testes do serviço e CLI simulam o hardware, incluindo falha de backup, escrita
parcial, efeitos entre controles, leitura divergente, restauração incompatível,
prévia desatualizada e controles não permitidos. O smoke test Tkinter faz o fluxo
completo simulado, valida a rolagem e encerra sua própria janela e thread.
Opcionalmente, se Pillow já estiver instalado, salva `output/gui-demo.png`.
Pillow não é uma dependência do aplicativo.

As leituras/escritas reais e a aplicação do Sabor OLED Equilibrado nas duas telas
locais estão registradas em `documents/OLED-VALIDATION.md`. Correspondência visual,
preferência estética e calibração colorimétrica não foram medidas por instrumento.

Referências de implementação: [consulta VCP](https://learn.microsoft.com/en-us/windows/win32/api/lowlevelmonitorconfigurationapi/nf-lowlevelmonitorconfigurationapi-getvcpfeatureandvcpfeaturereply),
[escrita VCP](https://learn.microsoft.com/en-us/windows/win32/api/lowlevelmonitorconfigurationapi/nf-lowlevelmonitorconfigurationapi-setvcpfeature),
[enumeração e liberação dos monitores físicos](https://learn.microsoft.com/en-us/windows/win32/api/physicalmonitorenumerationapi/nf-physicalmonitorenumerationapi-getphysicalmonitorsfromhmonitor),
[identificação da interface no Windows](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumdisplaydevicesw).
