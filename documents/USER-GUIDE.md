# Guia de uso do Monitor IPS

[Voltar ao README](../README.md) · [English overview](../README.en.md)

Este guia detalha os recursos da interface em português e do CLI. Para preparar
o ambiente, consulte [Começar](../README.md#começar).

## Modelos prontos para IPS e VA

Abra **Modelos prontos** e selecione no topo o monitor que receberá os ajustes.
Selecione o destino pelo nome e identificador exibidos no seu computador. Nesta
tela, um IPS pode ser o destino mesmo que também esteja selecionado como referência;
somente a cópia exige duas telas diferentes.

| Modelo / ID CLI | Brilho IPS / VA | Curva SDR |
| --- | --- | --- |
| OLED equilibrado / `oled-balanced` | Teto 22% / 16% | Profundidade suave |
| Cinema escuro / `cinema-dark` | Teto 16% / 12% | Profundidade mais forte |
| Cores naturais / `natural` | Alvo 32% / 28% | Neutra |
| Ambiente claro / `bright-room` | Alvo 55% / 45% | Neutra |

Percentuais são da escala DDC, não luminância em cd/m². Um teto mantém brilho já
menor; um alvo pode aumentar o brilho atual e isso aparece na prévia. **Usar brilho
personalizado** substitui a sugestão por um alvo de 0 a 100%. Confira o tipo de
painel e clique **Revisar modelo no destino**; a aplicação só ocorre após **Salvar
backup e aplicar**. O modelo inicial selecionado é OLED equilibrado.

Todos preservam e verificam contraste, RGB e modo de cor atuais. As curvas são
absolutas, não acumulam o efeito e preservam códigos 0–8 e 240–255. A curva neutra
substitui inclusive ajustes anteriores nos três canais; não equivale a uma
calibração de cores. É possível desmarcar a curva e ajustar apenas o brilho.
HDR/WCG e topologia incompatível bloqueiam a curva, sem fallback automático no CLI.
O driver pode quantizar os valores; uma diferença de até 256/65535 é tolerada,
como nas demais operações de curva, para evitar reaplicações desnecessárias.

Não existe configuração universal que transforme IPS/VA em OLED. O contraste
físico e o controle de luz por pixel são características do painel. Estes números
são pontos de partida estéticos do aplicativo, não parâmetros certificados para
seu exemplar. Gamma 2,2, D65 e luminância precisam de medição para serem confirmados.
Pesquisa e fontes: [IMAGE-PRESETS-RESEARCH.md](IMAGE-PRESETS-RESEARCH.md).
Validação: [PRESETS-VALIDATION.md](PRESETS-VALIDATION.md).

```powershell
python monitor_ips.py presets
python monitor_ips.py presets --json
python monitor_ips.py preset --monitor ID_IPS --panel ips --name oled-balanced --dry-run
python monitor_ips.py preset --monitor ID_IPS --panel ips --name oled-balanced
python monitor_ips.py preset --monitor ID_VA --panel va --name cinema-dark --brightness 15
python monitor_ips.py preset --monitor ID_IPS --panel ips --name bright-room --no-tone --dry-run
```

Sem `--dry-run`, o CLI pede confirmação; `--yes` permite automação. Backups e
restauração usam o fluxo descrito abaixo. Nenhum modelo é reaplicado automaticamente.
O comando legado `oled` mantém seu comportamento anterior.

## Igualar o VA ao IPS

1. Em Copiar ajustes, escolha o IPS como **Referência** e o VA como **Destino**.
2. Confira a tabela: referência, destino atual, depois da cópia e comparação.
3. **Mesmos valores** copia os números nativos. **Proporcional ao máximo**
   copia proporções quando as escalas forem diferentes.
4. A curva SDR opcional copia a curva atual do IPS, sem criar outro perfil.
   Se HDR ou o driver impedir a leitura, desmarque para copiar apenas DDC.
5. Clique em **Igualar VA ao IPS**, revise e confirme. Um backup completo dos
   campos legíveis do destino é salvo antes da primeira escrita.

O IPS é apenas lido. Se o IPS ou o destino mudarem depois da prévia, a operação
é bloqueada. Após aplicar, o serviço relê e verifica os controles compatíveis.

A classificação IPS/VA depende da identificação feita pelo usuário. O arquivo local
`monitor_roles.json` mapeia IDs para tipos e é ignorado pelo Git. Não há detecção
automática da tecnologia do painel. Os números DISPLAY e IDs variam entre computadores.

### Modo de cor e RGB bloqueado

Alguns monitores bloqueiam ganhos RGB em determinados presets. Durante os testes
de desenvolvimento, um VA confirmou o comando DDC, mas ignorou o novo ganho RGB.
Em um VA testado durante o desenvolvimento, **Usuário 2 (0x0C)** permitiu editar
RGB, enquanto outros presets ignoraram a escrita. Esse resultado depende do modelo
e não deve ser interpretado como uma regra para todos os monitores.

O automático consulta as capacidades anunciadas e pode usar um modo Usuário
para copiar os ganhos. Prefere Usuário 2 quando disponível e mantém um modo Usuário
já ativo. O preset nominal pode diferir do IPS, mas os controles copiados são
verificados. A prévia e a confirmação mostram essa mudança; presets não anunciados
não são enviados. Alterar um preset pode mudar outros controles: o serviço relê e
aplica novamente os valores desejados.

Em **Opções do modo de cor**, escolha automático, mesmo preset literal da
referência, Usuário 1 ou Usuário 2. O preset literal pode bloquear RGB e provocar
falha de verificação. A aplicação informa essa falha, sem declarar sucesso.

## Ajustar aparência e backups

- **Brilho, Contraste e Cores:** brilho, contraste e ganhos RGB em unidades nativas, com
  campos numéricos, botões −/+ e sliders sincronizados. Editar apenas prepara os
  valores; revise e confirme para aplicar, com backup automático.
- **Curva SDR manual:** opção avançada, desligada por padrão. Meios-tons de 0,85
  a 1,15 e corte de sombras de 0 a 4 níveis digitais. Substitui a curva atual por
  uma curva absoluta e neutra, sem acumular ajustes. O corte pode esconder detalhes;
  nenhum desses controles reduz o preto físico emitido pelo painel.
- **Desfazer:** prepara a restauração do backup anterior à última aplicação no
  destino durante esta sessão. Backups de outras sessões continuam disponíveis na tela Backups.
- **Preto lavado?:** consulta RGB/faixa completa por NVAPI somente leitura em GPUs
  NVIDIA. Diagnóstico indisponível em outros drivers é informado sem inferir a faixa.
  O teste de preto abre uma janela em cada tela selecionada: Espaço alterna ambos
  entre 0, 8, 16 e 32; Esc fecha a janela. A comparação é visual, sem medição óptica.
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

# Use os identificadores retornados pelo comando list
python monitor_ips.py match --source ID_IPS --target ID_VA --dry-run
python monitor_ips.py match --source ID_IPS --target ID_VA

# Alternativas explícitas (substitua ID_IPS e ID_VA)
python monitor_ips.py match --source ID_IPS --target ID_VA --mode relative --no-tone
python monitor_ips.py match --source ID_IPS --target ID_VA --color-mode source --dry-run
python monitor_ips.py match --source ID_IPS --target ID_VA --color-mode user2

python monitor_ips.py set --monitor ID_VA brightness=30 contrast=50 --dry-run
python monitor_ips.py tune --monitor ID_VA --brightness 20 --contrast 50 --dry-run
python monitor_ips.py tune --monitor ID_VA --gamma 1.05 --black-point 0 --dry-run
python monitor_ips.py diagnose --monitor ID_VA
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
