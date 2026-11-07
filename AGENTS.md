# Monitor IPS

Aplicativo local Windows em Python/Tkinter. CLI e GUI compartilham o serviço em
`monitor_tool/service.py`; somente `windows.py` acessa DDC/CI. `tone.py` acessa a curva
GPU depois de confirmar SDR pela topologia Win32. Sem dependências
Python externas em tempo de execução. Não aplicar ajustes no hardware durante QA
sem autorização específica para os monitores/valores. Usar `--demo` nos testes de escrita.

## Workflow global

- Prefixar todo comando shell com `rtk`; política: `C:/Users/maxsu/.codex/RTK.md`.
- Em projetos novos, verificar `rtk proxy npx.cmd --yes skills list -g`.
- Planejamento: `grill-me` / `grilling`; fechar decisões com o usuário antes de codar.
- Descoberta: `find-skills`, procurar uma skill adequada ao escopo.
- Frontend/UI: `design-taste-frontend`; validar a interface real. Aqui a janela é
  Tkinter, portanto validar widgets e captura nativa; um navegador não renderiza a GUI.
- Navegador, quando houver páginas web: `agent-browser`, com sessão exclusiva e
  encerramento em `finally`. Não iniciar browser para testes desta janela nativa.
- Vídeo/motion, quando solicitado: `hyperframes`, HTML com render em código.
- Ler cada SKILL.md aplicável. Preservar instruções existentes ao atualizar este arquivo.

## Contratos

- Allowlist: brilho, contraste, ganhos R/G/B. Não aceitar códigos VCP arbitrários,
  reset de fábrica, energia ou entrada. Temperatura e gamma VCP ficam fora desta versão.
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

Para o smoke test nativo de leitura e screenshot com encerramento automático:
`rtk proxy python scripts/qa_gui.py`. Ele usa apenas o backend de demonstração.
