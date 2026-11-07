# Pesquisa e proposta de modelos de imagem

Consulta em 07/11/2026. Proposta em revisão; os modelos abaixo ainda não foram
implementados ou aplicados.

## Resultado da pesquisa

OLED possui emissão por pixel e não depende da iluminação traseira de um LCD.
Um ajuste DDC ou uma curva GPU não transforma o preto físico, gamut, resposta ou
HDR de um IPS/VA em OLED. Não existe um único conjunto de números que entregue
a melhor imagem em qualquer monitor e ambiente.

A EIZO apresenta gamma 2,2 como referência comum, com brilho ajustado separadamente
ao ambiente. Seu fluxo de calibração recomenda objetivos de gamma, ponto branco e
brilho definidos para o uso, e explica que calibração não remove limitações do
monitor. Esses objetivos não podem ser certificados apenas com percentuais DDC.

Fontes primárias:

- [EIZO — gamma e correção de gamma](https://www.eizo.com/library/basics/lcd_display_gamma/)
- [EIZO — ajuste e calibração do monitor](https://www.eizo.eu/colour-management-and-calibration/colour-management-the-complete-workflow/monitor-adjustment)
- [EIZO — temperatura de cor](https://www.eizo.com/library/basics/color_temperature_on_an_LCD_monitor/)
- [LG — tecnologias LCD e OLED](https://www.lg.com/my/lg-experience/helpful-hints/lg-screen-technology-explained/)

Não foi localizado manual oficial suficiente para definir calibração específica
pelos identificadores locais VLK2730 e LHCFFFF. Não inferir marca/modelo comercial
nem copiar ICC, RGB ou saturação de outro exemplar. Os perfis serão estéticos e
deverão informar seus parâmetros como escolhas do aplicativo, não do fabricante.

## Conjunto proposto

| Modelo | Uso | Estratégia |
| --- | --- | --- |
| OLED equilibrado | Uso geral, luz moderada | Curva suave de profundidade, preservando sombras e realces |
| Cinema escuro | Filmes em ambiente escuro | Menos luz de fundo e meios-tons mais profundos, sem corte de sombras |
| Cores naturais | Conteúdo SDR e uso diário | Curva neutra, preservando contraste e ganhos RGB existentes |
| Ambiente claro | Sala iluminada | Mais luz de fundo com curva neutra, sem estourar os canais RGB |

O destaque sugerido é OLED equilibrado. Os quatro modelos devem funcionar em
IPS e VA, com seleção explícita de tela e tipo de painel. A seleção não aplica
automaticamente. Prévia deve mostrar alterações, controles preservados e avisar
quando uma curva absoluta substituir a curva atual.

## Integração prevista

- Catálogo único no backend Python, reutilizado pela interface e pelo CLI.
- Reutilizar o serviço, plano por token, backup, verificação e restauração atuais.
- Reutilizar as curvas de `looks.py` nos modelos estéticos e uma curva identidade
  nos neutros; não aplicar gamma 2,2 como expoente GPU sobre uma tela desconhecida.
- Preservar RGB, contraste e preset OSD atuais; não inventar temperatura Kelvin
  a partir de ganhos sem medição.
- Brilho como percentual da escala DDC, nunca como cd/m². Permitir ajuste do ponto
  de partida e mostrar quando o valor sugerido aumenta a luz atual.
- Curva apenas em SDR confirmado. Sem curva, informar que só o brilho será mudado;
  nunca fazer fallback silencioso em HDR ou ao falhar a API.
- Aplicação em IPS permitida quando ele for o destino explícito, preservando o VA.
- Testar catálogo, extremos/monotonicidade, repetição sem acúmulo, backup/restore,
  prévia obsoleta, HDR, controles indisponíveis e aplicação pela GUI em DEMO.

## Contexto da leitura atual

Leitura somente leitura nesta rodada: ambas as telas com brilho 8/100, contraste
55/100 e preset 0x08; ganhos RGB diferentes. Esses valores são contexto, não uma
calibração aprovada para reutilização. Nenhum ajuste de hardware foi realizado
para esta pesquisa. Alterações existentes na interface foram preservadas.
