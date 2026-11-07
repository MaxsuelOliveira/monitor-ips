# Validação do layout claro — 07/11/2026

## Atualização: expansores próprios

- Eliminados os cinco pares de tags de expansão nativa. Explicações dos modelos, opções de cor, instruções de comparação e histórico usam `disclosures.js`/`disclosures.css`; curva SDR usa seção comum na tela Avançado.
- Botão nativo com `type="button"`, `aria-expanded`, `aria-controls`, região identificada e visibilidade por `hidden`. Clique, Enter e Espaço verificados em Electron DEMO; conteúdo fechado sai da árvore de acessibilidade.
- Histórico vazio apresenta mensagem; ao criar um backup DEMO, a mensagem desapareceu, o contador passou a 1 e o registro apareceu.
- Verificados o seletor do modo de cor expandido e os controles SDR na tela Avançado.
- Capturas locais: `output/disclosures-desktop.png` (1180 × 830) e `output/disclosures-mobile.png` (390 × 844). Sem overflow horizontal da página no viewport menor (scrollWidth 375).
- Busca estática e DOM renderizado: zero elementos HTML nativos de expansão. Agent Browser `errors`: vazio. `npm test`, `npm run check` e `git diff --check` aprovados.
- Regra registrada em `AGENTS.md`. Nenhum monitor real foi alterado.

final result: passed

## Referência e evidências

- Proposta aprovada: primeira imagem exibida na conversa, `C:/Users/maxsu/.codex/generated_images/01a1b6ad-3625-74d2-a9a5-1d604eaca634/exec-4d2b63ee-0efe-4d8f-a3c4-5505522d7d1d.png` (1487 × 1058 px, quatro quadros).
- Aplicação: janela Electron própria, `electron . --demo --qa`, sessão Agent Browser `monitor-match-41ce845836`, CDP local 63615, PID 12512. Hardware real não foi acessado para escrita.
- Capturas finais: `output/redesign-welcome.png`, `output/redesign-setup.png`, `output/redesign-brightness.png`, `output/redesign-review.png`.
- Comparação conjunta aberta e examinada: `output/redesign-comparison.png`. Os quatro quadros da referência foram recortados sem as legendas externas, e cada captura foi reduzida proporcionalmente para caber em 700 × 480 px, sem distorcer seu aspecto.
- Viewport final 1180 × 830 CSS px; capturas finais 1180 × 830 px, escala de captura 1. A janela nativa inicial produziu 1906 × 1334 px devido à escala do Windows; não foi usada como comparação de densidade 1:1.
- Capturas adicionais: `output/redesign-colors.png`, `output/redesign-advanced.png`, `output/redesign-backups.png`, `output/redesign-820.png`, `output/redesign-390.png`.

## Comparação visual e adaptações

- Tipografia: Public Sans local, títulos em 600, texto escuro, hierarquia de título/instrução/controle/ação. Tamanhos de produto foram mantidos legíveis no viewport real; o desenho gerado amplia letras proporcionalmente nos seus quadros menores. A comparação é da direção visual e organização, sem afirmar identidade pixel a pixel.
- Espaçamento: menu lateral persistente, seletor do destino, uma função visível, controle horizontal e uma ação principal. Boas-vindas e assistente ocupam a janela sem navegação concorrente. A revisão usa uma superfície de página com foco modal, preservando o bloqueio de interação enquanto se confirma.
- Cores: fundo gelo, texto azul escuro, azul de ação, seleção em azul claro e bordas funcionais. Superfícies de diagnóstico mantêm seus padrões de preto originais.
- Imagens: ilustrações raster próprias para boas-vindas e escolha do monitor; Bootstrap Icons local com licença preservada. A ilustração não simula a imagem resultante de um ajuste.
- Texto e dados: nomes e limites reais do backend de demonstração substituem os números fictícios do desenho. Brilho aparece em unidades DDC (ex.: 140 de máximo 200), não como uma porcentagem inventada. A revisão mostra os valores exatos enviados ao serviço. Aviso de demo e mensagens de backup/verificação permanecem visíveis.
- Foco regional: a confirmação foi capturada separadamente em tamanho legível; o antes/depois 140 → 125, destino e ação de backup foram examinados. Os campos RGB indisponíveis permanecem desabilitados e recebem explicação explícita.

## Histórico de correções visuais

1. Primeira captura: faltavam ícones de navegação e a escolha do monitor usava apenas um ícone genérico; a confirmação ainda tinha formato de caixa pequena. Tratados como desvios P2.
2. Correções: ícones locais, ilustrações coerentes com a referência, confirmação em página, espaço da imagem de boas-vindas ajustado. Evidência posterior em `redesign-setup.png`, `redesign-review.png` e na comparação conjunta final.
3. Sem P0/P1/P2 de usabilidade remanescente nas capturas examinadas. Em 390 px o menu vira faixa com rolagem própria; a página não tem overflow horizontal (scrollWidth 375, innerWidth 390). Em 820 × 640 o menu lateral e Configurar telas permanecem alcançáveis; conteúdo longo usa rolagem vertical.

## Fluxos verificados

- Boas-vindas → referência → destino → revisão da seleção → Brilho. Essa configuração não aplica ajustes.
- Navegação Brilho, Contraste, Cores, Copiar ajustes, Comparar telas, Backups e Avançado.
- Seleção salva e retorno à tela Brilho após recarregar.
- Rascunho de Brilho 130, troca para Contraste 62 e confirmação: apenas Contraste 60 → 62 na prévia. Aplicação DEMO concluída, backup registrado e valor relido 62; o brilho permaneceu 140.
- Revisão de Brilho 140 → 125 e cancelamento. Sliders não aplicam ao vivo.
- Prévia de cópia, controles RGB indisponíveis e curva SDR desabilitada até selecionar a opção.
- Estados adicionais simulados no renderer: sem monitores, backup/restauração/revisão desabilitados; com um monitor, ajustes individuais disponíveis e mensagem indicando que copiar exige duas telas.
- Agent Browser `errors`: nenhum erro de página ao final dos fluxos normais.

## Validações automatizadas

- `python -m unittest discover -s tests -v`: 61 testes aprovados.
- `python -m compileall -q monitor_ips.py monitor_tool tests`: aprovado.
- `python monitor_ips.py --demo list --json`: dois monitores simulados.
- `npm test`: integração Electron/Python de comparar, aplicar, restaurar e encerrar o filho aprovada.
- `npm run check`: sintaxe dos módulos existentes e do novo shell aprovada.
- `git diff --check`: aprovado.

## Limites e refinamentos

- Nenhuma calibração, escrita DDC/CI ou alteração de curva de monitores físicos foi realizada. Tkinter não foi redesenhado.
- As telas sem equivalente no desenho foram organizadas com o mesmo sistema visual, preservando as funções existentes.
- Refinamento P3: o fundo das ilustrações raster varia levemente em relação ao fundo da janela; não afeta legibilidade ou uso.
- Evidências em `output/` são locais e ignoradas pelo Git. A origem dos assets entregues está em `desktop/assets/SOURCES.md`.
- Encerramento: `window.monitor.qa('quit')` retornou sucesso; launcher confirmou saída 0. Sessão Agent Browser exata encerrada; consulta Win32 confirmou ausência do PID 12512 e dos filhos diretos após o encerramento. Nenhum preview foi deixado aberto.
