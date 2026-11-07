# Desenvolvimento do Monitor IPS

[README](../README.md) · [English README](../README.en.md)

## Desenvolvimento e validação

`desktop/` contém Electron, preload isolado, HTML/CSS/JS e cliente RPC.
O renderer não tem Node, shell ou acesso direto a arquivos. Um Python por janela
recebe JSON por stdin/stdout. Planos ficam no Python e são aplicados por token
de uso único. `monitor_tool/service.py` concentra as regras, `windows.py` acessa
DDC/CI e `tone.py` acessa a curva SDR. A janela aguarda operações antes de fechar
e encerra seu próprio processo Python.

`diagnostics.py` consulta somente a faixa de saída NVIDIA; `visual.py` gera a curva
manual. A atribuição da interface pública NVAPI está nos [avisos de terceiros](../THIRD_PARTY_NOTICES.md).
`controls.js` mantém os controles personalizados; `shell.js` organiza a navegação
e a configuração inicial; `presets.js` apresenta os modelos. O estilo claro usa
`simple.css` e `presets.css`. Os painéis expansíveis usam botões acessíveis em
`disclosures.js`/`disclosures.css`. Animações respeitam `prefers-reduced-motion`.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q monitor_ips.py monitor_tool tests scripts
npm.cmd test
npm.cmd run check

# QA Electron com CDP temporário e sessão exclusiva
node scripts/qa-desktop-launch.cjs
node scripts/qa-desktop-launch.cjs --real-read-only

# QA Tkinter legado
python scripts/qa_gui.py
```

O launcher de QA informa porta/PID/sessão em `output/desktop-qa.json`.
Use Agent Browser com esse nome e porta. Ao terminar, invoque
`window.monitor.qa('quit')`, feche a sessão exata e confirme a saída do launcher.
QA só é habilitado em demo ou diagnóstico `--read-only`, que bloqueia apply no
main. A abertura normal não usa CDP nem canais de QA.

Evidências: [DESKTOP-VALIDATION.md](DESKTOP-VALIDATION.md).
Documentação: [validação dos READMEs e do modelo reutilizável](README-VALIDATION.md).
Histórico: [VALIDATION.md](VALIDATION.md),
[OLED-VALIDATION.md](OLED-VALIDATION.md).
Referências: [Electron](https://www.electronjs.org/docs/latest/tutorial/security),
[VCP](https://learn.microsoft.com/en-us/windows/win32/api/lowlevelmonitorconfigurationapi/nf-lowlevelmonitorconfigurationapi-getvcpfeatureandvcpfeaturereply),
[curva GPU](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setdevicegammaramp),
[VCP 0x14](https://www.ddcutil.com/vcpinfo_output/).
