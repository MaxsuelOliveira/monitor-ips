# Electron e sincronização IPS → VA — 07/11/2026

## Entrega

- Interface principal substituída por Electron 45.2.3, HTML/CSS/JS local, fontes
  Public Sans e IBM Plex Mono empacotadas por npm. Não usa servidor ou CDN.
- Sincronizar, Ajuste fino e Backups. Referência/destino com os papéis conhecidos,
  tabela de prévia, modos exato/proporcional, cópia opcional da curva SDR,
  confirmação e backup automático.
- CLI `match` usa as mesmas regras. Tkinter anterior em `gui-tk`; comandos anteriores
  preservados. O experimento OLED não é a ação principal da nova janela.
- Processo Python por janela, JSON via stdin/stdout, planos no backend e tokens
  de uso único. Renderer sem Node, sandbox, CSP, navegação e IPC restritos.

## Causa do problema RGB real

O VA DISPLAY1 / LHCFFFF anunciava RGB legível. A escrita retornava sucesso, mas
uma leitura posterior retornava o valor anterior. Presets fixos eram a causa
observável: no preset inicial 0x08 o VA tinha R45/G43/B50. No preset 0x05 tinha
R49/G46/B47 e continuava recusando ganhos individuais. Usuário 1 (0x0B) também
não aceitou o ganho solicitado. Todos os casos foram detectados como falha,
interrompidos e tiveram backup.

As capacidades anunciadas das duas telas incluem 0x14(05 08 0B 0C). **Usuário 2
(0x0C)** permitiu ajustar e confirmar R44/G50/B50 no VA. O algoritmo consulta essas
capacidades e só seleciona um preset anunciado. A UI informa que o modo nominal
pode diferir do IPS, pois é necessário para RGB editável. O automático preserva
modo Usuário já ativo e não reativa um preset bloqueado na próxima execução.

## Estado final real verificado

Referência: IPS DISPLAY2 / VLK2730, ID `0581ae7f4b073cc4`.
Destino: VA DISPLAY1 / LHCFFFF, ID `43ecb36d2d9651ca`.
Foram copiados os valores **atuais** do IPS. O brilho do IPS estava em 5 nesta
tarefa; não foi presumido o valor 22 do experimento anterior. Nenhuma escrita foi
enviada ao IPS durante a sincronização.

| Controle | IPS / referência | VA / destino |
| --- | --- | --- |
| Brilho | 5/100 | 5/100 |
| Contraste | 50/100 | 50/100 |
| Vermelho | 44/100 | 44/100 |
| Verde | 50/100 | 50/100 |
| Azul | 50/100 | 50/100 |
| Curva GPU SDR | Referência | Igual, diferença máxima 0 em 768 entradas |
| Preset nominal | 0x05 | 0x0C / Usuário 2, necessário para editar RGB |

O recibo privado da releitura está em `output/native-match-verified.json`.
Uma nova prévia `match --dry-run` retornou nenhuma alteração aplicável.

Backups locais, ignorados pelo Git:

- **Antes de mudar o modo original do VA (0x08):**
  `backups/20261107T145235Z-c9eafce6311d475b858e518919b3a1d6.json`.
  Schema 3, inclui preset, ganhos e curva anterior; opção para desfazer toda a mudança.
- Antes da etapa final que habilitou Usuário 2 e copiou RGB/curva:
  `backups/20261107T145501Z-6a925dc1426d4b86837cb5e0630d7ce0.json`.

Exemplo para revisar a restauração original do VA, sem aplicar:

```powershell
python monitor_ips.py restore --monitor 43ecb36d2d9651ca --file backups/20261107T145235Z-c9eafce6311d475b858e518919b3a1d6.json --dry-run
```

## Validações

- **53 testes Python:** cópia exata/proporcional, guarda de origem/destino/curva,
  modo de cor, desbloqueio RGB, efeitos dos presets, schema 3 e compatibilidade,
  backup, falhas parciais, HDR e liberação de handles/DC.
- **Teste Node → Python RPC real em demo:** ler, comparar, aplicar, restaurar,
  rejeitar token reutilizado e encerrar o processo filho. Passou.
- Verificação sintática Node, compilação Python e `git diff --check` passaram.
- Auditoria npm durante instalação: zero vulnerabilidades reportadas nas 16 dependências.
- Ruff não instalado no Python local; lint Python não executado.

### Janela real e Agent Browser

Instâncias próprias com CDP local temporário e sessões distintas, todas encerradas:
`monitor-match-ab241e662b`, `monitor-match-67e74f2680`,
`monitor-match-481727b374`, `monitor-match-127091e68e`, `monitor-match-ed67ba2a58`.

- Demo Electron: leitura, confirmação/cópia e releitura, ajuste manual (brilho 42),
  backup manual, restauração de schema 3 e retorno ao valor 140, padrão visual
  aberto/fechado, abas e controles indisponíveis.
- O caminho de arquivo para restauração em QA foi fornecido pelo canal controlado
  de demonstração; não foi automatizado o seletor nativo de arquivos do Windows.
  A confirmação e a aplicação/restauração passaram pelo renderer, IPC e Python reais.
- Layout inspecionado em três larguras de janela: 820, 1180 e 1440. Sem overflow
  horizontal de página; rolagem vertical e ação primária acessível na janela menor.
- Fonte Public Sans confirmada carregada; sem erros JavaScript registrados no renderer.
- A ação de confirmação foi ligada ao submit do formulário para não depender de
  um frame de fechamento de dialog quando a janela está ocluída.
- Regressões adicionais em `scripts/qa-desktop-regressions.js` passaram na janela
  demo real: campo vazio não vira zero, cancelar descarta o plano manual,
  trocar de seção não aplica um plano de outro fluxo, cópia exata/proporcional,
  confirmação, referência preservada e reaplicação sem alterações.
- Diagnóstico Electron real com `--read-only`: selecionou DISPLAY2 como IPS e DISPLAY1
  como VA, mostrou nenhum ajuste pendente e confirmou o estado acima. A tentativa
  de apply de diagnóstico foi recusada no main antes de chegar ao backend.

Capturas locais ignoradas pelo Git: `output/electron-real.png`,
`output/electron-820.png`, `output/electron-1440.png`, `output/electron-pattern.png`.
A direção visual é data-terminal: superfícies escuras neutras, números monoespaçados,
seleção por linha discreta e comparação como conteúdo central. Sem imagens artificiais.

## Limites

A igualdade dos controles listados e das curvas foi confirmada por leitura real.
Não foi feita medição com colorímetro nem validação humana de aparência idêntica.
O preset nominal do VA é diferente por necessidade do firmware; a interface mostra
essa exceção. Outros menus/ICC/HDR/resolução não fazem parte da cópia. Jogos e Windows
podem substituir curvas GPU. Sem watcher, serviço ou tarefa agendada de reaplicação.

## Encerramento

As cinco instâncias próprias do Electron encerraram com código 0, junto dos seus
processos Python. Todas as sessões exatas do Agent Browser foram fechadas. A checagem
de PIDs/filhos e processos de backend/QA encontrou zero recursos de teste remanescentes.
O QA Tkinter também confirmou worker encerrado. Nenhuma instância humana foi encerrada.

O lint visual terminou sem falhas; números monoespaçados são uma decisão explícita
da direção data-terminal e os travessões da tabela representam valores indisponíveis.
