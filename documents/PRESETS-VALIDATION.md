# Modelos prontos — validação em 07/11/2026

## Escopo entregue

Quatro modelos no catálogo Python: OLED equilibrado, Cinema escuro, Cores naturais
e Ambiente claro. GUI e CLI compartilham catálogo, planejamento, backup, verificação
e restauração. IPS pode ser selecionado explicitamente como destino. Nenhuma
alteração do driver, ICC, preset OSD, RGB ou contraste faz parte desses modelos.

Interface segue o shell claro existente, com seleção por rádio, seletor de painel
customizado, opção de curva SDR, brilho percentual personalizado com input/slider
e botão de revisão visível antes do catálogo. Seleção e prévia não escrevem.

## Evidências

- 71 testes Python aprovados. Os dez testes novos exercitam os quatro modelos nos
  dois painéis, escala DDC diferente, guarda de controles preservados e preset,
  curva neutra e curvas estéticas, sombras/realces, HDR, brilho indisponível,
  parâmetros inválidos, idempotência e quantização do driver, tokens, undo e CLI.
- Integração Node → Python aprovada, com encerramento do processo filho.
- Sintaxe JavaScript e compilação Python aprovadas.
- `scripts/qa-presets.js`, executado via Agent Browser em Electron DEMO próprio:
  oito combinações modelo/painel passaram por revisão, aplicação e undo completo
  de controles e curva; outro monitor, RGB e contraste preservados. Também foram
  validados limites do override, escala 0–200, sem curva e cancelar.
- Nenhum erro JavaScript reportado pelo Agent Browser.
- Janelas 820/1180/1440 px sem overflow horizontal; screenshots inspecionados em
  `output/presets-820.png`, `presets-1180.png`, `presets-1440.png`; revisão final
  com ação no topo em `output/presets-final.png`. Arquivos de QA são ignorados.
- CLI real somente `--dry-run`: OLED equilibrado no IPS já estava equivalente à
  curva atual e ao teto de brilho; Cinema escuro no IPS e OLED equilibrado no VA
  produziram planos de alteração apenas da curva. Não houve escrita real nesta rodada.
- Recursos próprios: Electron PIDs 22084 e 27500, sessões Agent Browser exclusivas,
  fechados ao fim da validação e launchers com saída 0. Nenhum serviço permanente.

## Limites da evidência

Aplicação e restauração automatizadas foram provadas em DEMO, não em escrita no
hardware. As prévias reais provam leitura e construção do plano para as telas
conectadas; não provam melhoria visual nem equivalência com OLED. Não foi usado
colorímetro. Os percentuais dos modelos são escolhas heurísticas documentadas,
e não uma medição de luminância, ponto branco ou gamma dos monitores locais.

Um IPS não adquire preto por pixel, gamut, resposta ou HDR de um OLED por software.
O aplicativo declara esse limite e apresenta os modelos como ajustes de aparência.
