# Interface e diagnóstico de preto — 07/11/2026

## Entrega

Interface Electron com superfícies arredondadas, animações curtas e suporte a
`prefers-reduced-motion`, seletores personalizados e controles numéricos, −/+ e
sliders sincronizados. Edição prepara valores; aplicação continua exigindo prévia,
confirmação, backup e verificação. Curva SDR manual opcional, absoluta e limitada;
desfazer usa o último backup do destino nesta sessão. CLI `tune` e `diagnose`.

## Evidências

- 61 testes Python aprovados, incluindo curva, limites, estado obsoleto, HDR,
  restauração e diagnóstico somente leitura.
- Integração Node → Python aprovada: comparar, aplicar, restaurar e encerrar filho.
- Sintaxe JavaScript e compilação Python aprovadas.
- Agent Browser em Electron DEMO: seletores/teclado, sincronização de inputs,
  nenhum write ao editar, limites, campo vazio, curva e avisos, aplicar, desfazer
  DDC + curva e preservação da referência. Script: `scripts/qa-studio-regressions.js`.
- Janelas de 820/1180/1440 px, viewport 811/1170/1430 px, sem overflow horizontal;
  screenshots inspecionados em `output/studio-820.png`, `studio-1180.png` e
  `studio-final.png` (ignorados pelo Git).
- NVIDIA RTX 4060 real: consultas GET retornaram RGB completo, 8 bits, nas duas
  saídas. Nenhum SET de driver foi implementado.
- Teste pareado real em instância `--read-only`: posição confirmada por EnumWindows,
  uma janela em cada monitor. A primeira implementação colocava ambas no principal;
  corrigido usando o centro do retângulo físico e janelas independentes posicionadas
  antes de entrar em tela cheia. Raiz e body do teste RGB 0 ocupam toda a janela.
- Alternância sincronizada 0 → 8 e botão de retorno a 0 verificados em DEMO,
  incluindo fundo computado `rgb(0, 0, 0)` nas duas janelas.
- Cada launcher de QA usa userData por PID para evitar disputa de cache.
- Todas as instâncias próprias de QA e sessões Agent Browser encerradas; launchers
  confirmaram saída 0. Não foi iniciado watcher, serviço ou tarefa permanente.

## Resultado visual e limites

O usuário relatou cinza no IPS durante o teste. Depois de fechar os padrões,
confirmou que o IPS voltou ao aspecto anterior e que **o VA está bom no conteúdo
normal**. Nenhum ajuste real de brilho, RGB ou curva foi aplicado nesta rodada de
diagnóstico e redesign. A confirmação é perceptual; não é uma calibração óptica
nem prova de igualdade de luminância, gamut ou contraste físico entre painéis.

Os níveis 8/16/32 são fundos cinza intencionais, não alterações dos monitores.
O teste agora explica isso e oferece retorno explícito ao nível 0. A curva manual
pode escurecer tons e ocultar detalhes; não reduz o preto físico do painel.
