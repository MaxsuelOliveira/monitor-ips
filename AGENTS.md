# Monitor IPS

Aplicativo local Windows: Electron/HTML/CSS na janela principal, Python no backend
e CLI, Tkinter em `gui-tk` para compatibilidade. CLI e GUI compartilham o serviço em
`monitor_tool/service.py`; somente `windows.py` acessa DDC/CI. `tone.py` acessa a curva
GPU depois de confirmar SDR pela topologia Win32. Sem dependências
Python externas em tempo de execução. Não aplicar ajustes no hardware durante QA
sem autorização específica para os monitores/valores. Usar `--demo` nos testes de escrita.

`diagnostics.py` consulta NVAPI somente leitura; `visual.py` gera curvas manuais
absolutas, limitadas e opcionais. Não confundir o fundo cinza dos níveis 8/16/32 do
teste com uma alteração de hardware. Usar o centro do retângulo físico para mapear
cada monitor para o display Electron; não associar janelas de teste como filhas da
principal, pois o Windows pode colocá-las no mesmo monitor em tela cheia.

## Workflow global

- Prefixar todo comando shell com `rtk`; política: `C:/Users/maxsu/.codex/RTK.md`.
- Em projetos novos, verificar `rtk proxy npx.cmd --yes skills list -g`.
- Planejamento: `grill-me` / `grilling`; fechar decisões com o usuário antes de codar.
- Descoberta: `find-skills`, procurar uma skill adequada ao escopo.
- Frontend/UI: `design-taste-frontend`; validar a janela Electron real por Agent Browser/CDP,
  screenshots e fluxos. A janela Tkinter legada exige QA nativo separado.
- Navegador, quando houver páginas web: `agent-browser`, com sessão exclusiva e
  encerramento em `finally`. Sessão exclusiva por tarefa. CDP somente em instâncias
  próprias de QA; fechar app, backend Python e sessão exata ao concluir.
- Vídeo/motion, quando solicitado: `hyperframes`, HTML com render em código.
- Ler cada SKILL.md aplicável. Preservar instruções existentes ao atualizar este arquivo.

## Contratos

- Allowlist: brilho, contraste, ganhos R/G/B. Não aceitar códigos VCP arbitrários,
  reset de fábrica, energia ou entrada. O único controle categórico de escrita é
  modo de cor 0x14: consultar capacidades e aceitar somente presets anunciados.
  Temperatura Kelvin arbitrária e gamma VCP ficam fora desta versão.
- Sincronização: copiar valores atuais do IPS sem escrever na referência. Revalidar
  origem/destino antes de aplicar. Verificar todos os controles compatíveis ao final,
  inclusive os inicialmente iguais. Modo Usuário 2 foi validado no VA LHCFFFF para
  permitir RGB; o preset nominal pode diferir do IPS e deve aparecer na prévia.
- Backup schema 3 salva modo de cor e curva opcional. Restaurar preset antes dos
  ganhos, tratar efeitos colaterais e continuar aceitando schemas 1 e 2 sem inventar campos.
- Renderer isolado, sandbox, sem Node nem shell. IPC com sender validado e operações
  limitadas. Backend Python via stdio, sem servidor. Planos por token de uso único,
  nunca aceitar plano de escrita montado pelo renderer. Canais QA só em demo ou
  diagnóstico `--read-only`, cujo apply é bloqueado no processo principal.
- Sabor OLED é um perfil estético, não calibração medida. Curva GPU opcional apenas
  em SDR confirmado, um destino ativo por fonte GDI; bloquear HDR/WCG e espelhamento.
  Preservar extremos e monotonicidade e evitar acúmulo em reaplicações.
- Backup schema 2 inclui curva GPU de 3x256 WORDs. Restaurar schema 1 muda apenas
  DDC; nunca fingir que ele restaura a curva GPU. Falha silenciosa da API é erro de aplicação.
- Não prometer preto OLED, gamut novo, HDR ou persistência da curva. Não criar serviço
  ou watcher para reaplicar curvas. O usuário confirmou DISPLAY2 como IPS nesta máquina;
  a classificação local está em `monitor_roles.json` (ignorado pelo Git), sem autodetecção.
- Prévia + backup completo dos controles legíveis do destino antes de qualquer escrita.
- Backups JSON versionados, sem sobrescrever. Demonstração isolada de hardware real.
- Restauração exige mesmo identificador/interface e mesmos máximos. Não forçar
  restauração em outro monitor ou após troca de conexão. Não tratar como backup de firmware/ICC.
- Handles Win32 devem ser liberados em `finally`, inclusive ao ocorrer erro.
- Só a thread principal toca em Tkinter; um worker por operação, sem monitores permanentes.
- Preservar mudanças externas, validar e fazer commit apenas dos arquivos da tarefa.

## Validação

`rtk proxy python -m unittest discover -s tests -v`

`rtk proxy python -m compileall -q monitor_ips.py monitor_tool tests`

`rtk proxy python monitor_ips.py --demo list --json`

`rtk proxy npm.cmd test`

`rtk proxy npm.cmd run check`

`rtk proxy node scripts/qa-desktop-launch.cjs` informa PID, porta e sessão próprios.
Para leitura real sem permitir apply: acrescentar `--real-read-only`. Encerrar por
`window.monitor.qa('quit')`, fechar sessão exata do Agent Browser e verificar saída.

Para o smoke test nativo de leitura e screenshot com encerramento automático:
`rtk proxy python scripts/qa_gui.py`. Ele usa apenas o backend de demonstração.
